from .medication import MedicationParserMixin
from .fluid_balance import FluidBalanceParserMixin
from .all_patient_data import AllPatientDataParserMixin
from .respiratory import RespiratoryParserMixin
from .vitals import VitalsParserMixin
from .lab import LabParserMixin
from .patient_info import PatientInfoParserMixin

class DataParser(
    MedicationParserMixin,
    FluidBalanceParserMixin,
    AllPatientDataParserMixin,
    RespiratoryParserMixin,
    VitalsParserMixin,
    LabParserMixin,
    PatientInfoParserMixin,
):
    """
    Hauptklasse für das Parsing (Fassade).
    
    Diese Klasse führt alle spezialisierten Mixins zusammen.
    Durch die Vererbung stehen alle Methoden (z.B. parse_medication_logic, parse_respiratory_data)
    in dieser einen Klasse zur Verfügung.
    
    Verwendung:
        parser = DataParser("datei.csv")
        df_meds = parser.parse_medication_logic()
    """
    pass
