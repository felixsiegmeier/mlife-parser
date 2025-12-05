from __future__ import annotations

import logging
import re
from io import TextIOBase
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)

class DataParserBase:
    """
    Basisklasse für alle Parser.
    
    Hier liegen die gemeinsamen Funktionen, die alle Mixins benötigen:
    1. Einlesen der Datei (_read_input)
    2. Bereinigen von Metadaten/Headern (_clean_csv)
    3. Aufteilen der Datei in Hauptkategorien (_split_blocks)
    4. Generische Hilfsfunktionen für Zeitstempel und Tabellen-Parsing.
    """
    
    def __init__(self, file: str | TextIOBase, delimiter: str = ";"):
        """Initialisiert den DataParser."""
        self.delimiter = delimiter
        self._clean_file: Optional[str] = None
        self._blocks: Optional[Dict[str, Dict[str, str]]] = None
        self._raw_input = file
        self._source_path: Optional[Path] = None
        self.raw_file = self._read_input(file)
        self._detect_delimiter()
        
        self.headers = {
            "Vitaldaten": ['Online erfasste Vitaldaten', 'Manuell erfasste Vitaldaten'],
            "Respiratordaten": ['Online erfasste Respiratorwerte', 'Beatmung', 'Manuell erfasste Respiratorwerte'],
            "Labor": ['Labor: Blutgase arteriell', 'Labor: Blutgase venös', 'Labor: Blutgase gv', 
                     'Labor: Blutgase unspez.', 'Labor: Blutbild', 'Labor: Differentialblutbild',
                     'Labor: Blutgruppe', 'Labor: Gerinnung', 'Labor: TEG', 'Labor: TAT',
                     'Labor: Enzyme', 'Labor: Retention', 'Labor: Lipide', 'Labor: Proteine',
                     'Labor: Elektrolyte', 'Labor: Blutzucker', 'Labor: Klinische Chemie',
                     'Labor: Medikamentenspiegel', 'Labor: Schilddrüse', 'Labor: Serologie/Infektion'],
            'Medikamentengaben': ["Medikamentengaben"],
            'Bilanz': ["Bilanz"],
            'ALLE Patientendaten': ["ALLE Patientendaten"]
        }

    def _detect_delimiter(self) -> None:
        """Ermittelt den Delimiter basierend auf der Häufigkeit von ';' vs '|'."""
        if not self.raw_file:
            return
            
        # Analyse eines Samples (z.B. erste 5000 Zeichen)
        sample = self.raw_file[:5000]
        semicolons = sample.count(";")
        pipes = sample.count("|")
        
        if pipes > semicolons:
            self.delimiter = "|"
        else:
            self.delimiter = ";"

    def _clean_string(self, s: str) -> str:
        """Bereinigt Strings von überflüssigen Leerzeichen und Punkten am Ende."""
        if not s or not isinstance(s, str):
            return s
        # Mehrfache Leerzeichen durch einfache ersetzen
        s = re.sub(r'\s+', ' ', s).strip()
        # Punkt am Ende entfernen, falls vorhanden (außer es ist eine Abkürzung wie 'Dr.')
        if s.endswith('.') and len(s) > 3 and not s.endswith('Dr.'):
            s = s[:-1]
        return s
        
    def _read_input(self, raw: str | TextIOBase | bytes | bytearray) -> str:
        """Sorgt dafür, dass der Parser immer einen rohen CSV-String erhält."""
        if isinstance(raw, TextIOBase):
            contents = raw.read()
            if hasattr(raw, "seek"):
                raw.seek(0)
            return contents

        if isinstance(raw, (bytes, bytearray)):
            return raw.decode("utf-8", errors="ignore")

        if isinstance(raw, str):
            if "\n" in raw:
                return raw
            potential_path = Path(raw)
            if potential_path.exists() and potential_path.is_file():
                self._source_path = potential_path
                return potential_path.read_text(encoding="utf-8", errors="ignore")
            return raw

        raise TypeError("Unsupported input type for DataParser")

    def _clean_csv(self) -> str:
        """Bereinigt die CSV-Datei."""
        if self._clean_file is not None:
            return self._clean_file
            
        lines = self.raw_file.splitlines()
        skip = {len(lines) - 1}  # Skip last line
        headers = [] # every header line start index; headers are 8 lines long and should be skipped
        
        # Find lines to skip
        for i, line in enumerate(lines):
            line_stripped = line.lstrip()
            if "Ausdruck: Gesamte Akte" in line_stripped:
                headers.append(i)
            elif any(text in line_stripped for text in [
                "Bei aktuell laufenden Statusmodulen",
                "Datum/Uhrzeit bezieht sich jeweils auf den Intervallstart."
            ]):
                skip.add(i)
                if "Datum/Uhrzeit" in line_stripped:
                    skip.add(i - 1)
            elif re.search(r"Intervall:\s*\d{2}\s*min\.,?", line_stripped):
                skip.add(i)
        
        # Skip header blocks
        for j, h in enumerate(headers):
            skip.update(range(h, min(h + 8, len(lines))))
            if j > 0 and h - 1 >= 0:
                skip.add(h - 1)
        
        # Build clean file
        clean_lines = [line for i, line in enumerate(lines) if i not in skip]
        self._clean_file = "\n".join(clean_lines)
        return self._clean_file
    
    def _split_blocks(self) -> Dict[str, Dict[str, str]]:
        """Teilt die Datei in kategorisierte Blöcke auf.
        
        Lazy loading: Die Blöcke werden nur beim ersten Aufruf berechnet und gespeichert.
        Bei weiteren Aufrufen wird das gespeicherte Ergebnis direkt zurückgegeben.
        """
        if self._blocks is not None:
            return self._blocks
            
        lines = self._clean_csv().splitlines()
        result = {category: {} for category in self.headers}
        current_category = None
        current_block = None
        buffer = []

        for line in lines:
            key = line.split(self.delimiter, 1)[0].strip()
            
            # Check if line starts a new block
            found_category = None
            for category, blocks in self.headers.items():
                if key in blocks:
                    found_category = category
                    break
            
            if found_category:
                # Save previous buffer
                if current_category and current_block and buffer:
                    result[current_category][current_block] = "\n".join(buffer).strip()
                # Start new block
                current_category = found_category
                current_block = key
                buffer = []
            else:
                buffer.append(line)
        
        # Save final buffer
        if current_category and current_block and buffer:
            result[current_category][current_block] = "\n".join(buffer).strip()
            
        self._blocks = result
        return result
    
    def _parse_timestamp(self, ts_str: str) -> Optional[datetime]:
        """Parst Timestamp."""
        ts_str = ts_str.strip()
        for fmt in ("%d.%m.%y %H:%M", "%d.%m.%Y %H:%M"):
            try:
                return datetime.strptime(ts_str, fmt)
            except (ValueError, TypeError):
                continue
        return None
    
    def _is_timestamp_row(self, parts) -> bool:
        """Prüft ob Zeile Timestamps enthält."""
        date_pattern = re.compile(r"\d{2}\.\d{2}\.\d{2,4}\s*\d{2}:\d{2}")
        return any(isinstance(tok, str) and date_pattern.search(tok) for tok in parts)

