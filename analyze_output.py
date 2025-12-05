import pandas as pd
import sys

def analyze():
    try:
        df = pd.read_csv('output.csv', sep=';')
        print("--- Source Types ---")
        print(df['source_type'].value_counts())
        print("\n--- Categories per Source Type ---")
        print(df.groupby('source_type')['category'].nunique())
        
        print("\n--- Null Values ---")
        print(df.isnull().sum())
        
        print("\n--- Sample of 'Arzt Verlauf' ---")
        verlauf = df[df['source_type'] == 'Arzt Verlauf']
        if not verlauf.empty:
            print(verlauf[['timestamp', 'value']].head())
            print(f"Average length of 'Arzt Verlauf' value: {verlauf['value'].astype(str).str.len().mean()}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze()
