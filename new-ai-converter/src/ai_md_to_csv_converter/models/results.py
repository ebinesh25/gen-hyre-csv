"""Result dataclasses for pipeline operations."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..core.config import Config


@dataclass
class ConversionResult:
    """Result of converting a single file.

    Attributes:
        success: Whether conversion was successful
        input_file: Path to input MD file
        output_file: Path to output CSV file
        question_count: Number of questions in the output
        verification_result: Optional verification result from js-verify
        metadata: Additional metadata from the pipeline
        error: Optional error message if conversion failed
        duration_seconds: Time taken for conversion
        timestamp: When the conversion occurred
        source_md_file: Optional path to original MD file (for fixing context)
        fixed_output_file: Optional path to fixed CSV file (if fixing was attempted)
    """
    success: bool
    input_file: Path
    output_file: Path
    question_count: int = 0
    verification_result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_seconds: float = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source_md_file: Optional[Path] = None
    fixed_output_file: Optional[Path] = None


@dataclass
class PipelineResult:
    """Result of processing a batch of files.

    Attributes:
        total_files: Total number of files processed
        successful: Number of successful conversions
        failed: Number of failed conversions
        results: List of individual file results
        duration_seconds: Total time for the batch
        timestamp: When the batch was processed
    """
    total_files: int
    successful: int
    failed: int
    results: List[ConversionResult] = field(default_factory=list)
    duration_seconds: float = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_report(self) -> Dict[str, Any]:
        """Convert to report format (JSON serializable).

        Returns:
            Dictionary representation of the result
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "summary": {
                "total": self.total_files,
                "successful": self.successful,
                "failed": self.failed,
                "duration_seconds": self.duration_seconds,
            },
            "files": [
                {
                    "input": str(r.input_file),
                    "output": str(r.output_file),
                    "success": r.success,
                    "question_count": r.question_count,
                    "verified": r.verification_result is not None,
                    "error": r.error,
                }
                for r in self.results
            ]
        }


@dataclass
class PipelineContext:
    """Context object passed through pipeline stages.

    Attributes:
        config: The configuration object
        input_file: Path to input file
        output_file: Path to output file
        metadata: Additional metadata collected during processing
        original_content: Original MD content
        preprocessed_content: Content after preprocessing
        csv_output: Final CSV output
        verification_result: Optional verification result
        source_md_file: Optional path to original MD file (for fixing context)
        fixed_output_file: Optional path to fixed CSV file
    """
    config: Config
    input_file: Path
    output_file: Path
    metadata: Dict[str, Any] = field(default_factory=dict)
    original_content: str = ""
    preprocessed_content: str = ""
    csv_output: str = ""
    verification_result: Optional[Dict[str, Any]] = None
    source_md_file: Optional[Path] = None
    fixed_output_file: Optional[Path] = None


@dataclass
class FixResult:
    """Result of fixing a CSV file.

    Attributes:
        success: Whether fixing was successful
        input_csv: Path to original CSV file
        output_csv: Path to fixed CSV file
        errors_before: Number of errors before fixing
        errors_after: Number of errors after fixing
        fixed_rows: Number of rows that were fixed
        duration_seconds: Time taken for fixing
        timestamp: When the fix occurred
    """
    success: bool
    input_csv: Path
    output_csv: Path
    errors_before: int = 0
    errors_after: int = 0
    fixed_rows: int = 0
    duration_seconds: float = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
