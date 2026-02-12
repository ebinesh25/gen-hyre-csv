"""JS-Verify wrapper - integrates with the existing js-verify script."""
import asyncio
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

from .base import BaseValidator
from ..core.config import Config
from ..core.exceptions import VerificationError
from ..utils.logger import get_logger


class JsVerifyWrapper(BaseValidator):
    """Wrapper for the js-verify CSV validation script.

    Integrates with ../js-verify/verfifyCSV.js to validate generated CSV files.
    """

    def __init__(self, config: Config):
        """Initialize JS verify wrapper.

        Args:
            config: Configuration object
        """
        super().__init__(config.pipeline.verification)
        self.logger = get_logger(__name__)

        # Get paths from config
        self.js_verify_path = config.pipeline.verification.js_verify_path
        self.verify_report_path = Path("js-verify/verification-report.json")
        self.csv_output_dir = Path("csv-ai")

    async def verify(self, csv_file: Path, context) -> Optional[Dict[str, Any]]:
        """Verify CSV file using js-verify.

        Args:
            csv_file: Path to CSV file to verify
            context: Pipeline context

        Returns:
            Verification result dict with keys:
                - passed: True if verification passed
                - errors: List of errors found
                - warnings: List of warnings
                - report_path: Path to verification report

        Raises:
            VerificationError: If verification fails critically
        """
        try:
            self.logger.debug(f"Verifying {csv_file.name} with js-verify")

            # Step 1: Copy CSV to csv-ai directory (where js-verify expects it)
            await self._copy_to_csv_dir(csv_file)

            # Step 2: Run js-verify
            await self._run_verify_script()

            # Step 3: Parse verification report
            result = await self._parse_verification_report(csv_file)

            return result

        except VerificationError:
            raise
        except Exception as e:
            raise VerificationError(f"js-verify failed: {e}") from e

    async def _copy_to_csv_dir(self, csv_file: Path) -> None:
        """Copy CSV file to csv-ai directory.

        Args:
            csv_file: Source CSV file
        """
        # Create csv-ai directory if it doesn't exist
        self.csv_output_dir.mkdir(parents=True, exist_ok=True)

        # Destination path
        dest_path = self.csv_output_dir / csv_file.name

        # Copy file (use async I/O)
        import aiofiles
        import shutil

        # Use sync copy for simplicity (file is typically small)
        shutil.copy(csv_file, dest_path)

        self.logger.debug(f"Copied {csv_file.name} to {dest_path}")

    async def _run_verify_script(self) -> None:
        """Run the js-verify script using bun.

        Raises:
            VerificationError: If script execution fails
        """
        cmd = ["bun", "run", self.js_verify_path]

        self.logger.debug(f"Running: {' '.join(cmd)}")

        try:
            # Run subprocess (with asyncio for non-blocking)
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path.cwd().parent.parent  # Run from parent directory
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                # Check if it's a validation error (expected) or execution error (unexpected)
                if "Error: Cannot find module" in error_msg or "bun: command not found" in error_msg:
                    raise VerificationError(f"js-verify execution error: {error_msg}")

                # Validation errors are OK - we parse the report for details
                self.logger.debug(f"js-verify completed with validation errors")

            else:
                self.logger.debug("js-verify completed successfully")

        except FileNotFoundError:
            raise VerificationError(
                "bun command not found. Install bun from https://bun.sh"
            )
        except Exception as e:
            if isinstance(e, VerificationError):
                raise
            raise VerificationError(f"Failed to run js-verify: {e}") from e

    async def _parse_verification_report(self, csv_file: Path) -> Dict[str, Any]:
        """Parse the verification-report.json file.

        Args:
            csv_file: Original CSV file path

        Returns:
            Verification result dict
        """
        # Check from parent directory (where js-verify is located)
        report_path = Path.cwd().parent.parent / self.verify_report_path

        if not report_path.exists():
            raise VerificationError(
                f"Verification report not found: {report_path}"
            )

        try:
            # Read report
            import aiofiles
            async with aiofiles.open(report_path, 'r', encoding='utf-8') as f:
                report_content = await f.read()

            report = json.loads(report_content)

            # Find results for our specific file
            file_results = self._extract_file_results(report, csv_file.name)

            return {
                "passed": file_results.get("status") != "failed",
                "status": file_results.get("status", "unknown"),
                "errors": file_results.get("errors", []),
                "warnings": file_results.get("warnings", []),
                "total_questions": file_results.get("totalQuestions", 0),
                "verified_questions": file_results.get("verifiedQuestions", 0),
                "report_path": str(report_path),
            }

        except json.JSONDecodeError as e:
            raise VerificationError(f"Failed to parse verification report: {e}") from e
        except Exception as e:
            raise VerificationError(f"Failed to read verification report: {e}") from e

    def _extract_file_results(self, report: dict, filename: str) -> dict:
        """Extract results for a specific file from the report.

        Args:
            report: Full verification report
            filename: Name of the CSV file

        Returns:
            Results for the specific file
        """
        # The report structure varies - handle different formats
        if "files" in report:
            for file_result in report["files"]:
                if filename in file_result.get("file", ""):
                    return file_result

        # If no specific file results, return summary
        return {
            "status": report.get("status", "unknown"),
            "errors": report.get("errors", []),
            "warnings": report.get("warnings", []),
            "totalQuestions": report.get("totalQuestions", 0),
            "verifiedQuestions": report.get("verifiedQuestions", 0),
        }
