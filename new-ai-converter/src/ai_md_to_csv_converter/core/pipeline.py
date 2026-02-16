"""Main pipeline orchestrator for MD to CSV conversion."""
import asyncio
import time
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

from ..core.config import Config
from ..core.exceptions import ConversionError, VerificationError
from ..models.results import ConversionResult, PipelineResult, PipelineContext
from ..providers.factory import ProviderFactory
from ..preprocessors.factory import PreprocessorFactory
from ..postprocessors.factory import PostprocessorFactory
from ..utils.logger import get_logger
from ..utils.retry import RetryHandler


class FixError(Exception):
    """Exception raised when fixing fails."""
    pass


class Pipeline:
    """Main pipeline orchestrator for MD to CSV conversion.

    Stages:
    1. Preprocessing - MD format fixing
    2. Conversion - AI-based conversion
    3. Postprocessing - CSV cleanup
    4. Verification - JS-based validation
    """

    def __init__(self, config: Config):
        """Initialize the pipeline.

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = get_logger(__name__)

        # Initialize provider
        provider_name = config.pipeline.provider.active
        provider_config = {
            "name": provider_name,
            **config.pipeline.provider.settings.get(provider_name, {})
        }
        self.provider = ProviderFactory.create(provider_name, provider_config)

        # Initialize preprocessors
        self.preprocessors = PreprocessorFactory.create_pipeline(
            config.pipeline.preprocess
        )

        # Initialize postprocessors
        self.postprocessors = PostprocessorFactory.create_pipeline(
            config.pipeline.postprocess
        )

        # Initialize retry handler
        self.retry_handler = RetryHandler({
            "max_retries": config.retry.max_retries,
            "base_delay": config.retry.base_delay,
            "exponential_backoff": config.retry.exponential_backoff,
            "jitter": config.retry.jitter,
            "jitter_range": config.retry.jitter_range,
        })

        # Import validator lazily (only when verification is enabled)
        self._validator = None

    async def process_file(
        self,
        input_file: Path,
        output_file: Path
    ) -> ConversionResult:
        """Process a single MD file to CSV.

        Args:
            input_file: Path to input MD file
            output_file: Path to output CSV file

        Returns:
            ConversionResult with status and metadata
        """
        start_time = time.time()
        context = PipelineContext(
            config=self.config,
            input_file=input_file,
            output_file=output_file,
            source_md_file=input_file,  # Store for fixing context
        )

        self.logger.info(f"Processing: {input_file.name}")

        try:
            # Stage 1: Read input MD
            context.original_content = await self._read_input(input_file)
            context.preprocessed_content = context.original_content

            # Stage 2: Preprocess MD (using existing preprocessors)
            if self.preprocessors:
                self.logger.debug(f"Running {len(self.preprocessors)} preprocessors")
                for preprocessor in self.preprocessors:
                    context.preprocessed_content = await preprocessor.process(
                        context.preprocessed_content,
                        context
                    )

            # Stage 3: Parse MD to CSV (using parse_md_questions.py)
            self.logger.debug("Converting MD to CSV using parse_md_questions")
            from ..preprocessors.parse_md_questions import parse_md_to_csv
            context.csv_output = parse_md_to_csv(context.preprocessed_content)

            # Stage 4: Postprocess CSV
            if self.postprocessors:
                self.logger.debug(f"Running {len(self.postprocessors)} postprocessors")
                for postprocessor in self.postprocessors:
                    context.csv_output = await postprocessor.process(
                        context.csv_output,
                        context
                    )

            # Stage 5: Write output CSV
            await self._write_output(output_file, context.csv_output)

            # Stage 6: Verify (if enabled)
            if self.config.pipeline.verification.enabled:
                context.verification_result = await self._verify(
                    output_file,
                    context
                )

                # Stage 7: Auto-fix if enabled and verification failed
                if (context.verification_result and
                    not context.verification_result.get("passed", True) and
                    self.config.pipeline.fixing.enabled and
                    self.config.pipeline.fixing.auto_fix_on_failure):

                    self.logger.info(f"Attempting AI fix for {input_file.name}")
                    try:
                        fixed_csv = await self._fix_csv(
                            context.original_content,  # Original MD for context
                            context.csv_output,        # CSV with errors
                            context.verification_result,
                            context
                        )

                        # Save fixed CSV to separate file
                        fixed_file = output_file.parent / f"{output_file.stem}_fixed{output_file.suffix}"
                        await self._write_output(fixed_file, fixed_csv)
                        context.fixed_output_file = fixed_file

                        # Verify the fixed version
                        fixed_verification = await self._verify(fixed_file, context)
                        context.verification_result = fixed_verification

                        self.logger.info(f"Fixed CSV saved to {fixed_file.name}")

                        # Update csv_output to fixed version for counting
                        context.csv_output = fixed_csv

                    except FixError as e:
                        if self.config.pipeline.fixing.fail_on_unfixable:
                            raise
                        self.logger.warning(f"AI fix failed: {e}")
                        # Continue with original failed result

            # Calculate duration
            duration = time.time() - start_time

            # Count questions
            question_count = context.csv_output.count("\nobjective,")

            self.logger.info(
                f"Success: {input_file.name} → {output_file.name} "
                f"({question_count} questions, {duration:.1f}s)"
            )

            return ConversionResult(
                success=True,
                input_file=input_file,
                output_file=output_file,
                question_count=question_count,
                verification_result=context.verification_result,
                metadata=context.metadata,
                duration_seconds=duration,
                source_md_file=context.source_md_file,
                fixed_output_file=context.fixed_output_file,
            )

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Failed: {input_file.name}: {e}")

            return ConversionResult(
                success=False,
                input_file=input_file,
                output_file=output_file,
                error=str(e),
                duration_seconds=duration,
            )

    async def process_batch(
        self,
        files: List[Tuple[Path, Path]]
    ) -> PipelineResult:
        """Process a batch of files.

        Args:
            files: List of (input_file, output_file) tuples

        Returns:
            PipelineResult with batch summary
        """
        start_time = time.time()
        self.logger.info(f"Processing batch of {len(files)} files")

        results = []
        successful = 0
        failed = 0

        # Process files (with parallelism if configured)
        parallel_workers = self.config.io.parallel_workers

        if parallel_workers > 1:
            # Process in parallel
            tasks = [
                self.process_file(input_file, output_file)
                for input_file, output_file in files
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Process sequentially
            results = []
            for input_file, output_file in files:
                result = await self.process_file(input_file, output_file)
                results.append(result)

        # Count successes and failures
        for result in results:
            if isinstance(result, Exception):
                failed += 1
            elif result.success:
                successful += 1
            else:
                failed += 1

        duration = time.time() - start_time

        self.logger.info(
            f"Batch complete: {successful} successful, {failed} failed "
            f"({duration:.1f}s)"
        )

        return PipelineResult(
            total_files=len(files),
            successful=successful,
            failed=failed,
            results=[r for r in results if not isinstance(r, Exception)],
            duration_seconds=duration,
        )

    async def _read_input(self, input_file: Path) -> str:
        """Read input MD file.

        Args:
            input_file: Path to input file

        Returns:
            File contents as string
        """
        # Use aiofiles for async reading
        import aiofiles
        async with aiofiles.open(input_file, 'r', encoding='utf-8') as f:
            return await f.read()

    async def _write_output(self, output_file: Path, content: str) -> None:
        """Write output CSV file.

        Args:
            output_file: Path to output file
            content: CSV content to write
        """
        # Create output directory if needed
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Use aiofiles for async writing
        import aiofiles
        async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
            await f.write(content)

    async def _build_prompts(self, md_content: str) -> Tuple[str, str]:
        """Build system and user prompts.

        Args:
            md_content: Preprocessed markdown content

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        # Load system prompt from template
        template_dir = Path(__file__).parent.parent.parent / "templates" / "prompts"
        system_prompt_file = template_dir / "system_prompt.txt"
        conversion_prompt_file = template_dir / "conversion_prompt.txt"

        if not system_prompt_file.exists():
            raise ConversionError(f"System prompt template not found: {system_prompt_file}")
        if not conversion_prompt_file.exists():
            raise ConversionError(f"Conversion prompt template not found: {conversion_prompt_file}")

        # Read templates
        import aiofiles
        async with aiofiles.open(system_prompt_file, 'r', encoding='utf-8') as f:
            system_prompt = await f.read()

        async with aiofiles.open(conversion_prompt_file, 'r', encoding='utf-8') as f:
            conversion_prompt = await f.read()

        # Fill in user prompt with MD content
        user_prompt = conversion_prompt.replace("{md_content}", md_content)

        return system_prompt, user_prompt

    async def _verify(
        self,
        csv_file: Path,
        context: PipelineContext
    ) -> Optional[Dict[str, Any]]:
        """Verify CSV output using js-verify.

        Args:
            csv_file: Path to CSV file to verify
            context: Pipeline context

        Returns:
            Verification result dict, or None if verification failed
        """
        # Lazy import of validator
        if self._validator is None:
            from ..validators.js_verify_wrapper import JsVerifyWrapper
            self._validator = JsVerifyWrapper(self.config)

        try:
            result = await self._validator.verify(csv_file, context)
            return result
        except VerificationError as e:
            if self.config.pipeline.verification.continue_on_error:
                self.logger.warning(f"Verification failed (continuing): {e}")
                return {"error": str(e)}
            raise

    async def _fix_csv(
        self,
        md_content: str,
        csv_content: str,
        error_report: Dict[str, Any],
        context: PipelineContext
    ) -> str:
        """Fix CSV errors using AI.

        Args:
            md_content: Original MD content
            csv_content: Generated CSV with errors
            error_report: Verification error report
            context: Pipeline context

        Returns:
            Fixed CSV content

        Raises:
            FixError: If fixing fails
        """
        from ..fixers.factory import FixerFactory

        fixer_config = {
            "name": "ai_csv_fixer",
            "enabled": True,
            "provider": context.config.pipeline.fixing.provider,
            "options": {
                "single_attempt": context.config.pipeline.fixing.max_attempts == 1,
                "validate_output": context.config.pipeline.fixing.validate_after_fix,
            }
        }

        try:
            fixer = FixerFactory.create(fixer_config)
            return await fixer.fix(md_content, csv_content, error_report, context)
        except Exception as e:
            raise FixError(f"AI-based CSV fixing failed: {e}") from e
