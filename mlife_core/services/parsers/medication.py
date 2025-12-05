from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
import pandas as pd

from .base import DataParserBase
from mlife_core.schemas.parse_schemas.medication import MedicationModel

class MedicationParserMixin(DataParserBase):
    """
    Mixin speziell für das Parsen von Medikamentengaben.
    
    Behandelt die komplexe Logik von Start-/Stopp-Zeiten, Raten und Bolus-Gaben,
    die im Block 'Medikamentengaben' enthalten sind.
    """
    def parse_medication_logic(self, config: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Parst Medikamentendaten."""
        blocks = self._split_blocks()
        med_text = blocks.get("Medikamentengaben", {}).get("Medikamentengaben", "")

        clean_text = self._clean_medication_text(med_text)
        lines = [line.split(self.delimiter) for line in clean_text.splitlines()]

        data_list = []
        buffer = []
        current_header = None

        for line in lines:
            if not self._is_timestamp_row(line):
                if buffer and current_header:
                    cols = self._get_medication_columns(current_header)
                    if cols:
                        data_list.extend(self._process_medication_block(buffer, cols, current_header))
                current_header = line
                buffer = []
            else:
                if current_header:
                    buffer.append(line)

        if buffer and current_header:
            cols = self._get_medication_columns(current_header)
            if cols:
                data_list.extend(self._process_medication_block(buffer, cols, current_header))

        return pd.DataFrame([item.__dict__ for item in data_list])

    def _clean_medication_text(self, text: str) -> str:
        """Bereinigt Medikamenten-Text."""
        return re.sub(
            r'"(.*?)"',
            lambda m: m.group(0).replace("\n", " ").replace("\r", "").replace('"', ""),
            text,
            flags=re.DOTALL,
        )

    def _extract_from_cell(self, cell_content: str, pattern: str, converter=None) -> List:
        """Extrahiert Werte aus Zelle mit Pattern."""
        matches = re.findall(pattern, cell_content)
        if converter:
            return [converter(match) for match in matches if converter(match) is not None]
        return matches

    def _get_medication_columns(self, header) -> Optional[Dict[str, int]]:
        """Findet Spalten-Indices für Medikamente."""
        category = next((entry for entry in header if isinstance(entry, str) and entry.strip()), "")
        try:
            return {
                'medication': header.index(category),
                'concentration': header.index("Konzentration"),
                'application': header.index("App.- form"),
                'start': header.index("Start/Änderung"),
                'stop': header.index("Stopp"),
                'rate': header.index("Rate(mL/h)")
            }
        except ValueError:
            return None

    def _process_medication_block(self, lines, cols, header) -> List[MedicationModel]:
        """Verarbeitet Medikamenten-Block."""
        result = []
        category = next((entry for entry in header if isinstance(entry, str) and entry.strip()), "")

        for line in lines:
            if len(line) <= max(cols.values()):
                continue

            start_times = self._extract_from_cell(
                line[cols['start']],
                r"\d{2}\.\d{2}\.\d{2,4}\s*\d{2}:\d{2}",
                self._parse_timestamp,
            )
            stop_times = self._extract_from_cell(
                line[cols['stop']],
                r"\d{2}\.\d{2}\.\d{2,4}\s*\d{2}:\d{2}",
                self._parse_timestamp,
            )
            rates = self._extract_from_cell(
                line[cols['rate']],
                r"\d+(?:[.,]\d+)?",
                lambda x: float(x.replace(",", ".")),
            )

            for i, start in enumerate(start_times):
                rate = rates[i] if i < len(rates) else None
                concentration = line[cols['concentration']]
                value = rate if rate is not None else concentration
                
                result.append(
                    MedicationModel(
                        parameter=line[cols['medication']],
                        category=category,
                        concentration=concentration,
                        application=line[cols['application']],
                        timestamp=start,
                        stop=stop_times[i] if i < len(stop_times) else None,
                        rate=rate,
                        value=value
                    )
                )

        return result
