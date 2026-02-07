#!/usr/bin/env python3
"""
Script to upload DOCX files to the parsing API and save the CSV output.
"""

import argparse
import sys
from pathlib import Path

import requests


def parse_single_file(docx_path: str, output_dir: str = "./csv", api_url: str = "http://localhost:8000/api/parse-doc"):
    """
    Upload a single DOCX file to the API and save the CSV response.

    Args:
        docx_path: Path to the DOCX file to upload
        output_dir: Directory to save the output CSV file
        api_url: URL of the parse-doc API endpoint

    Returns:
        Path to the saved CSV file, or None if failed
    """
    docx_file = Path(docx_path)

    # Validate input file
    if not docx_file.exists():
        print(f"Error: File not found: {docx_path}")
        return None

    if not docx_file.suffix.lower() in ('.docx',):
        print(f"Error: Not a DOCX file: {docx_path}")
        return None

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Prepare output filename
    output_csv = output_path / f"{docx_file.stem}_questions.csv"

    # Upload file to API
    print(f"Uploading {docx_file.name} to {api_url}...")

    try:
        with open(docx_file, 'rb') as f:
            files = {'file': (docx_file.name, f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            response = requests.post(api_url, files=files, timeout=300)

        if response.status_code == 200:
            # Save CSV response
            output_csv.write_bytes(response.content)
            print(f"Success! CSV saved to: {output_csv}")
            return output_csv
        else:
            print(f"Error: API returned status {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to API at {api_url}")
        print("Make sure the FastAPI server is running (e.g., 'uvicorn api.main:app --reload')")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Upload DOCX files to the parsing API and save CSV output"
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="DOCX file(s) to process (can be multiple files or a directory)"
    )
    parser.add_argument(
        "-o", "--output",
        default="./csv",
        help="Output directory for CSV files (default: ./csv)"
    )
    parser.add_argument(
        "-u", "--url",
        default="http://localhost:8000/api/parse-doc",
        help="API endpoint URL (default: http://localhost:8000/api/parse-doc)"
    )

    args = parser.parse_args()

    # Process each input file
    results = []
    for file_path in args.files:
        path = Path(file_path)

        if path.is_dir():
            # Process all DOCX files in directory
            docx_files = list(path.glob("*.docx")) + list(path.glob("*.DOCX"))
            if not docx_files:
                print(f"No DOCX files found in directory: {file_path}")
                continue
            for docx_file in docx_files:
                result = parse_single_file(str(docx_file), args.output, args.url)
                results.append(result)
        else:
            # Process single file
            result = parse_single_file(file_path, args.output, args.url)
            results.append(result)

    # Summary
    successful = sum(1 for r in results if r is not None)
    print(f"\nDone! Processed {successful}/{len(results)} files successfully.")

    return 0 if successful == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
