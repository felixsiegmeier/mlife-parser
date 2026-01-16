# PDMS Daten-Aggregationsübersicht

**Erstellt:** 09.01.2026  
**Zweck:** Übersicht für Gespräch mit PDMS-Administratoren zur Optimierung des Datenexports für Forschungszwecke

---

## Zusammenfassung

Der aktuelle PDMS-Export aggregiert Daten auf verschiedene Zeitintervalle. Für Forschungszwecke werden **höher aufgelöste Rohdaten** benötigt.

| Aggregationsintervall | Anzahl Kategorien | Kritikalität für Forschung |
|-----------------------|-------------------|----------------------------|
| 60 Minuten            | 2                 | 🔴 Hoch                    |
| 30 Minuten            | ~15               | 🟡 Mittel                  |
| 1 Minute              | 1                 | 🟢 Akzeptabel              |
| 71-73 Stunden         | 2                 | 🔴 Hoch                    |
| Exakte Zeitstempel    | ~3                | ✅ Optimal                 |

---

## Detaillierte Auflistung nach Kategorie

### 🔴 Kritisch: 60-Minuten-Aggregation

Diese Daten werden auf Stundenintervalle aggregiert (`:50`-Zeitstempel). Der **erste Wert** des Intervalls wird verwendet.

| Kategorie | Beispielparameter | Aggregation |
|-----------|-------------------|-------------|
| **Online erfasste Vitaldaten** | HF, ARTm, ARTs, ARTd, SpO2, ZVDm, AF, FAP | 60 min, Erster |
| **Manuell erfasste Vitaldaten** | HZV, Temperatur, BP, Herzfrequenz | 60 min, Erster |

**Problem:** Echtzeit-Monitordaten (HF, Blutdruck, SpO2) werden eigentlich sekündlich erfasst, aber nur stündlich exportiert.

**Anfrage an PDMS-Admin:**  
→ Export mit 1-Minuten- oder 5-Minuten-Intervall möglich?  
→ Alternativ: Rohdaten-Export ohne Aggregation?

---

### 🟡 Moderat: 30-Minuten-Aggregation

Diese Daten werden auf 30-Minuten-Intervalle aggregiert.

| Kategorie | Beispielparameter | Aggregation |
|-----------|-------------------|-------------|
| **Manuell erfasste Respiratorwerte** | FiO2 | 30 min, Erster |
| **Labor: Blutgase arteriell** | pO2, pCO2, pH, Laktat, BE | 30 min, Erster |
| **Labor: Blutgase venös** | pO2, pCO2, pH, Laktat | 30 min, Erster |
| **Labor: Blutgase gv** | Chlorid | 30 min, Erster |
| **Labor: Blutgase kapillär** | pH, pO2, pCO2 | 30 min, Erster |
| **Labor: Blutgase unspez.** | Div. BGA-Werte | 30 min, Erster |
| **Labor: Blutbild** | Hb, Hkt, Leukozyten, Thrombozyten | 30 min, Erster |
| **Labor: Differentialblutbild** | Neutrophile, Lymphozyten, etc. | 30 min, Erster |
| **Labor: Retikulozyten** | Retikulozyten | 30 min, Erster |
| **Labor: Blutgruppe** | AB0, Rhesus | 30 min, Erster |
| **Labor: Gerinnung** | INR, PTT, Fibrinogen | 30 min, Erster |
| **Labor: TEG** | TEG-Parameter | 30 min, Erster |
| **Labor: TAT** | Thrombozytenaggregation | 30 min, Erster |
| **Labor: Enzyme** | CK, CK-MB, Troponin, GOT, GPT | 30 min, Erster |
| **Labor: Retention** | Kreatinin, Harnstoff | 30 min, Erster |
| **Labor: Proteine** | Albumin, CRP | 30 min, Erster |
| **Labor: Elektrolyte** | Na, K, Ca, Mg | 30 min, Erster |

**Hinweis:** Für Laborwerte ist 30-Minuten-Aggregation meist akzeptabel, da Laborabnahmen seltener erfolgen. Problem entsteht nur bei mehreren Abnahmen innerhalb von 30 Minuten.

---

### 🟢 Akzeptabel: 1-Minuten-Aggregation

| Kategorie | Beispielparameter | Aggregation |
|-----------|-------------------|-------------|
| **Online erfasste Respiratorwerte** | FiO2, Tidalvolumen, PEEP, Compliance, Atemfrequenz, Modus | 1 min, Erster |

**Hinweis:** Diese Auflösung ist für die meisten Forschungszwecke ausreichend.

---

### 🔴 Kritisch: Mehrtages-Aggregation (Bilanz)

Diese Daten werden über **ca. 3 Tage (71-73 Stunden)** summiert.

| Kategorie | Inhalt | Aggregation |
|-----------|--------|-------------|
| **Bilanz: Flüssigkeitsbilanz** | Einfuhr/Ausfuhr pro Quelle (Infusion, DK, Drainage, etc.) | 71-73 h Summe |
| **Bilanz: Kolloidbilanz** | Blutersatz, Nährwerte, Elektrolyte | 71-73 h Summe |

**Problem:** Keine tagesscharfe oder stündliche Bilanzierung möglich!

**Anfrage an PDMS-Admin:**  
→ 24-Stunden-Bilanzintervall möglich?  
→ Oder stundenweise Ein-/Ausfuhr-Daten exportieren?

---

### ✅ Optimal: Exakte Zeitstempel (keine Aggregation)

Diese Daten werden mit dem Original-Zeitstempel exportiert.

| Kategorie | Inhalt |
|-----------|--------|
| **Medikamentengaben** | Start/Stopp/Rate für Perfusoren, Bolusgaben, Infusionen |
| **ALLE Patientendaten** | Geräte (ECMO, Impella), Zugänge, Wunden, Pflegedoku, Scores |
| **Beatmung** | Aktivitäten (Intubation, Extubation) |

**Hinweis:** Diese Struktur ist für Forschung gut geeignet.

---

## Bekannte Datenredundanz: HZV-Dopplung

Das HZV (Herzzeitvolumen) der Impella erscheint **doppelt** im Export:

1. **"Impella A. axilliaris rechts"** → Exakter Dokumentationszeitpunkt (z.B. 14:59)
2. **"Manuell erfasste Vitaldaten"** → Auf Stunde aggregiert (z.B. 14:50)

**Ursache:** Das PDMS mappt den Impella-HZV-Wert automatisch in die Vitaldaten-Tabelle.

**Anfrage an PDMS-Admin:**  
→ Ist dieses Mapping konfigurierbar?  
→ Kann das Auto-Mapping deaktiviert werden, sodass HZV nur unter Impella erscheint?

---

## Empfehlungen für PDMS-Konfiguration

### Priorität 1: Vitaldaten höher auflösen
- **Aktuell:** 60-Minuten-Intervall
- **Wunsch:** 1-5 Minuten oder Echtzeit-Export
- **Betroffene Parameter:** HF, Blutdruck (ART, FAP), SpO2, AF, ZVD

### Priorität 2: Bilanzierung tagessscharf
- **Aktuell:** ~3-Tage-Summen
- **Wunsch:** 24-Stunden-Intervalle oder stündliche Einzelwerte

### Priorität 3: HZV-Redundanz vermeiden
- **Aktuell:** Doppelt in Vitaldaten + Impella
- **Wunsch:** Nur in Impella-Dokumentation (mit exaktem Zeitstempel)

---

## Technischer Hintergrund

**Exportformat:** CSV mit Semikolon-Delimiter  
**Aggregationsmethode:** "Erster" (erster Wert im Intervall wird übernommen)  
**Intervall-Startzeit:** Minute :50 (konfigurierbar?)

---

*Dokument erstellt für Gespräch mit PDMS-Administration*
