from mlife_core.schemas.parse_schemas.base import BaseDataModel
from typing import Optional


class FluidBalanceModel(BaseDataModel):
    time_range: Optional[str] = None  # e.g., "10.09.2025 11:00 - 15.09.2025 07:59"