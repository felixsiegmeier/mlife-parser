# mLife Data Parser

Ein Tool zur Konsolidierung und Transformation von medizinischen Patientendaten (CSV) in ein einheitliches "Long Format" (Tidy Data).

## Features

- **Parsing**: Liest komplexe, heterogene CSV-Exportdateien (mLife).
- **Konsolidierung**: Führt Vitaldaten, Labordaten, Beatmung, Medikamente, Bilanzierung und Gerätedaten (ECMO, Impella, CRRT, NIRS) zusammen.
- **Formatierung**: Gibt eine bereinigte CSV-Datei im Long Format aus (`timestamp`, `source_type`, `category`, `parameter`, `value`).
- **Validierung**: Nutzt Pydantic-Modelle zur Sicherstellung der Datenintegrität.

## Installation

1. Repository klonen.
2. Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   # oder mit uv
   uv sync
   ```

## Nutzung

### Kommandozeile (CLI)

```bash
python cli.py <input_file> [-o output.csv]
```

Beispiel:
```bash
python cli.py data/gesamte_akte.csv -o mein_export.csv
```

### Grafische Oberfläche (GUI)

Startet eine minimale Benutzeroberfläche zur Dateiauswahl:

```bash
python main.py
```

### Programmatische Nutzung

```python
from mlife_core.services.pipeline import run_parsing_pipeline

df = run_parsing_pipeline("data/gesamte_akte.csv")
print(df.head())
```

Für detaillierte Beispiele siehe `testbook.ipynb`.

## Projektstruktur

```
.
├── cli.py                      # CLI Einstiegspunkt
├── main.py                     # GUI Einstiegspunkt (Flet)
├── testbook.ipynb              # Beispiel-Notebook zur Anwendung
├── mlife_core/                 # Kern-Bibliothek
│   ├── services/
│   │   ├── pipeline.py         # Orchestrierung des Parsing-Prozesses
│   │   └── parsers/            # Parser-Module (Mixins)
│   │       ├── base.py         # Basisklasse für alle Parser
│   │       ├── vitals.py       # Vitaldaten-Parser
│   │       ├── lab.py          # Labor-Parser
│   │       ├── medication.py   # Medikamenten-Parser
│   │       ├── respiratory.py  # Beatmungs-Parser
│   │       ├── fluid_balance.py# Bilanz-Parser
│   │       ├── all_patient_data.py # Geräte, Scores, etc.
│   │       └── patient_info.py # Patienteninfo-Parser
│   ├── schemas/
│   │   └── parse_schemas/      # Pydantic Datenmodelle
│   │       ├── base.py         # Basisklasse (BaseDataModel)
│   │       ├── vitals.py
│   │       ├── lab.py
│   │       ├── medication.py
│   │       └── ...
│   └── utils/
│       ├── export.py           # Export-Hilfsfunktionen
│       └── formatters.py       # Formatierungs-Utilities
├── ui/                         # Flet GUI-Komponenten
│   ├── app_state.py            # Anwendungsstatus
│   └── tabs/                   # Tab-Komponenten
│       ├── overview.py
│       ├── quick_export.py
│       └── custom_export.py
├── deidentifier_engine/        # Anonymisierung (in Entwicklung)
│   ├── anonymizer.py
│   └── nlp_engine.py
└── data/                       # Beispieldaten
```

## Datenmodell

Alle Daten werden auf ein gemeinsames Schema gemappt:

- `timestamp`: Zeitpunkt der Messung/Handlung
- `source_type`: Herkunft (z.B. "Vitals", "Lab", "Medication")
- `category`: Unterkategorie (z.B. "Blutgase", "Katecholamine")
- `parameter`: Name des Parameters (z.B. "pH", "Norepinephrin")
- `value`: Numerischer Wert oder Textwert

Zusätzliche Felder (z.B. für Medikamente: `rate`, `concentration`) sind im Modell vorhanden und werden bei Bedarf mit ausgegeben.
