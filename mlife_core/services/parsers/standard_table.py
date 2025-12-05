from __future__ import annotations
from typing import Optional, Tuple
import pandas as pd

from .base import DataParserBase

class StandardTableParser(DataParserBase):
    """
    Mixin für Parser, die Standard-Tabellen verarbeiten.
    
    Enthält die Logik zum Parsen von Tabellen, die aus einer Zeitstempel-Zeile
    und darauffolgenden Werte-Zeilen bestehen (z.B. Vitaldaten, Labor, Respirator).
    """
    
    def _get_first_entry(self, parts) -> Optional[Tuple[int, str]]:
        """Findet ersten nicht-leeren Eintrag."""
        for i, entry in enumerate(parts):
            if isinstance(entry, str) and entry.strip():
                return (i, entry.strip())
        return None

    def _parse_table_data(self, category_name: str, data_class, **options):
        """Parst tabellarische Daten (Vitals, Respiratory, Lab)."""
        blocks = self._split_blocks().get(category_name, {})
        data_list = []

        for key, block_str in blocks.items():
            timestamps = None
            lines = [line.rstrip('\r') for line in block_str.splitlines()]
            
            for line in lines:
                parts = line.split(self.delimiter)
                
                # Timestamp row?
                if self._is_timestamp_row(parts):
                    timestamps = [tok.strip() for tok in parts]
                    continue
                    
                if not timestamps:
                    continue
                    
                first_entry = self._get_first_entry(parts)
                if not first_entry:
                    continue
                    
                # Parse values
                for i, token in enumerate(parts):
                    if not isinstance(token, str) or not token.strip():
                        continue
                        
                    # Skip parameter column for lab data
                    if options.get('skip_first') and i == first_entry[0]:
                        continue
                        
                    # Clean token
                    clean_token = token.strip().replace(",", ".")
                    if options.get('clean_lab'):
                        clean_token = clean_token.replace("(-)", "").replace("(+)", "")
                        
                    try:
                        value = float(clean_token)
                    except (ValueError, TypeError):
                        value = clean_token
                        
                    # Get timestamp
                    try:
                        timestamp = self._parse_timestamp(timestamps[i])
                        if not timestamp:
                            continue
                    except (IndexError, TypeError):
                        continue
                        
                    # Clean category name
                    category = key.replace("Labor:", "").strip() if "Labor:" in key else key.strip()
                    
                    data_list.append(data_class(
                        timestamp=timestamp,
                        value=value,
                        category=category,
                        parameter=first_entry[1]
                    ))

        return pd.DataFrame([item.__dict__ for item in data_list])
