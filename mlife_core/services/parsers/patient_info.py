from __future__ import annotations
import re
from typing import Optional
import pandas as pd
from datetime import datetime

from .base import DataParserBase

class PatientInfoParserMixin(DataParserBase):
    """
    Mixin zum Parsen der statischen Patienteninformationen aus dem Header.
    (Alter, Größe, Gewicht, BMI, BSA)
    """

    def extract_patient_name(self) -> Optional[str]:
        """
        Versucht den Patientennamen aus den ersten Zeilen zu extrahieren.
        Erwartet Format in Zeile 3, Spalte 2 (Index 1).
        """
        try:
            lines = self.raw_file.splitlines()[:20]
            for line in lines:
                parts = line.split(self.delimiter)
                # Heuristik: Name steht oft in der 2. Spalte (Index 1), 1. Spalte ist leer
                # Format: "Nachname, Vorname"
                if len(parts) > 2 and not parts[0].strip() and parts[1].strip():
                    potential_name = parts[1].strip()
                    if "," in potential_name and not any(char.isdigit() for char in potential_name):
                        return potential_name
        except Exception:
            pass
        return None

    def parse_patient_info(self) -> pd.DataFrame:
        """
        Extrahiert einmalig die Patientenstammdaten aus dem Header-Bereich.
        """
        # Wir schauen uns nur die ersten 100 Zeilen an, da der Header dort stehen muss.
        # Wir nutzen self.raw_file direkt, da _split_blocks den Header entfernen könnte.
        lines = self.raw_file.splitlines()[:100]
        
        header_found = False
        values_row = None
        timestamp = None
        
        # 1. Suche nach Timestamp (Start des Berichtszeitraums)
        # Format: |10.09.2025 11:53 - 30.09.2025 01:45|...
        for line in lines:
            # Suche nach Datumsbereich DD.MM.YYYY HH:MM - DD.MM.YYYY HH:MM
            match = re.search(r"(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})\s*-\s*\d{2}\.\d{2}\.\d{4}", line)
            if match:
                timestamp = self._parse_timestamp(match.group(1))
                break
        
        if not timestamp:
            # Fallback: Versuche "Zeitpunkt Ausdruck" zu finden
            for line in lines:
                match = re.search(r"(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})", line)
                if match:
                    timestamp = self._parse_timestamp(match.group(1))
                    break
        
        if not timestamp:
            timestamp = datetime.now() # Fallback, sollte nicht passieren

        # 2. Suche nach der Zeile mit "Fall-ID" und "Größe"
        for i, line in enumerate(lines):
            if "Fall-ID" in line and "Größe" in line and "Gewicht" in line:
                # Die Werte stehen typischerweise in der nächsten Zeile
                if i + 1 < len(lines):
                    values_row = lines[i+1]
                    header_found = True
                    break
        
        if not header_found or not values_row:
            return pd.DataFrame()

        # 3. Parsen der Werte
        # Wir nutzen ein Mapping basierend auf Schlüsselwörtern im Header und Positionen?
        # Da die Spalten durch Delimiter getrennt sind, ist es sicherer, Header und Value Zeile parallel zu splitten.
        
        header_parts = lines[i].split(self.delimiter)
        value_parts = values_row.split(self.delimiter)
        
        data = {}
        
        # Mapping von Header-Name zu Ziel-Parameter
        mapping = {
            "Alter": "Alter",
            "Gewicht": "Gewicht",
            "Größe": "Größe",
            "Körperoberfläche": "Körperoberfläche (BSA)",
            "Fall-ID": "Fall-ID",
            "Pat.-ID": "Patienten-ID"
        }
        
        for idx, h in enumerate(header_parts):
            h_clean = h.strip()
            if h_clean in mapping and idx < len(value_parts):
                val_raw = value_parts[idx].strip()
                if val_raw:
                    data[mapping[h_clean]] = val_raw

        # 4. Bereinigung und BMI Berechnung
        results = []
        
        height_cm = None
        weight_kg = None
        
        for param, val in data.items():
            clean_val = val
            
            # Einheiten entfernen und in Float wandeln wo möglich
            if param == "Größe":
                clean_val = val.lower().replace("cm", "").strip()
                try:
                    height_cm = float(clean_val.replace(",", "."))
                    clean_val = height_cm
                except ValueError:
                    pass
            elif param == "Gewicht":
                clean_val = val.lower().replace("kg", "").strip()
                try:
                    weight_kg = float(clean_val.replace(",", "."))
                    clean_val = weight_kg
                except ValueError:
                    pass
            elif param == "Alter":
                clean_val = val.lower().replace("j", "").strip()
            elif param == "Körperoberfläche (BSA)":
                clean_val = val.lower().replace("m²", "").replace("m2", "").strip()
            
            results.append({
                "timestamp": timestamp,
                "category": "Patientenstamm",
                "parameter": param,
                "value": clean_val,
                "source_type": "PatientInfo"
            })
            
        # BMI berechnen
        if height_cm and weight_kg and height_cm > 0:
            bmi = weight_kg / ((height_cm / 100) ** 2)
            results.append({
                "timestamp": timestamp,
                "category": "Patientenstamm",
                "parameter": "BMI",
                "value": round(bmi, 2),
                "source_type": "PatientInfo"
            })

        return pd.DataFrame(results)
