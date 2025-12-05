import re
from typing import List, Optional
from presidio_analyzer import PatternRecognizer, Pattern
from presidio_anonymizer.entities import OperatorConfig
from .nlp_engine import analyzer, anonymizer

def create_name_pattern(p_name, regex_str):
    """Helper für Regex-Erstellung mit Word Boundaries"""
    return Pattern(name=p_name, regex=regex_str, score=1.0)

def create_patterns_for_name(name_str, label_prefix):
    """Funktion zum Erstellen von Patterns für einen Namen"""
    patterns = []
    clean = name_str.strip()
    if not clean:
        return patterns
        
    parts = clean.split()
    escaped_parts = [re.escape(p) for p in parts]
    
    if len(escaped_parts) >= 1:
        # Pattern: Exakte Eingabe
        full_name_regex = r"\b" + r"\s+".join(escaped_parts) + r"\b"
        patterns.append(create_name_pattern(f"{label_prefix}_Exact", full_name_regex))
    
    if len(escaped_parts) >= 2:
        lastname = escaped_parts[-1]
        firstname_parts = escaped_parts[:-1]
        firstname = r"\s+".join(firstname_parts)
        
        # Pattern: "Nachname, Vorname"
        p_last_first = r"\b" + lastname + r"\s*,\s*" + firstname + r"\b"
        patterns.append(create_name_pattern(f"{label_prefix}_LastFirst", p_last_first))
        
        # Pattern: "Nachname Vorname"
        p_last_first_no_comma = r"\b" + lastname + r"\s+" + firstname + r"\b"
        patterns.append(create_name_pattern(f"{label_prefix}_LastFirstNoComma", p_last_first_no_comma))
        
        # Pattern: Nur Nachname (wenn > 3 Zeichen)
        if len(parts[-1]) > 3:
            p_last_only = r"\b" + lastname + r"\b"
            patterns.append(create_name_pattern(f"{label_prefix}_LastOnly", p_last_only))
    return patterns

def sledgehammer_replace(txt: str, terms: List[str]) -> str:
    """
    Ersetzt alle Begriffe aus der Liste im Text (case-insensitive).
    """
    if not terms:
        return txt
    
    for term in terms:
        if not term or not term.strip():
            continue
        
        # Case-insensitive replacement
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        txt = pattern.sub("<ANONYM>", txt)
    
    return txt

def anonymize_content(text: str, blacklist_terms: List[str] = [], persistent_blacklist: List[str] = []) -> str:
    """
    Anonymisiert den gegebenen Text.
    
    Args:
        text: Der zu anonymisierende Text.
        blacklist_terms: Eine Liste von Begriffen (Namen, Daten), die definitiv entfernt werden sollen.
        persistent_blacklist: Eine Liste von Begriffen (Ärzte, Orte, etc.), die dauerhaft entfernt werden sollen.
    
    Returns:
        Der anonymisierte Text.
    """
    results = []
    if not text:
        return ""

    # Liste für Ad-hoc Recognizer (werden nur für diesen Aufruf genutzt)
    ad_hoc_recognizers = []

    # 1. Ad-hoc Regel: Blacklist Terms (als Deny-List für PERSON oder generisch)
    if blacklist_terms:
        bl_recognizer = PatternRecognizer(
            supported_entity="PERSON",
            deny_list=blacklist_terms,
            name="BlacklistRecognizer"
        )
        ad_hoc_recognizers.append(bl_recognizer)

    # 2. Ad-hoc Regel: Persistente Blacklist
    if persistent_blacklist:
        doc_patterns = []
        for i, doc in enumerate(persistent_blacklist):
            doc_patterns.extend(create_patterns_for_name(doc, f"Persistent_{i}"))
        
        if doc_patterns:
            doc_recognizer = PatternRecognizer(
                supported_entity="PERSON",
                patterns=doc_patterns,
                name="PersistentBlacklistRecognizer"
            )
            ad_hoc_recognizers.append(doc_recognizer)

    # Analyse durchführen
    results = analyzer.analyze(
        text=text,
        language='de',
        entities=["PERSON", "DATE_TIME", "SENSITIVE_DATE", "PHONE_NUMBER", "EMAIL_ADDRESS"],
        ad_hoc_recognizers=ad_hoc_recognizers
    )

    # Konfiguration der Anonymisierung
    operators = {
        "PERSON": OperatorConfig("replace", {"new_value": "<ANONYM>"}),
        "SENSITIVE_DATE": OperatorConfig("replace", {"new_value": "<GD>"}),
        "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<KONTAKT>"}),
        "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<KONTAKT>"}),
        "DEFAULT": OperatorConfig("keep")
    }

    anonymized_result = anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators=operators
    )
    
    final_text = anonymized_result.text

    # Blacklist hämmern
    if blacklist_terms:
        final_text = sledgehammer_replace(final_text, blacklist_terms)
        
    # Persistente Blacklist hämmern
    if persistent_blacklist:
        final_text = sledgehammer_replace(final_text, persistent_blacklist)

    return final_text
