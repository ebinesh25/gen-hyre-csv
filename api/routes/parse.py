import asyncio
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from doc2md import convert_docx_to_md

# Import parser functions from the project root
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from parse_md_questions import parse_questions_from_file, write_to_csv

router = APIRouter()

TEMP_DIR = Path(__file__).parent.parent.parent / "temp"
TEMP_DIR.mkdir(exist_ok=True)


@router.post("/parse-doc")
async def parse_doc(file: UploadFile = File(...)):
    """
    Parse a DOCX file containing questions and return a CSV file.

    Accepts a DOCX file upload, converts it to markdown, parses questions,
    and returns a CSV file with the parsed questions.
    """
    # Validate file type
    if not file.filename or not file.filename.endswith(('.docx', '.DOCX')):
        raise HTTPException(status_code=400, detail="Only DOCX files are supported")

    # Create temp directory for this request
    request_id = id(file)
    request_temp_dir = TEMP_DIR / f"request_{request_id}"
    request_temp_dir.mkdir(exist_ok=True)

    try:
        # Save uploaded DOCX
        docx_path = request_temp_dir / file.filename
        with open(docx_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Convert DOCX to markdown (run in thread to avoid Playwright sync/async conflict)
        md_output_dir = request_temp_dir / "md"
        md_files = await asyncio.to_thread(convert_docx_to_md, str(docx_path), str(md_output_dir))

        if not md_files:
            raise HTTPException(status_code=400, detail="No markdown files generated from DOCX")

        # Parse all questions from markdown files
        all_questions = []
        for md_file in md_files:
            questions = parse_questions_from_file(md_file)
            all_questions.extend(questions)

        if not all_questions:
            raise HTTPException(status_code=400, detail="No questions found in document")

        # Write to CSV
        csv_path = request_temp_dir / "output.csv"
        write_to_csv(all_questions, csv_path)

        # Return CSV file
        return FileResponse(
            path=csv_path,
            filename=f"{Path(file.filename).stem}_questions.csv",
            media_type="text/csv"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
