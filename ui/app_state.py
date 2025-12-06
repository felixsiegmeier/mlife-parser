import pandas as pd
from typing import Callable, Optional

class AppState:
    def __init__(self):
        self.df: pd.DataFrame = None
        self.patient_name: str = None
        self.filepath: str = None
        self.is_anonymized: bool = False
        self.custom_export = {
            "standard_categories": set(),
            "other_sources": set()
        }
        # Temporary storage for export operations
        self.export_df: pd.DataFrame = None
        # Callback für Status-Updates nach Anonymisierung
        self.on_anonymization_complete: Optional[Callable[[], None]] = None
