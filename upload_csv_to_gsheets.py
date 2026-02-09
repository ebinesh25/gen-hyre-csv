import gspread
import pandas as pd
import os
from pathlib import Path

# --- UPDATE THIS PATH to your new Service Account JSON file ---
CREDENTIALS_PATH = '/home/positron/.config/downloadDocs/guvi-account-service-key.json'

# Path to your CSV files
CSV_FOLDER_PATH = './csv-new'  # Assuming CSVs are in the same folder, or change this

def main():
    try:
        # 1. Authenticate using the new Service Account file
        # Make sure you have enabled Google Sheets API & Drive API in Cloud Console
        gc = gspread.service_account(filename=CREDENTIALS_PATH)
        
        # 2. Get list of CSV files
        # Using Pathlib for better path handling
        csv_files = list(Path(CSV_FOLDER_PATH).glob('*.csv'))
        
        if not csv_files:
            print("No CSV files found in:", CSV_FOLDER_PATH)
            return

        print(f"Found {len(csv_files)} CSV files. Starting upload...")

        for file_path in csv_files:
            try:
                # Read CSV
                df = pd.read_csv(file_path)
                
                # Clean up filename for the Sheet title (remove extension)
                sheet_title = file_path.stem
                
                # 3. Create the Spreadsheet
                sh = gc.create(sheet_title)
                
                # 4. Upload data
                # We access the first worksheet (default)
                worksheet = sh.sheet1
                
                # Convert DataFrame to list of lists for upload
                # Reset index=False prevents pandas from adding the index numbers as a column
                data_to_upload = [df.columns.values.tolist()] + df.values.tolist()
                worksheet.update(data_to_upload)
                
                # 5. Get the URL
                sheet_url = sh.url
                print(f"✅ Success: '{file_path.name}' -> '{sheet_title}'")
                print(f"   URL: {sheet_url}\n")

            except Exception as e:
                print(f"❌ Failed to upload {file_path.name}: {e}")

    except FileNotFoundError:
        print(f"Error: The credentials file was not found at {CREDENTIALS_PATH}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    main()