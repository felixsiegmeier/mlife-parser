from mlife_core.schemas.parse_schemas.base import BaseDataModel
from pydantic import Field
from typing import Optional
from datetime import datetime

class MedicationModel(BaseDataModel):
    """
    Model for medication data.
    Inherited mapping:
    - timestamp -> start time of medication/infusion
    - parameter -> name of the medication
    - value     -> rate (for infusions) or concentration/dose (for bolus/single doses)
    """
    application: Optional[str] = Field(..., description="Kind of application")
    stop: Optional[datetime | None] = Field(None, description="Timestamp of infusion stop")
    concentration: Optional[str] = Field(None, description="Concentration of the medication")
    rate: Optional[float | None] = Field(None, description="Infusion rate of the medication")

    class Config:
        from_attributes = True
