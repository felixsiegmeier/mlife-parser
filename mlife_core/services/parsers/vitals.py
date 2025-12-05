from __future__ import annotations
import pandas as pd

from .standard_table import StandardTableParser
from mlife_core.schemas.parse_schemas.vitals import VitalsModel

class VitalsParserMixin(StandardTableParser):
    """
    Mixin für Vitaldaten.
    """
    def parse_vitals(self) -> pd.DataFrame:
        """Parst die Vitaldaten."""
        return self._parse_table_data("Vitaldaten", VitalsModel)
