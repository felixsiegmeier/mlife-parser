import spacy
import subprocess
import sys
import os
import tarfile
import shutil
import tempfile
import urllib.request
import ssl
import socket
import time
import threading
from typing import Optional, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

# Standard-Modellname und Version
DEFAULT_MODEL_NAME = "de_core_news_lg"
MODEL_VERSION = "3.7.0"
MODEL_URL = f"https://github.com/explosion/spacy-models/releases/download/{DEFAULT_MODEL_NAME}-{MODEL_VERSION}/{DEFAULT_MODEL_NAME}-{MODEL_VERSION}.tar.gz"

# Download-Konfiguration
CONNECTION_TIMEOUT = 15  # 15 Sekunden für initiale Verbindung
READ_TIMEOUT = 30  # 30 Sekunden Timeout wenn keine Daten kommen

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


def _check_connectivity() -> Tuple[bool, str]:
    """
    Schneller Konnektivitätstest zu GitHub (max 10 Sekunden).
    Testet nur ob der Host erreichbar ist, nicht den vollständigen Download.
    """
    test_host = "github.com"
    test_port = 443
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((test_host, test_port))
        sock.close()
        
        if result == 0:
            return True, "Verbindung OK"
        else:
            return False, f"Verbindung zu {test_host} fehlgeschlagen (Code: {result})"
    except socket.timeout:
        return False, "Verbindungs-Timeout: Server nicht erreichbar"
    except socket.gaierror as e:
        return False, f"DNS-Fehler: {str(e)}"
    except Exception as e:
        return False, f"Netzwerkfehler: {str(e)}"


def download_model_with_progress(
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Tuple[bool, str]:
    """
    Lädt das spaCy-Modell direkt von GitHub herunter (für --onefile Builds).
    Prüft zuerst die Konnektivität mit schnellem Timeout.
    
    Args:
        progress_callback: Optionale Callback-Funktion mit (progress: 0.0-1.0, status_text: str)
    
    Returns:
        Tuple aus (Erfolg: bool, Nachricht: str)
    """
    model_dir = get_model_directory()
    
    # Modell-Verzeichnis erstellen
    try:
        os.makedirs(model_dir, exist_ok=True)
    except Exception as e:
        return False, f"Konnte Verzeichnis nicht erstellen: {str(e)}"
    
    if progress_callback:
        progress_callback(0.0, "Prüfe Netzwerkverbindung...")
    
    # SCHNELLER Konnektivitätstest zuerst (max 10 Sekunden)
    connectivity_ok, connectivity_msg = _check_connectivity()
    if not connectivity_ok:
        return False, f"Keine Verbindung zu GitHub möglich: {connectivity_msg}. Bitte prüfen Sie Ihre Firewall-Einstellungen."
    
    if progress_callback:
        progress_callback(0.01, "Verbindung OK - starte Download...")
    
    # Temporäre Datei für den Download
    tmp_path = None
    
    try:
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        # Thread-basierter Download mit hartem Timeout
        download_result = {'success': False, 'error': None, 'response': None}
        
        def try_connect():
            """Versucht die Verbindung herzustellen."""
            try:
                ssl_context = ssl.create_default_context()
                request = urllib.request.Request(
                    MODEL_URL,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) mlife-parser/1.0'}
                )
                # Sehr kurzer Socket-Timeout
                socket.setdefaulttimeout(CONNECTION_TIMEOUT)
                response = urllib.request.urlopen(request, timeout=CONNECTION_TIMEOUT, context=ssl_context)
                download_result['response'] = response
                download_result['success'] = True
            except Exception as e:
                download_result['error'] = str(e)
        
        # Verbindung in separatem Thread mit hartem Timeout
        connect_thread = threading.Thread(target=try_connect, daemon=True)
        connect_thread.start()
        connect_thread.join(timeout=CONNECTION_TIMEOUT + 5)  # Etwas mehr Zeit als Socket-Timeout
        
        if connect_thread.is_alive() or not download_result['success']:
            # Thread hängt noch oder Verbindung fehlgeschlagen
            error_msg = download_result.get('error', 'Verbindungs-Timeout - Server antwortet nicht')
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass
            return False, f"Netzwerkfehler: {error_msg}. Bitte prüfen Sie Ihre Firewall-Einstellungen."
        
        # Verbindung erfolgreich - jetzt downloaden
        response = download_result['response']
        if response is None:
            return False, "Verbindung fehlgeschlagen - keine Server-Antwort erhalten."
        
        if progress_callback:
            progress_callback(0.02, "Verbunden - starte Download...")
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        block_size = 512 * 1024  # 512 KB Blöcke für häufigere Updates
        last_progress_time = time.time()
        
        with open(tmp_path, 'wb') as out_file:
            while True:
                # Timeout-Check: Wenn seit 30 Sekunden keine Daten kamen, abbrechen
                current_time = time.time()
                
                try:
                    # Setze Socket-Timeout für jeden Read
                    if hasattr(response, 'fp') and hasattr(response.fp, 'raw'):
                        response.fp.raw._sock.settimeout(READ_TIMEOUT)
                    buffer = response.read(block_size)
                except socket.timeout:
                    response.close()
                    if tmp_path and os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except:
                            pass
                    return False, "Download-Timeout: Keine Daten empfangen. Verbindung möglicherweise blockiert."
                except Exception as e:
                    response.close()
                    if tmp_path and os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except:
                            pass
                    return False, f"Download-Fehler: {str(e)}"
                
                if not buffer:
                    break
                
                downloaded += len(buffer)
                out_file.write(buffer)
                last_progress_time = current_time
                
                if total_size > 0 and progress_callback:
                    progress = min(downloaded / total_size, 1.0) * 0.95
                    downloaded_mb = downloaded / (1024 * 1024)
                    total_mb = total_size / (1024 * 1024)
                    progress_callback(progress, f"Lade herunter: {downloaded_mb:.1f} / {total_mb:.1f} MB")
        
        response.close()
        
        # Prüfen ob Download vollständig
        if total_size > 0 and downloaded < total_size:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass
            return False, f"Download unvollständig: {downloaded}/{total_size} Bytes"
        
        if progress_callback:
            progress_callback(0.96, "Entpacke Modell...")
        
        # Entpacken
        print(f"Entpacke nach {model_dir}...")
        with tarfile.open(tmp_path, "r:gz") as tar:
            tar.extractall(model_dir)
        
        if progress_callback:
            progress_callback(1.0, "Fertig!")
        
        print(f"Modell erfolgreich installiert in {model_dir}")
        
        # Temporäre Datei löschen
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        
        return True, "Modell erfolgreich heruntergeladen und installiert."
        
    except tarfile.TarError as e:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass
        return False, f"Fehler beim Entpacken: {str(e)}"
        
    except Exception as e:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass
        return False, f"Unerwarteter Fehler: {str(e)}"


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
