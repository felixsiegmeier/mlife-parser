import spacy
import subprocess
import sys
import os
import tarfile
import shutil
import tempfile
import urllib.request
from typing import Optional, Tuple, Callable

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

# Standard-Modellname und Version
DEFAULT_MODEL_NAME = "de_core_news_lg"
MODEL_VERSION = "3.7.0"
MODEL_URL = f"https://github.com/explosion/spacy-models/releases/download/{DEFAULT_MODEL_NAME}-{MODEL_VERSION}/{DEFAULT_MODEL_NAME}-{MODEL_VERSION}.tar.gz"

# Globale Engine-Instanzen (lazy initialized)
_analyzer: Optional[AnalyzerEngine] = None
_anonymizer: Optional[AnonymizerEngine] = None
_initialized: bool = False


def get_app_directory() -> str:
    """
    Ermittelt das Verzeichnis, in dem die App liegt.
    Bei PyInstaller --onefile ist das der Ordner der .exe, nicht der temp-Ordner.
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller: Ordner der ausführbaren Datei
        return os.path.dirname(sys.executable)
    else:
        # Entwicklungsmodus: Aktuelles Arbeitsverzeichnis
        return os.getcwd()


def get_model_directory() -> str:
    """Gibt den Pfad zum Modell-Verzeichnis zurück."""
    return os.path.join(get_app_directory(), "spacy_models")


def get_model_path() -> str:
    """Ermittelt den vollständigen Pfad zum spaCy-Modell."""
    model_dir = get_model_directory()
    # Das entpackte Modell liegt in einem Unterordner mit dem Modellnamen
    return os.path.join(model_dir, f"{DEFAULT_MODEL_NAME}-{MODEL_VERSION}", DEFAULT_MODEL_NAME, f"{DEFAULT_MODEL_NAME}-{MODEL_VERSION}")


def is_model_available() -> bool:
    """
    Prüft, ob das spaCy-Modell lokal verfügbar ist.
    
    Returns:
        True, wenn das Modell im App-Verzeichnis existiert, sonst False.
    """
    model_path = get_model_path()
    # Prüfen ob das Modell-Verzeichnis existiert und die meta.json vorhanden ist
    meta_path = os.path.join(model_path, "meta.json")
    return os.path.exists(meta_path)


def download_model_with_progress(
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Tuple[bool, str]:
    """
    Lädt das spaCy-Modell direkt von GitHub herunter (für --onefile Builds).
    
    Args:
        progress_callback: Optionale Callback-Funktion mit (progress: 0.0-1.0, status_text: str)
    
    Returns:
        Tuple aus (Erfolg: bool, Nachricht: str)
    """
    model_dir = get_model_directory()
    
    try:
        # Modell-Verzeichnis erstellen
        os.makedirs(model_dir, exist_ok=True)
        
        if progress_callback:
            progress_callback(0.0, "Starte Download...")
        
        # Temporäre Datei für den Download
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # Download mit Fortschrittsanzeige
            def reporthook(block_num, block_size, total_size):
                if total_size > 0 and progress_callback:
                    # Download nimmt 0-99% ein, Entpacken wird separat angezeigt
                    progress = min(block_num * block_size / total_size, 1.0) * 0.99
                    downloaded_mb = (block_num * block_size) / (1024 * 1024)
                    total_mb = total_size / (1024 * 1024)
                    progress_callback(progress, f"Lade herunter: {downloaded_mb:.1f} / {total_mb:.1f} MB")
            
            print(f"Lade Modell von {MODEL_URL}...")
            urllib.request.urlretrieve(MODEL_URL, tmp_path, reporthook)
            
            if progress_callback:
                progress_callback(0.99, "Entpacke Modell...")
            
            # Entpacken
            print(f"Entpacke nach {model_dir}...")
            with tarfile.open(tmp_path, "r:gz") as tar:
                tar.extractall(model_dir)
            
            if progress_callback:
                progress_callback(1.0, "Fertig!")
            
            print(f"Modell erfolgreich installiert in {model_dir}")
            return True, "Modell erfolgreich heruntergeladen und installiert."
            
        finally:
            # Temporäre Datei löschen
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    except urllib.error.URLError as e:
        error_msg = f"Netzwerkfehler beim Herunterladen: {str(e)}"
        print(error_msg)
        return False, error_msg
    except tarfile.TarError as e:
        error_msg = f"Fehler beim Entpacken: {str(e)}"
        print(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Unerwarteter Fehler: {str(e)}"
        print(error_msg)
        return False, error_msg


def download_model() -> Tuple[bool, str]:
    """
    Lädt das spaCy-Modell herunter (ohne Fortschrittsanzeige).
    
    Returns:
        Tuple aus (Erfolg: bool, Nachricht: str)
    """
    return download_model_with_progress(None)


def ensure_model_available(auto_download: bool = False) -> Tuple[bool, str]:
    """
    Stellt sicher, dass das spaCy-Modell verfügbar ist.
    
    Args:
        auto_download: Wenn True, wird das Modell automatisch heruntergeladen, falls es fehlt.
    
    Returns:
        Tuple aus (Verfügbar: bool, Nachricht: str)
    """
    if is_model_available():
        return True, f"Modell '{DEFAULT_MODEL_NAME}' ist verfügbar."
    
    if auto_download:
        return download_model()
    
    return False, f"Modell '{DEFAULT_MODEL_NAME}' ist nicht installiert. Bitte laden Sie es herunter."


def _initialize_engines() -> None:
    """Initialisiert die NLP-Engines (intern)."""
    global _analyzer, _anonymizer, _initialized
    
    if _initialized:
        return
    
    model_path = get_model_path()
    
    if not is_model_available():
        raise RuntimeError(
            f"spaCy-Modell nicht gefunden. "
            f"Bitte mit download_model() herunterladen."
        )
    
    print(f"Lade spaCy Modell: {model_path}")
    
    # Konfiguration des NLP-Engines mit lokalem Pfad
    provider = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "de", "model_name": model_path}]
    })
    
    nlp_engine = provider.create_engine()
    
    # Erhöhe das Zeichenlimit für spaCy (Standard ist 1.000.000)
    # Wir setzen es auf 10.000.000, um auch sehr lange Dokumente zu verarbeiten
    spacy_nlp_dict = getattr(nlp_engine, "nlp", None)
    if spacy_nlp_dict and "de" in spacy_nlp_dict:
        spacy_nlp_dict["de"].max_length = 10000000
        print(f"spaCy max_length auf {spacy_nlp_dict['de'].max_length} erhöht.")
    
    _analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["de"])
    _anonymizer = AnonymizerEngine()
    _initialized = True
    print("Presidio Analyzer & Anonymizer erfolgreich initialisiert.")


def get_analyzer() -> AnalyzerEngine:
    """
    Gibt die Analyzer-Instanz zurück (lazy initialization).
    
    Raises:
        RuntimeError: Wenn das spaCy-Modell nicht verfügbar ist.
    """
    if not _initialized:
        _initialize_engines()
    return _analyzer


def get_anonymizer() -> AnonymizerEngine:
    """
    Gibt die Anonymizer-Instanz zurück (lazy initialization).
    
    Raises:
        RuntimeError: Wenn das spaCy-Modell nicht verfügbar ist.
    """
    if not _initialized:
        _initialize_engines()
    return _anonymizer


def is_engine_initialized() -> bool:
    """Prüft, ob die Engines bereits initialisiert wurden."""
    return _initialized


def get_model_size_mb() -> float:
    """Gibt die ungefähre Größe des Modells in MB zurück (für UI-Anzeige)."""
    return 541.0  # de_core_news_lg ist ca. 541 MB
