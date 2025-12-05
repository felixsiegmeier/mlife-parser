from __future__ import annotations
import csv
import re
from io import StringIO
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd

from .base import DataParserBase
from mlife_core.schemas.parse_schemas.fluidbalance import FluidBalanceModel

class FluidBalanceParserMixin(DataParserBase):
    def parse_fluidbalance_logic(self) -> pd.DataFrame:
        """Parst Flüssigkeitsbilanz-Daten auf Basis der Bilanz-Blöcke."""
        blocks = self._split_blocks()
        fluid_text = blocks.get("Bilanz", {}).get("Bilanz", "")

        if not fluid_text:
            return pd.DataFrame()

        reader = list(csv.reader(StringIO(fluid_text), delimiter=self.delimiter))
        if not reader:
            return pd.DataFrame()

        header_row = reader[0]
        time_columns: Dict[int, str] = {}
        for idx, cell in enumerate(header_row):
            cleaned = cell.strip().strip('"')
            if cleaned and cleaned.lower() != "flüssigkeitsbilanz":
                time_columns[idx] = cleaned.replace("\n", " ")

        entries: List[FluidBalanceModel] = []
        current_category: Optional[str] = None

        for row in reader[1:]:
            label = row[3].strip() if len(row) > 3 else ""

            if not label:
                continue

            # Check if row contains any numeric values in the time columns
            has_values = False
            for col_idx in time_columns:
                if col_idx < len(row):
                    val = row[col_idx].strip()
                    if val and any(c.isdigit() for c in val):
                        has_values = True
                        break
            
            # If no values, treat as category header
            if not has_values:
                current_category = label
                continue

            # It's a parameter row
            parameter = label.strip("() ")
            
            for col_idx, value_raw in enumerate(row):
                if col_idx not in time_columns:
                    continue
                value_str = value_raw.strip().replace(" ", "")
                if not value_str:
                    continue
                value_str = value_str.replace(",", ".")
                try:
                    value = float(value_str)
                except ValueError:
                    continue

                time_label = time_columns[col_idx]
                timestamp = self._time_range_to_timestamp(time_label)
                
                if timestamp is None:
                    continue
                    
                entries.append(
                    FluidBalanceModel(
                        timestamp=timestamp,
                        value=value,
                        category=current_category or "unknown",
                        parameter=parameter,
                        time_range=time_label,
                    )
                )

        if not entries:
            return pd.DataFrame()
        with open("fluid_debug.log", "w") as f:
            for entry in entries:
                f.write(f"{entry}\n")

        return pd.DataFrame([item.dict() for item in entries])

    def _time_range_to_timestamp(self, label: str) -> Optional[datetime]:
        """Ermittelt einen repräsentativen Timestamp aus einem Zeitbereichs-Label."""
        cleaned = label.strip().strip('"')
        cleaned = cleaned.replace("\n", " ")
        match = re.search(
            r"(\d{2}\.\d{2}\.\d{4}\s*\d{2}:\d{2})\s*-\s*(\d{2}\.\d{2}\.\d{4}\s*\d{2}:\d{2})",
            cleaned,
        )
        if match:
            start = self._parse_timestamp(match.group(1))
            end = self._parse_timestamp(match.group(2))
            if start and end:
                return start + (end - start) / 2
            return start or end

        return self._parse_timestamp(cleaned)
