from __future__ import annotations
import pandas as pd

from .standard_table import StandardTableParser
from mlife_core.schemas.parse_schemas.respiratory import RespiratoryModel

class RespiratoryParserMixin(StandardTableParser):
    """
    Mixin für Respirator-Daten.
    """
    def parse_respiratory_data(self) -> pd.DataFrame:
        """Parst die Respiratordaten."""
        return self._parse_table_data("Respiratordaten", RespiratoryModel)
