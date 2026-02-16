"""CLI entry point for the AI MD to CSV converter."""
import asyncio
import sys
from pathlib import Path
from typing import Optional

import click

from .core.config import ConfigLoader
from .core.pipeline import Pipeline
from .utils.logger import setup_logging, get_logger


@click.group()
@click.option(
    '--config', '-c',
    type=click.Path(exists=True, path_type=Path),
    help='Path to custom configuration file'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
@click.pass_context
def cli(ctx, config: Optional[Path], verbose: bool):
    """AI-powered Markdown to CSV converter.

    Convert question files from Markdown format to CSV format with
    built-in verification and preprocessing.
    """
    # Load configuration
    config_loader = ConfigLoader(config)
    ctx.obj = {'config_loader': config_loader, 'verbose': verbose}

    # Setup logging
    try:
        cfg = config_loader.load()
        setup_logging(
            level="DEBUG" if verbose else cfg.logging.level,
            format_type=cfg.logging.format,
            console_output=cfg.logging.console_output,
            file_output=cfg.logging.file_output,
            log_dir=cfg.logging.log_dir,
        )
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('input', type=click.Path(exists=True, path_type=Path), required=False)
@click.option(
    '--output', '-o',
    type=click.Path(path_type=Path),
    help='Output file or directory'
)
@click.option(
    '--provider', '-p',
    type=click.Choice(['groq', 'claude_cli', 'openai'], case_sensitive=False),
    help='AI provider to use'
)
@click.option(
    '--no-verify',
    is_flag=True,
    help='Skip verification step'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Show what would be done without actually converting'
)
@click.pass_context
def convert(ctx, input: Optional[Path], output: Optional[Path],
            provider: Optional[str], no_verify: bool, dry_run: bool):
    """Convert markdown file(s) to CSV.

    If INPUT is a directory, all .md files will be converted.
    If INPUT is a single file, only that file will be converted.
    """
    config_loader = ctx.obj['config_loader']
    verbose = ctx.obj['verbose']

    try:
        # Load configuration
        config = config_loader.load()

        # Override provider if specified
        if provider:
            config.pipeline.provider.active = provider

        # Override verification setting
        if no_verify:
            config.pipeline.verification.enabled = False

        # Initialize pipeline
        pipeline = Pipeline(config)
        logger = get_logger(__name__)

        # Determine input/output files
        if input is None:
            # Use default input directory from config
            input = config.io.input_dir

        if input.is_file():
            # Single file
            if output is None:
                output = config.io.output_dir / config.io.csv_subdir / f"{input.stem}.csv"
            elif output.is_dir():
                output = output / f"{input.stem}.csv"

            files = [(input, output)]
            logger.info(f"Converting single file: {input.name}")

        elif input.is_dir():
            # Directory of files
            md_files = list(input.glob("*.md"))
            if not md_files:
                click.echo(f"No .md files found in {input}")
                sys.exit(1)

            # Determine output directory
            if output is None:
                output_dir = config.io.output_dir / config.io.csv_subdir
            elif output.is_file():
                click.echo("OUTPUT must be a directory when INPUT is a directory")
                sys.exit(1)
            else:
                output_dir = output

            # Create file pairs
            files = [
                (md_file, output_dir / f"{md_file.stem}.csv")
                for md_file in md_files
            ]
            logger.info(f"Converting {len(files)} files from {input.name}")

        else:
            click.echo(f"INPUT must be a file or directory: {input}")
            sys.exit(1)

        # Dry run?
        if dry_run:
            click.echo("Dry run - would convert:")
            for inp, outp in files:
                click.echo(f"  {inp} → {outp}")
            sys.exit(0)

        # Run pipeline
        result = asyncio.run(pipeline.process_batch(files))

        # Display results
        click.echo(f"\n{'='*50}")
        click.echo(f"Results: {result.successful} successful, {result.failed} failed")
        click.echo(f"Duration: {result.duration_seconds:.1f}s")
        click.echo(f"{'='*50}")

        # Show failed files
        if result.failed > 0:
            click.echo("\nFailed conversions:")
            for r in result.results:
                if not r.success:
                    click.echo(f"  {r.input_file.name}: {r.error}")

        # Exit with error code if any failures
        sys.exit(0 if result.failed == 0 else 1)

    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Conversion failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.argument('csv_file', type=click.Path(exists=True, path_type=Path))
@click.pass_context
def verify(ctx, csv_file: Path):
    """Verify a CSV file using js-verify.

    This command runs the verification step on an existing CSV file.
    """
    config_loader = ctx.obj['config_loader']
    verbose = ctx.obj['verbose']

    try:
        config = config_loader.load()
        pipeline = Pipeline(config)
        logger = get_logger(__name__)

        from .models.results import PipelineContext

        context = PipelineContext(
            config=config,
            input_file=csv_file,
            output_file=csv_file,
        )

        result = asyncio.run(pipeline._verify(csv_file, context))

        if result:
            click.echo(f"\nVerification results for {csv_file.name}:")
            click.echo(f"  Status: {'PASSED' if result['passed'] else 'FAILED'}")
            click.echo(f"  Questions: {result.get('verified_questions', 0)}/{result.get('total_questions', 0)} verified")

            if result.get('errors'):
                click.echo(f"  Errors: {len(result['errors'])}")
                for error in result['errors'][:5]:  # Show first 5
                    click.echo(f"    - {error}")
                if len(result['errors']) > 5:
                    click.echo(f"    ... and {len(result['errors']) - 5} more")

            if result.get('warnings'):
                click.echo(f"  Warnings: {len(result['warnings'])}")

            sys.exit(0 if result['passed'] else 1)
        else:
            click.echo("Verification failed to produce results")
            sys.exit(1)

    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Verification failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.argument('csv_file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--md-file', '-m',
    type=click.Path(exists=True, path_type=Path),
    help='Original MD file (for context)'
)
@click.option(
    '--output', '-o',
    type=click.Path(path_type=Path),
    help='Output file for fixed CSV (default: <input>_fixed.csv)'
)
@click.pass_context
def fix(ctx, csv_file: Path, md_file: Optional[Path], output: Optional[Path]):
    """Fix a CSV file using AI based on verification errors.

    This command:
    1. Verifies the CSV file
    2. If errors found, sends to AI for fixing
    3. Saves fixed version to new file
    4. Re-verifies the fixed version
    """
    config_loader = ctx.obj['config_loader']
    verbose = ctx.obj['verbose']

    try:
        config = config_loader.load()
        pipeline = Pipeline(config)
        logger = get_logger(__name__)

        from .models.results import PipelineContext
        from .core.pipeline import FixError

        context = PipelineContext(
            config=config,
            input_file=md_file or csv_file,
            output_file=csv_file,
        )

        # Step 1: Verify to get error report
        click.echo(f"Verifying {csv_file.name}...")
        verification_result = asyncio.run(pipeline._verify(csv_file, context))

        if not verification_result:
            click.echo("Verification failed to produce results")
            sys.exit(1)

        if verification_result.get('passed', True):
            click.echo(f"No errors found in {csv_file.name}")
            sys.exit(0)

        errors = verification_result.get('errors', [])
        click.echo(f"Found {len(errors)} errors")

        # Step 2: Read original MD if provided
        md_content = ""
        if md_file:
            click.echo(f"Reading MD file: {md_file.name}")
            md_content = md_file.read_text(encoding='utf-8')

        # Step 3: Read CSV content
        csv_content = csv_file.read_text(encoding='utf-8')

        # Step 4: Fix with AI
        click.echo("Sending to AI for fixing...")
        try:
            fixed_csv = asyncio.run(pipeline._fix_csv(
                md_content,
                csv_content,
                verification_result,
                context
            ))
        except FixError as e:
            click.echo(f"AI fixing failed: {e}", err=True)
            if verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

        # Step 5: Save fixed CSV
        if output is None:
            output = csv_file.parent / f"{csv_file.stem}_fixed{csv_file.suffix}"

        output.write_text(fixed_csv, encoding='utf-8')

        click.echo(f"Fixed CSV saved to {output}")

        # Step 6: Verify fixed version
        click.echo("Verifying fixed CSV...")
        fixed_verification = asyncio.run(pipeline._verify(output, context))

        if fixed_verification and fixed_verification.get('passed', True):
            click.echo("Verification PASSED")
            sys.exit(0)
        else:
            errors_after = len(fixed_verification.get('errors', [])) if fixed_verification else 0
            click.echo(f"Verification still has {errors_after} errors")
            sys.exit(1)

    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Fix failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option('--force', '-f', is_flag=True, help='Overwrite existing files')
@click.pass_context
def init(ctx, force: bool):
    """Initialize configuration file.

    Creates a default configuration file at config/default.yaml
    if it doesn't exist.
    """
    config_path = Path("config/default.yaml")

    if config_path.exists() and not force:
        click.echo(f"Configuration file already exists: {config_path}")
        click.echo("Use --force to overwrite")
        sys.exit(1)

    # Create config directory
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Default configuration
    default_config = """# AI MD to CSV Converter Configuration

pipeline:
  # Preprocessing stages
  preprocess:
    - name: "md_formatter"
      enabled: true
      options:
        fix_question_numbers: true
        normalize_spacing: true
        add_options_headers: true
    - name: "option_normalizer"
      enabled: true
      options:
        ensure_letter_prefixes: true
        validate_option_counts: true
    - name: "answer_validator"
      enabled: true
      options:
        warn_on_mismatch: true
        suggest_corrections: true

  # AI provider configuration
  provider:
    active: "${AI_PROVIDER:-groq}"
    settings:
      groq:
        model: "llama-3.3-70b-versatile"
        temperature: 0
        max_tokens: 16000
        max_retries: 5
      claude_cli:
        timeout: 300
        max_retries: 5

  # Postprocessing stages
  postprocess:
    - name: "csv_cleaner"
      enabled: true
      options:
        remove_code_blocks: true
        filter_non_csv_lines: true
        validate_header: true

  # Verification configuration
  verification:
    enabled: true
    method: "js_verify"
    js_verify_path: "../js-verify/verfifyCSV.js"
    auto_fix: false
    continue_on_error: true

# Input/output configuration
io:
  input_dir: "../md"
  output_dir: "output"
  csv_subdir: "csv"
  failed_subdir: "failed"
  reports_subdir: "reports"
  overwrite_existing: false
  backup_on_conversion: true
  backup_dir: "output/.backups"
  batch_size: 10
  parallel_workers: 1

# Logging configuration
logging:
  level: "INFO"
  format: "detailed"
  console_output: true
  file_output: true
  log_dir: "logs"

# Retry configuration
retry:
  max_retries: 5
  base_delay: 60
  exponential_backoff: true
  jitter: true
  jitter_range: 0.1

# Progress tracking
progress:
  enabled: true
  show_bar: true
  update_interval: 1
  save_intermediate: true
  checkpoint_file: "output/.progress.json"

# Default values for CSV output
defaults:
  csv:
    question_type: "objective"
    category: "Aptitude"
    difficulty: "medium"
    score: 5
    tags: "Aptitude,Numbers"
"""

    config_path.write_text(default_config)
    click.echo(f"Created configuration file: {config_path}")
    click.echo("\nEdit this file to customize the converter settings.")


@cli.command()
@click.pass_context
def status(ctx):
    """Show system status and configuration."""
    config_loader = ctx.obj['config_loader']
    verbose = ctx.obj['verbose']

    try:
        config = config_loader.load()

        click.echo("=== AI MD to CSV Converter Status ===\n")

        click.echo(f"Provider: {config.pipeline.provider.active}")
        click.echo(f"Input directory: {config.io.input_dir}")
        click.echo(f"Output directory: {config.io.output_dir}")
        click.echo(f"Verification: {'enabled' if config.pipeline.verification.enabled else 'disabled'}")

        click.echo(f"\nPreprocessors: {len(config.pipeline.preprocess)}")
        for p in config.pipeline.preprocess:
            status = "enabled" if p.get("enabled", True) else "disabled"
            click.echo(f"  - {p['name']}: {status}")

        click.echo(f"\nPostprocessors: {len(config.pipeline.postprocess)}")
        for p in config.pipeline.postprocess:
            status = "enabled" if p.get("enabled", True) else "disabled"
            click.echo(f"  - {p['name']}: {status}")

        if verbose:
            click.echo(f"\nLogging: {config.logging.level} ({config.logging.format})")
            click.echo(f"Retry: {config.retry.max_retries} max, {config.retry.base_delay}s base delay")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def main():
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == '__main__':
    main()
