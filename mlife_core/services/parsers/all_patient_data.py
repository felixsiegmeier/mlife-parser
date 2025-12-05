from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd

from .base import DataParserBase

class AllPatientDataMixin(DataParserBase):
    """
    Mixin für den komplexen Block 'ALLE Patientendaten'.
    
    Dieser Block in der CSV ist anders aufgebaut als die anderen:
    Er enthält verschachtelte Unterkategorien (z.B. Geräte, spezielle Laborwerte),
    die dynamisch erkannt werden müssen. Dieses Mixin stellt Funktionen bereit,
    um diese verschachtelte Struktur zu durchsuchen und zu parsen.
    """
    def _extract_all_patient_data_headers(self, data_str: str) -> set:
        lines = data_str.splitlines()
        headers_set = set()
        for line in lines:
            l = line.split(self.delimiter)
            if len(l) > 2 and l[0] == "" and l[1] == "" and l[2] and l[2] != "Datum":
                headers_set.add(l[2])
        return headers_set

    def _get_from_all_patient_data_by_string(self, query: str) -> Dict[str, Dict[str, List[str]]]:
        patient_data = self._split_blocks().get("ALLE Patientendaten", {})
        if isinstance(patient_data, dict):
            data_str = next(iter(patient_data.values()), "")
        else:
            data_str = patient_data

        headers = self._extract_all_patient_data_headers(data_str)
        matching_headers = [header for header in headers if query.lower() in header.lower()]

        lines = data_str.splitlines()
        result: Dict[str, Dict[str, List[str]]] = {header: {} for header in matching_headers}

        current_header: Optional[str] = None
        current_sub_header_counter = 0
        current_sub_header: Optional[str] = None
        buffer: List[str] = []

        for line in lines:
            parts = line.split(self.delimiter)
            if len(parts) < 3:
                if current_header is not None:
                    buffer.append(line)
                continue

            key = parts[2]

            if key in headers:
                # Flush buffer to PREVIOUS block
                if current_header is not None and current_sub_header is not None and buffer:
                    result[current_header].setdefault(current_sub_header, []).extend(buffer)
                    buffer = []

                if key in matching_headers:
                    # Start NEW block
                    # Always increment counter for a new header occurrence to separate entries
                    if key == current_header:
                        current_sub_header_counter += 1
                    else:
                        current_sub_header_counter = 1

                    current_header = key
                    current_sub_header = f"{current_header} {current_sub_header_counter}"
                    result[current_header].setdefault(current_sub_header, [])
                    
                    # Add the header line itself to the new block, as it may contain data
                    result[current_header][current_sub_header].append(line)
                else:
                    # It's a header, but not one we are looking for.
                    current_header = None
                    current_sub_header = None
            else:
                if current_header is not None:
                    buffer.append(line)

        if current_header is not None and current_sub_header is not None and buffer:
            result[current_header].setdefault(current_sub_header, []).extend(buffer)
        return result

    def _get_device_values(self, parts) -> Tuple[Optional[str], Optional[str]]:
        non_empty = [entry for entry in parts if isinstance(entry, str) and entry.strip()]
        if len(non_empty) >= 2:
            return non_empty[0], non_empty[1]
        return None, None

    def _find_timestamp(self, parts) -> Optional[datetime]:
        for token in parts:
            if isinstance(token, str) and re.search(r"\d{2}\.\d{2}\.\d{2,4}\s*\d{2}:\d{2}", token):
                return self._parse_timestamp(token)
        return None

    def parse_from_all_patient_data(self, keyword: str) -> pd.DataFrame:
        all_data = self.parse_all_patient_data()
        matching_headers = [h for h in all_data.keys() if keyword.upper() in h.upper()]
        dfs = []
        for h in matching_headers:
            dfs.extend(list(all_data[h].values()))
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    def parse_all_patient_data(self) -> Dict[str, Dict[str, pd.DataFrame]]:
        patient_data = self._split_blocks().get("ALLE Patientendaten", {})
        if isinstance(patient_data, dict):
            data_str = next(iter(patient_data.values()), "")
        else:
            data_str = patient_data

        headers = self._extract_all_patient_data_headers(data_str)
        result = {}

        for header in headers:
            blocks = self._get_from_all_patient_data_by_string(header)
            result[header] = {}

            for sub_header, lines in blocks.get(header, {}).items():
                # lines represents ONE entry (header line + content lines)
                
                data_rows = []
                current_timestamp = None
                text_buffer = []
                
                for line in lines:
                    parts = line.split(self.delimiter)
                    
                    # 1. Check for Timestamp
                    ts = self._find_timestamp(parts)
                    if ts:
                        # If we have a new timestamp, flush the buffer to the OLD timestamp
                        if text_buffer and current_timestamp:
                            val_str = "\n".join(text_buffer)
                            data_rows.append({
                                'timestamp': current_timestamp,
                                'value': val_str,
                                'category': sub_header,
                                'parameter': header,
                                'source_header': header
                            })
                            text_buffer = []
                        
                        current_timestamp = ts
                    
                    # 2. Check for Key-Value Pair (Impella style: col 4 param, col 9 value)
                    # Ensure parts has enough length and col 2 (header col) is empty
                    if len(parts) > 9 and parts[4].strip() and parts[9].strip() and not parts[2].strip():
                        # Flush text buffer first
                        if text_buffer and current_timestamp:
                            val_str = "\n".join(text_buffer)
                            data_rows.append({
                                'timestamp': current_timestamp,
                                'value': val_str,
                                'category': sub_header,
                                'parameter': header,
                                'source_header': header
                            })
                            text_buffer = []
                        
                        # Add Key-Value row
                        if current_timestamp:
                            val_str = parts[9].strip()
                            # Try to convert to float if possible
                            try:
                                val = float(val_str.replace(",", "."))
                            except ValueError:
                                val = val_str

                            data_rows.append({
                                'timestamp': current_timestamp,
                                'value': val,
                                'category': sub_header,
                                'parameter': parts[4].strip(), # Use the sub-parameter
                                'source_header': header
                            })
                        continue # Done with this line
                        
                    # 3. Collect Text/Value
                    # Filter empty parts
                    valid_parts = [p for p in parts if isinstance(p, str) and p.strip()]
                    
                    for p in valid_parts:
                        p_clean = p.strip()
                        # Skip if it matches the header key (fuzzy or exact)
                        if p_clean == header or (header in p_clean and len(p_clean) < len(header) + 5):
                            continue
                        
                        # Skip if it is the timestamp
                        if self._find_timestamp([p_clean]):
                            continue
                            
                        # Skip User Initials (e.g. "F. K.") - Simple Regex
                        if re.match(r"^[A-Z]\.\s*[A-Z]\.$", p_clean):
                            continue
                            
                        # Skip "Arztnotizen" artifact if present
                        if "Arztnotizen" in p_clean and len(p_clean) < 20:
                            continue

                        # Clean up quotes
                        val = p_clean.strip('"').strip()
                        if val:
                            text_buffer.append(val)

                # Flush remaining buffer
                if text_buffer and current_timestamp:
                     val_str = "\n".join(text_buffer)
                     # Try to convert to float if possible (for numeric parameters)
                     try:
                         value = float(val_str.replace(",", "."))
                     except ValueError:
                         value = val_str

                     data_rows.append({
                        'timestamp': current_timestamp,
                        'value': value,
                        'category': sub_header,
                        'parameter': header,
                        'source_header': header
                     })

                if data_rows:
                    result[header][sub_header] = pd.DataFrame(data_rows)

        with open("all_patient_data_debug.csv", "w", encoding="utf-8") as f:
            for header, sub_blocks in result.items():
                for sub_header, df in sub_blocks.items():
                    f.write(f"Header: {header} | Sub-header: {sub_header}\n")
                    df.to_csv(f, index=False, sep=';')
                    f.write("\n\n")
        return result


class AllPatientDataParserMixin(AllPatientDataMixin):
    def parse_complete_all_patient_data(self) -> pd.DataFrame:
        """
        Parst den kompletten Block 'ALLE Patientendaten' und gibt ihn als flachen DataFrame zurück.
        Enthält Geräte (ECMO, Impella, etc.), Scores, Pflegeberichte, etc.
        """
        all_data_dict = self.parse_all_patient_data()
        if not all_data_dict:
            return pd.DataFrame()

        frames: List[pd.DataFrame] = []
        for header, sub_blocks in all_data_dict.items():
            for sub_header, df in sub_blocks.items():
                if df is None or df.empty:
                    continue
                
                # Bereinigung der Metadaten
                if 'source_header' in df.columns:
                    df['source_header'] = df['source_header'].apply(self._clean_string)
                if 'category' in df.columns:
                    df['category'] = df['category'].apply(self._clean_string)
                if 'parameter' in df.columns:
                    df['parameter'] = df['parameter'].apply(self._clean_string)
                    
                frames.append(df)

        if not frames:
            return pd.DataFrame()

        result = pd.concat(frames, ignore_index=True)
        
        # Timestamp cleaning
        if "timestamp" in result.columns:
            result["timestamp"] = pd.to_datetime(result["timestamp"], errors="coerce")
            result = result.dropna(subset=["timestamp"])
            
        return result
