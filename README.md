# mLife Data Parser

Ein Tool zur strukturierten Erfassung, Anonymisierung und Konsolidierung von medizinischen Patientendaten aus dem PDMS mLife (Charitéhaus Digital Zentrums für Chirurgie – DHZC).

**Entwickelt mit Fokus auf Datenschutz**: Alle Patientendaten werden mittels NLP-basierter Erkennung und manueller Blacklist-Filterung anonymisiert.

---

## � Anonymisierung

Das Tool bietet zwei Modi: reines **Parsing** (ohne Anonymisierung) und **Anonymisierung mit NLP + Blacklist**.

### Parsing (Standard)
- CLI und "Quick Export": Nur Datenextraktion und Strukturierung
- **Keine Modifikation** von Patientendaten

### Anonymisierung (optional, GUI-Modus)

Bei Aktivierung wird ein zweistufiger Prozess angewandt:

**1. NLP-basierte Erkennung** (Presidio + spaCy de_core_news_lg)
- Automatische Erkennung von Personennamen, Telefonnummern, E-Mail-Adressen
- Gilt für Freitextfelder: Arztnotizen, Anamnese, Visite, Status, Bronchoskopie, etc.
- Ersetzung: `<ANONYM>` (Namen) oder `<KONTAKT>` (Kontaktdaten)

**2. Blacklist-Filterung** (mit Fuzzy-Matching)
- Nutzerbasierte Konfiguration für institutionsspezifische Begriffe
- Fuzzy-Schwellwert: 85% Ähnlichkeit (erkennt Tippfehler, Variationen)
- Ersetzung: `<ANONYM>`

**Ausnahmen:**
- Numerische Werte: Immer unverändert
- Texte <5 Zeichen: Nicht anonymisiert (z.B. "ja", "nein")
- Strukturierte Daten (Vitals, Lab): Nur Blacklist-Ersetzung, falls konfiguriert

### Technische Aspekte

- **Verarbeitung**: Lokal auf der Maschine (kein Upload zu Servern)
- **NLP-Modell**: Lokal gespeichert, offline verfügbar
- **Erkennungsgenauigkeit**: ~95–98% (basierend auf trainiertem Modell)
- **Limitationen**: Kontextabhängige Erkennungsfehler möglich, Namen in Sonderkontexten können übersehen werden

---

## 🔄 Programm-Flow

### Ablauf beim Start

```
GUI/CLI-Start
    ↓
[Input] ← Unstrukturierte mLife CSV-Export (Patientenakte)
    ↓
┌─────────────────────────────────────────┐
│  PARSING-PHASE (mlife_core/services)    │
├─────────────────────────────────────────┤
│ 1. Vitaldaten (Puls, Blutdruck, Sättigung)
│ 2. Labordaten (Blutgas, Chemie, etc.)
│ 3. Beatmungsdaten (Respirator, Parameter)
│ 4. Gerätedaten (ECMO, Impella, CRRT, NIRS)
│ 5. Bilanzierungsdaten (Ein-/Ausfuhr)
│ 6. Medikamenten-Gaben
│ 7. Statische Patienteninfo
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  STRUKTURIERUNG                         │
│  → Long Format (Tidy Data)              │
│  Spalten:                               │
│  - timestamp (zeitlich sortiert)        │
│  - source_type (Herkunft)               │
│  - category (Kategorie)                 │
│  - parameter (Messgröße)                │
│  - value (Wert)                         │
└─────────────────────────────────────────┘
    ↓
[Optional: Anonymisierung]
    ↓
┌─────────────────────────────────────────┐
│  ANONYMISIERUNGS-PHASE (optional)       │
│  (nur wenn aktiviert)                   │
├─────────────────────────────────────────┤
│ Für Freitextfelder:                     │
│  1. NLP-Analyzer (Presidio)             │
│     → Erkennt PERSON, PHONE, EMAIL      │
│  2. Anonymizer                          │
│     → Ersetzt erkannte Entitäten        │
│  3. Blacklist-Filter (Fuzzy)            │
│     → Entfernt user-definierte Begriffe │
│                                         │
│ Für andere Felder:                      │
│  - Nur Blacklist-Filterung (wenn vorhanden)
│  - Numerische Werte: unverändert        │
│  - Kurze Texte (<5 Zeichen): unverändert
└─────────────────────────────────────────┘
    ↓
[Output] → CSV im Long Format
           (mit oder ohne Anonymisierung)
```

### Einstiegspunkte

1. **Kommandozeile (CLI)**
   ```bash
   python cli.py <input.csv> -o <output.csv>
   ```
   - Reiner Parsing-Prozess (KEINE Anonymisierung)
   - Schnelle, serverlose Verarbeitung

2. **Grafische Oberfläche (GUI)**
   ```bash
   python main.py
   ```
   - Tabs für unterschiedliche Aufgaben:
     - **Overview**: Daten-Statistik, Parsing-Validierung
     - **Quick Export**: Standard-Parsing
     - **Anonymize**: Aktiviert NLP-Engine + Blacklist-Filterung
     - **Custom Export**: Erweiterte Optionen

3. **Programmatisch**
   ```python
   from mlife_core.services.pipeline import run_parsing_pipeline
   df = run_parsing_pipeline("data/patient.csv")
   ```

---

## 📦 Installation & Nutzung

### Installation

```bash
# Repository klonen
git clone <repo>
cd mlife-parser

# Abhängigkeiten installieren
pip install -r requirements.txt
# oder mit uv:
uv sync
```

### Schnellstart: GUI

```bash
python main.py
```

Der spaCy-Anonymisierungsmodell wird beim ersten Öffnen der "Anonymize"-Tab automatisch heruntergeladen (~500 MB).

### Schnellstart: CLI (Parsing ohne Anonymisierung)

```bash
python cli.py data/gesamte_akte.csv -o output.csv
```

---

## 📁 Projektstruktur

```
mlife-parser/
├── cli.py                              # Kommandozeilen-Einstiegspunkt
├── main.py                             # GUI-Einstiegspunkt (Flet Framework)
├── requirements.txt                    # Python-Abhängigkeiten
│
├── mlife_core/                         # Kern-Parsing-Bibliothek
│   ├── services/
│   │   ├── pipeline.py                 # Orchestrierung: Parsing → Konsolidierung
│   │   └── parsers/                    # Datentyp-spezifische Parser
│   │       ├── base.py                 # Basis-Parser-Klasse
│   │       ├── vitals.py               # Vitaldaten-Parser
│   │       ├── lab.py                  # Labor-Parser
│   │       ├── medication.py           # Medikamenten-Parser
│   │       ├── respiratory.py          # Beatmungs-Parser
│   │       ├── fluid_balance.py        # Bilanzierungs-Parser
│   │       ├── all_patient_data.py     # Geräte + Scores
│   │       └── patient_info.py         # Statische Patienteninfo
│   ├── schemas/                        # Pydantic Datenmodelle (Validierung)
│   │   └── parse_schemas/
│   │       ├── base.py
│   │       ├── vitals.py, lab.py, medication.py, etc.
│   └── utils/
│       ├── export.py                   # CSV-Export-Funktionen
│       └── formatters.py               # Formatierungs-Utilities
│
├── deidentifier_engine/                # Anonymisierungs-Modul
│   ├── anonymizer.py                   # Hauptlogik: NLP + Blacklist
│   └── nlp_engine.py                   # spaCy-Modellverwaltung (Presidio)
│
├── ui/                                 # Grafische Benutzeroberfläche (Flet)
│   ├── app_state.py                    # Globale App-State-Verwaltung
│   ├── tabs/
│   │   ├── overview.py                 # Daten-Übersicht
│   │   ├── anonymize.py                # Anonymisierungs-Interface
│   │   ├── quick_export.py             # Schneller Export
│   │   └── custom_export.py            # Benutzerdefinierter Export
│   └── dialogs/                        # Modal Dialoge
│
├── spacy_models/                       # Lokal installierte NLP-Modelle
│   └── de_core_news_lg-3.7.0/          # Deutsche spaCy Pipeline
│
└── storage/                            # Temporäre Dateien
    ├── data/                           # Verarbeitete Daten
    └── temp/                           # Cache
```

---

## � Verwendete Technologien

Alle geparsten Daten werden in ein einheitliches "Long Format" (Tidy Data) transformiert:

| Spalte | Beschreibung | Beispiel |
|--------|-------------|----------|
| `timestamp` | Zeitpunkt der Messung | 2025-01-15 14:30:00 |
| `source_type` | Datenherkunft | "Vitals", "Lab", "Medication" |
| `category` | Kategorie | "Herz-Kreislauf", "Blutgas" |
| `parameter` | Messgröße | "Puls", "SpO₂", "Hämaglobin" |
| `value` | Messwert oder Text | "85", "97%", "<ANONYM>" |

Dieses Format ermöglicht:
- Zeitliche Sortierung und Analyse
- Flexible Filter- und Pivot-Operationen
- Datenbank-Import
- Visualisierung mit Standard-Tools

---

## 📚 Verwendete Technologien

| Komponente | Bibliothek | Zweck |
|-----------|-----------|-------|
| Parsing | Pandas | CSV-Verarbeitung, Datenmanipulation |
| Validierung | Pydantic | Type-Checking, Schema-Validierung |
| NLP-Anonymisierung | Presidio + spaCy | Erkennung von Personen/Kontaktinfo |
| UI | Flet | Cross-Platform GUI (macOS, Windows, Linux) |
| Fuzzy Matching | RapidFuzz | Ähnlichkeitserkennung für Blacklist |

---

## 🚀 Nutzungsbeispiele

### Beispiel 1: Standard-Parsing (CLI)

```bash
python cli.py patient_data.csv -o parsed_output.csv
# Output: strukturiertes Long Format CSV (nicht anonymisiert)
```

### Beispiel 2: Mit Anonymisierung (GUI)

1. `python main.py`
2. Tab "Anonymize" → CSV auswählen
3. Blacklist-Begriffe hinzufügen (optional)
4. "Anonymisieren" → Output-Datei wird erstellt

### Beispiel 3: Programmatisch

```python
from mlife_core.services.pipeline import run_parsing_pipeline
from deidentifier_engine import anonymize_dataframe

# Parsing
df = run_parsing_pipeline("patient.csv")

# Anonymisierung (mit Blacklist)
blacklist = ["Stationär ABC", "Prof. Dr. Schmidt"]
df_anon = anonymize_dataframe(df, blacklist=blacklist)
df_anon.to_csv("output_anonymized.csv", index=False)
```

---

## 📋 Anforderungen

- Python 3.9+
- macOS, Linux, oder Windows
- ~1 GB Speicher für spaCy-Modell
- Internet (nur für initialen Modell-Download)

