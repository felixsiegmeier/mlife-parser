import argparse
import os
import sys
from mlife_core.services.pipeline import run_parsing_pipeline

def main():
    parser = argparse.ArgumentParser(description="Parse mLife CSV data into a consolidated format.")
    parser.add_argument("input_file", nargs="?", default="data/gesamte_akte2.csv", help="Path to the input CSV file.")
    parser.add_argument("--output", "-o", default="output.csv", help="Path to the output CSV file.")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found.")
        sys.exit(1)
        
    print(f"Processing {args.input_file}...")
    
    try:
        df = run_parsing_pipeline(args.input_file)
        
        if df.empty:
            print("No data parsed.")
            return

        print(f"Saving to {args.output}...")
        df.to_csv(args.output, index=False, sep=';')
        print("Done.")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
