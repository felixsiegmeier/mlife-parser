"""
Update-Checker für mLife Parser.
Prüft auf GitHub, ob eine neuere Version verfügbar ist.
"""

import urllib.request
import urllib.error
import json
import threading
from typing import Optional, Tuple, Callable
from dataclasses import dataclass

# GitHub API Endpoint für das neueste Release
# Hinweis: /releases/latest gibt nur "echte" Releases zurück, keine Prereleases
# Daher verwenden wir /releases und nehmen das erste Element
GITHUB_REPO = "felixsiegmeier/mlife-parser"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases"

# Aktuelle Version (wird aus pyproject.toml gelesen oder hier als Fallback)
CURRENT_VERSION = "1.0.0"


@dataclass
class UpdateInfo:
    """Informationen über ein verfügbares Update."""
    current_version: str
    latest_version: str
    download_url: str
    release_notes: str
    is_update_available: bool


def _parse_version(version_str: str) -> Tuple[int, ...]:
    """
    Parst eine Versionsstring in ein vergleichbares Tuple.
    Unterstützt Formate wie: 1.0.0, v1.0.0, 1.0.0-beta, v1.2.3-rc1
    """
    # Entferne 'v' Prefix falls vorhanden
    version = version_str.lower().strip()
    if version.startswith('v'):
        version = version[1:]
    
    # Entferne Suffix wie -beta, -rc1, etc. für den Vergleich
    # Beta/RC Versionen werden als kleiner betrachtet
    is_prerelease = False
    for suffix in ['-beta', '-alpha', '-rc', '-dev']:
        if suffix in version:
            version = version.split(suffix)[0]
            is_prerelease = True
            break
    
    # Parse die Versionsnummern
    try:
        parts = [int(p) for p in version.split('.')]
        # Füge 0 hinzu für Prerelease (damit 1.0.0-beta < 1.0.0)
        if is_prerelease:
            parts.append(0)
        else:
            parts.append(1)
        return tuple(parts)
    except ValueError:
        return (0, 0, 0, 0)


def _is_newer_version(current: str, latest: str) -> bool:
    """Prüft, ob latest neuer als current ist."""
    current_tuple = _parse_version(current)
    latest_tuple = _parse_version(latest)
    return latest_tuple > current_tuple


def get_current_version() -> str:
    """
    Liest die aktuelle Version aus pyproject.toml oder gibt Fallback zurück.
    """
    import os
    import sys
    
    # Bestimme den Basispfad
    if getattr(sys, 'frozen', False):
        # PyInstaller: Version ist eingebaut
        return CURRENT_VERSION
    else:
        # Entwicklungsmodus: Versuche pyproject.toml zu lesen
        try:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            pyproject_path = os.path.join(base_path, "pyproject.toml")
            
            if os.path.exists(pyproject_path):
                with open(pyproject_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip().startswith('version'):
                            # Parse: version = "1.0.0"
                            version = line.split('=')[1].strip().strip('"').strip("'")
                            return version
        except Exception:
            pass
    
    return CURRENT_VERSION


def check_for_update() -> Optional[UpdateInfo]:
    """
    Prüft auf GitHub, ob eine neuere Version verfügbar ist.
    
    Returns:
        UpdateInfo wenn erfolgreich, None bei Fehler oder wenn keine Verbindung.
    """
    current_version = get_current_version()
    
    try:
        # GitHub API Request mit Timeout
        request = urllib.request.Request(
            GITHUB_API_URL,
            headers={
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': f'mlife-parser/{current_version}'
            }
        )
        
        with urllib.request.urlopen(request, timeout=5) as response:
            releases = json.loads(response.read().decode('utf-8'))
        
        # Prüfe ob Releases vorhanden
        if not releases or not isinstance(releases, list) or len(releases) == 0:
            return None
        
        # Nehme das erste (neueste) Release (inkl. Prereleases)
        data = releases[0]
        
        latest_version = data.get('tag_name', '')
        release_notes = data.get('body', '')[:500] if data.get('body') else ''
        
        # Suche nach dem Download-Link (Windows .exe oder generischer Link)
        download_url = data.get('html_url', f'https://github.com/{GITHUB_REPO}/releases/latest')
        
        # Prüfe ob Update verfügbar
        is_update = _is_newer_version(current_version, latest_version)
        
        return UpdateInfo(
            current_version=current_version,
            latest_version=latest_version,
            download_url=download_url,
            release_notes=release_notes,
            is_update_available=is_update
        )
        
    except urllib.error.HTTPError:
        # 404 = Kein Release vorhanden
        return None
    except urllib.error.URLError:
        # Keine Internetverbindung oder Firewall
        return None
    except json.JSONDecodeError:
        # Ungültige API-Antwort
        return None
    except Exception:
        # Sonstige Fehler still ignorieren
        return None


def check_for_update_async(callback: Callable[[Optional[UpdateInfo]], None]) -> None:
    """
    Prüft asynchron auf Updates und ruft den Callback mit dem Ergebnis auf.
    
    Args:
        callback: Funktion die mit UpdateInfo oder None aufgerufen wird.
    """
    def check_thread():
        result = check_for_update()
        callback(result)
    
    thread = threading.Thread(target=check_thread, daemon=True)
    thread.start()
