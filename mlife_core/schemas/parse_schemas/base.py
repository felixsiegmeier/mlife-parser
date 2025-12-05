from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime

class BaseDataModel(BaseModel):
    timestamp: datetime = Field(..., description="Timestamp of the measurement or event")
    category: str = Field(..., description="Category of the data (e.g. 'Vitaldaten', 'Labor', 'Medikamente')")
    parameter: str = Field(..., description="Name of the parameter or medication")
    value: Optional[Any] = Field(None, description="Value of the measurement")
    source_type: Optional[str] = Field(None, description="Origin source type (e.g. 'Vitals', 'Lab')")

    class Config:
        from_attributes = True
