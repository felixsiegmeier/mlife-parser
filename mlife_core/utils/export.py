import pandas as pd

STANDARD_CATEGORIES = {
    "Vitaldaten": ["Vitals", "Vitalparameter (manuell)"],
    "Respiratordaten": ["Respiratory", "Beatmungsprotokoll manuell"],
    "Labor": ["Lab"],
    "Medikamentengaben": ["Medication"],
    "Bilanz": ["FluidBalance"]
}

def save_dataframe(df: pd.DataFrame, path: str) -> int:
    """
    Saves a DataFrame to CSV or Excel based on file extension.
    Removes empty columns before saving.
    Returns the number of rows saved.
    """
    # Leere Spalten entfernen (wo alle Werte NaN/None sind)
    df_clean = df.dropna(axis=1, how='all')
    
    if path.endswith(".xlsx"):
        df_clean.to_excel(path, index=False)
    else:
        df_clean.to_csv(path, index=False, sep=";")
    return len(df_clean)

def get_subset_df(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """
    Filters the main DataFrame based on a predefined key (e.g., 'vitals', 'lab').
    """
    if df is None: return pd.DataFrame()
    
    if key == "vitals":
        return df[df['source_type'] == 'Vitals']
    elif key == "lab":
        return df[df['source_type'] == 'Lab']
    elif key == "respiratory":
        return df[df['source_type'] == 'Respiratory']
    elif key == "medication":
        return df[df['source_type'] == 'Medication']
    elif key == "impella":
        term = "Impella"
        mask = (df['source_type'].astype(str).str.contains(term, case=False)) | \
               (df['category'].astype(str).str.contains(term, case=False)) | \
               (df['parameter'].astype(str).str.contains(term, case=False))
        return df[mask]
    elif key == "crrt":
        term = "Hämofilter|CRRT"
        mask = (df['source_type'].astype(str).str.contains(term, case=False, regex=True)) | \
               (df['category'].astype(str).str.contains(term, case=False, regex=True)) | \
               (df['parameter'].astype(str).str.contains(term, case=False, regex=True))
        return df[mask]
    elif key == "ecmo":
        term = "ECMO"
        mask = (df['source_type'].astype(str).str.contains(term, case=False)) | \
               (df['category'].astype(str).str.contains(term, case=False)) | \
               (df['parameter'].astype(str).str.contains(term, case=False))
        return df[mask]
    elif key == "nirs":
        term = "NIRS"
        mask = (df['source_type'].astype(str).str.contains(term, case=False)) | \
               (df['category'].astype(str).str.contains(term, case=False)) | \
               (df['parameter'].astype(str).str.contains(term, case=False))
        return df[mask]
    elif key == "doctor_notes":
        term = "Arzt Verlauf"
        mask = df['source_type'].astype(str).str.contains(term, case=False)
        return df[mask]
    
    return pd.DataFrame()
