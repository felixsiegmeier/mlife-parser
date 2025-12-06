import re
from typing import List, Optional, Callable
import pandas as pd
from presidio_anonymizer.entities import OperatorConfig
from rapidfuzz import fuzz
from .nlp_engine import get_analyzer, get_anonymizer


# Kategorien die Freitext mit potenziell sensiblen Daten enthalten
# Diese werden mit NLP-Anonymisierung verarbeitet
FREETEXT_SOURCE_TYPES = [
    "Arztnotizen",
    "Anamnese",
    "Visite",
    "Status",
    "Anästhesieübergabe",
    "Kardiotechnik (Notizen)",
    "Mikrobiologie",
    "Atmungstherapie",
    "Bronchoskopie",
    "Meilensteine",
    "Visite durchgeführt von",
    "weitere TeilnehmerInnen",
    "fachärztliche Behandlungsleitung",
    "fachärztliche Behandlungsleitung (WDA1I, WD4I)",
    "Anästhesiepflege",
    "HK Befund",
    "Reanimation",
    "Verbal Rate Skala",
    "Intensivmedizin",
    "Operation/Datum/Operateur",
    "Therapieplanung Folgewoche/Ziele/Sonstiges",
    "Behandlungsergebnisse/akt. Situation",
]


def blacklist_replace(txt: str, terms: List[str], fuzzy_matching: bool = True, fuzzy_threshold: int = 85) -> str:
    """
    Ersetzt alle Begriffe aus der Blacklist im Text (case-insensitive).
    
    Args:
        txt: Der zu bearbeitende Text.
        terms: Liste von Begriffen, die entfernt werden sollen.
        fuzzy_matching: Wenn True, werden auch ähnliche Begriffe erkannt (Tippfehler, Buchstabendreher).
        fuzzy_threshold: Schwellwert für Fuzzy Matching (0-100). Höher = strenger.
    
    Returns:
        Der bearbeitete Text mit ersetzten Begriffen.
    """
    if not terms or not txt:
        return txt
    
    # Bereinigte Terms (keine leeren Einträge)
    clean_terms = [t.strip() for t in terms if t and t.strip()]
    if not clean_terms:
        return txt
    
    if not fuzzy_matching:
        # Einfache case-insensitive Ersetzung
        for term in clean_terms:
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            txt = pattern.sub("<ANONYM>", txt)
        return txt
    
    # Fuzzy Matching: Text in Wörter aufteilen und prüfen
    # Wir behalten Trennzeichen bei, um den Text rekonstruieren zu können
    tokens = re.split(r'(\s+|[,;.!?:\-\(\)\[\]\"\']+)', txt)
    
    result_tokens = []
    for token in tokens:
        # Leere Tokens oder reine Trennzeichen überspringen
        if not token or not token.strip() or re.match(r'^[\s,;.!?:\-\(\)\[\]\"\']+$', token):
            result_tokens.append(token)
            continue
        
        # Prüfen ob Token einem Blacklist-Begriff ähnelt
        should_replace = False
        for term in clean_terms:
            # Exakte Übereinstimmung (case-insensitive)
            if token.lower() == term.lower():
                should_replace = True
                break
            
            # Fuzzy Matching nur bei ähnlicher Länge (Performance)
            if abs(len(token) - len(term)) <= 2:
                similarity = fuzz.ratio(token.lower(), term.lower())
                if similarity >= fuzzy_threshold:
                    should_replace = True
                    break
        
        if should_replace:
            result_tokens.append("<ANONYM>")
        else:
            result_tokens.append(token)
    
    return "".join(result_tokens)


def anonymize_content(text: str, blacklist: List[str] = [], fuzzy_matching: bool = True, fuzzy_threshold: int = 85) -> str:
    """
    Anonymisiert den gegebenen Text.
    
    Args:
        text: Der zu anonymisierende Text.
        blacklist: Eine Liste von Begriffen, die entfernt werden sollen (bereits bereinigte Wörter).
        fuzzy_matching: Wenn True, werden auch ähnliche Begriffe erkannt (Tippfehler, Buchstabendreher).
        fuzzy_threshold: Schwellwert für Fuzzy Matching (0-100). Höher = strenger. Standard: 85.
    
    Returns:
        Der anonymisierte Text.
    """
    if not text:
        return ""

    # Presidio-Analyse durchführen (erkennt automatisch Personen, Daten, etc.)
    results = get_analyzer().analyze(
        text=text,
        language='de',
        entities=["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS"]
    )

    # Konfiguration der Anonymisierung
    operators = {
        "PERSON": OperatorConfig("replace", {"new_value": "<ANONYM>"}),
        "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<KONTAKT>"}),
        "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<KONTAKT>"}),
        "DEFAULT": OperatorConfig("keep")
    }

    anonymized_result = get_anonymizer().anonymize(
        text=text,
        analyzer_results=results,
        operators=operators
    )
    
    final_text = anonymized_result.text

    # Blacklist-Begriffe entfernen (mit optionalem Fuzzy Matching)
    if blacklist:
        final_text = blacklist_replace(final_text, blacklist, fuzzy_matching, fuzzy_threshold)

    return final_text


def anonymize_dataframe(
    df: pd.DataFrame,
    blacklist: List[str],
    fuzzy_matching: bool = True,
    fuzzy_threshold: int = 85,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> pd.DataFrame:
    """
    Anonymisiert einen DataFrame mit Patientendaten.
    
    - Freitext-Kategorien (Arztnotizen, Visite, etc.) werden mit NLP anonymisiert
    - Alle anderen Kategorien: Nur Blacklist-Ersetzung auf value-Spalte
    - Numerische Werte werden nicht verändert (Performance)
    
    Args:
        df: Der zu anonymisierende DataFrame.
        blacklist: Liste von Begriffen, die ersetzt werden sollen.
        fuzzy_matching: Wenn True, werden auch ähnliche Begriffe erkannt.
        fuzzy_threshold: Schwellwert für Fuzzy Matching (0-100).
        progress_callback: Optionale Callback-Funktion mit (progress: 0.0-1.0, status_text: str)
    
    Returns:
        Der anonymisierte DataFrame (Kopie des Originals).
    """
    if df is None or df.empty:
        return df
    
    # Kopie erstellen, um das Original nicht zu verändern
    df_anon = df.copy()
    
    # Prüfen ob 'value' und 'source_type' Spalten existieren
    if 'value' not in df_anon.columns:
        return df_anon
    
    has_source_type = 'source_type' in df_anon.columns
    
    # Blacklist bereinigen
    clean_blacklist = [t.strip() for t in blacklist if t and t.strip()]
    
    if not clean_blacklist and not has_source_type:
        # Keine Blacklist und keine source_type -> nichts zu tun
        return df_anon
    
    total_rows = len(df_anon)
    processed = 0
    
    # Freitext-Zeilen identifizieren (diese bekommen NLP-Anonymisierung)
    if has_source_type:
        freetext_mask = df_anon['source_type'].isin(FREETEXT_SOURCE_TYPES)
        freetext_indices = df_anon[freetext_mask].index.tolist()
    else:
        freetext_indices = []
    
    # Alle Zeilen mit nicht-leerem value-Feld
    value_mask = df_anon['value'].notna() & (df_anon['value'].astype(str).str.strip() != '')
    rows_to_process = df_anon[value_mask].index.tolist()
    
    if progress_callback:
        progress_callback(0.0, f"Anonymisiere {len(rows_to_process)} Einträge...")
    
    for idx in rows_to_process:
        value = df_anon.at[idx, 'value']
        
        # Numerische Werte überspringen
        if isinstance(value, (int, float)):
            processed += 1
            continue
        
        value_str = str(value)
        
        # Kurze Standardwerte überspringen (z.B. "ja", "nein", "durchgeführt")
        if len(value_str) < 5:
            processed += 1
            continue
        
        if idx in freetext_indices:
            # Freitext: NLP + Blacklist-Anonymisierung
            try:
                anonymized_value = anonymize_content(
                    value_str,
                    blacklist=clean_blacklist,
                    fuzzy_matching=fuzzy_matching,
                    fuzzy_threshold=fuzzy_threshold
                )
                df_anon.at[idx, 'value'] = anonymized_value
            except Exception as e:
                # Bei Fehler: Nur Blacklist-Ersetzung
                print(f"NLP-Fehler bei Zeile {idx}: {e}")
                if clean_blacklist:
                    df_anon.at[idx, 'value'] = blacklist_replace(
                        value_str, clean_blacklist, fuzzy_matching, fuzzy_threshold
                    )
        else:
            # Kein Freitext: Nur Blacklist-Ersetzung (falls Blacklist vorhanden)
            if clean_blacklist:
                df_anon.at[idx, 'value'] = blacklist_replace(
                    value_str, clean_blacklist, fuzzy_matching, fuzzy_threshold
                )
        
        processed += 1
        
        # Fortschritt alle 100 Zeilen aktualisieren
        if progress_callback and processed % 100 == 0:
            progress = processed / len(rows_to_process)
            progress_callback(progress, f"Anonymisiert: {processed} / {len(rows_to_process)}")
    
    if progress_callback:
        progress_callback(1.0, "Anonymisierung abgeschlossen.")
    
    return df_anon
