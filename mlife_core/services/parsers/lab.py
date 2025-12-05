from __future__ import annotations
import pandas as pd

from .standard_table import StandardTableParser
from mlife_core.schemas.parse_schemas.lab import LabModel

class LabParserMixin(StandardTableParser):
    """
    Mixin für Labordaten.
    """
    def parse_lab(self) -> pd.DataFrame:
        """Parst die Labordaten."""
        return self._parse_table_data("Labor", LabModel, skip_first=True, clean_lab=True)
