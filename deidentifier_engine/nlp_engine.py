import spacy
import sys
import os
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

# Ermittle den Pfad zum Modell
# Fallback für PyInstaller (falls wir es doch packen wollen), aber sauberer
if getattr(sys, 'frozen', False):
    model_path = os.path.join(sys._MEIPASS, "de_core_news_lg")
else:
    model_path = "de_core_news_lg"

print(f"Lade spaCy Modell: {model_path}")

# Konfiguration des NLP-Engines
provider = NlpEngineProvider(nlp_configuration={
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "de", "model_name": model_path}]
})

# Initialisierung der Engines
try:
    nlp_engine = provider.create_engine()
    
    # Erhöhe das Zeichenlimit für spaCy (Standard ist 1.000.000)
    # Wir setzen es auf 10.000.000, um auch sehr lange Dokumente zu verarbeiten
    # Wir nutzen getattr, da 'nlp' nicht offiziell im Basis-Interface definiert ist
    spacy_nlp_dict = getattr(nlp_engine, "nlp", None)
    if spacy_nlp_dict and "de" in spacy_nlp_dict:
        spacy_nlp_dict["de"].max_length = 10000000
        print(f"spaCy max_length auf {spacy_nlp_dict['de'].max_length} erhöht.")
        
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["de"])
    anonymizer = AnonymizerEngine()
    print("Presidio Analyzer & Anonymizer erfolgreich initialisiert.")
except Exception as e:
    print(f"Fehler beim Initialisieren der NLP Engine: {e}")
    print("Tipp: Stelle sicher, dass 'de_core_news_lg' installiert ist.")
    raise e
