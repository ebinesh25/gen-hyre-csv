"""Configuration management system using YAML with environment variable substitution."""
import os
import re
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from .exceptions import ConfigError


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_retries: int = 5
    base_delay: int = 60
    exponential_backoff: bool = True
    jitter: bool = True
    jitter_range: float = 0.1


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "detailed"
    console_output: bool = True
    file_output: bool = True
    log_dir: Path = field(default_factory=lambda: Path("logs"))


@dataclass
class IOConfig:
    """Input/output configuration."""
    input_dir: Path = field(default_factory=lambda: Path("../md"))
    output_dir: Path = field(default_factory=lambda: Path("output"))
    csv_subdir: str = "csv"
    failed_subdir: str = "failed"
    reports_subdir: str = "reports"
    overwrite_existing: bool = False
    backup_on_conversion: bool = True
    backup_dir: Path = field(default_factory=lambda: Path("output/.backups"))
    batch_size: int = 10
    parallel_workers: int = 1


@dataclass
class ProviderConfig:
    """Provider configuration."""
    active: str = "groq"
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationConfig:
    """Verification configuration."""
    enabled: bool = True
    method: str = "js_verify"
    js_verify_path: str = "../js-verify/verfifyCSV.js"
    auto_fix: bool = False
    continue_on_error: bool = True


@dataclass
class FixingConfig:
    """AI-based CSV fixing configuration."""
    enabled: bool = False
    auto_fix_on_failure: bool = False
    max_attempts: int = 1
    provider: str = "claude_cli"
    validate_after_fix: bool = True
    fail_on_unfixable: bool = False


@dataclass
class PipelineConfig:
    """Pipeline configuration."""
    preprocess: List[Dict[str, Any]] = field(default_factory=list)
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    postprocess: List[Dict[str, Any]] = field(default_factory=list)
    verification: VerificationConfig = field(default_factory=VerificationConfig)
    fixing: FixingConfig = field(default_factory=FixingConfig)


@dataclass
class ProgressConfig:
    """Progress tracking configuration."""
    enabled: bool = True
    show_bar: bool = True
    update_interval: int = 1
    save_intermediate: bool = True
    checkpoint_file: str = "output/.progress.json"


@dataclass
class DefaultsConfig:
    """Default values for CSV output."""
    csv: Dict[str, Any] = field(default_factory=lambda: {
        "question_type": "objective",
        "category": "Aptitude",
        "difficulty": "medium",
        "score": 5,
        "tags": "Aptitude,Numbers",
    })


@dataclass
class Config:
    """Main configuration container."""
    converter: Dict[str, str] = field(default_factory=dict)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    io: IOConfig = field(default_factory=IOConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    progress: ProgressConfig = field(default_factory=ProgressConfig)
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)


class ConfigLoader:
    """Loads and validates configuration from YAML files."""

    DEFAULT_CONFIG_PATHS = [
        Path("config/default.yaml"),
        Path("/etc/ai-converter/config.yaml"),
        Path("~/.config/ai-converter/config.yaml"),
    ]

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize config loader.

        Args:
            config_path: Optional custom config path
        """
        self.config_path = config_path
        self._raw_config: Dict[str, Any] = {}

    def load(self) -> Config:
        """Load configuration from file with environment variable substitution.

        Returns:
            Config object

        Raises:
            ConfigError: If configuration is invalid or cannot be loaded
        """
        # Load base config
        loaded = False
        for path in self.DEFAULT_CONFIG_PATHS:
            if self.config_path:
                path = self.config_path
            if path.exists():
                with open(path) as f:
                    self._raw_config = yaml.safe_load(f)
                loaded = True
                break

        if not loaded:
            raise ConfigError(f"No configuration file found. Searched: {self.DEFAULT_CONFIG_PATHS}")

        # Substitute environment variables
        self._raw_config = self._substitute_env_vars(self._raw_config)

        # Construct Config object
        return self._build_config()

    def _substitute_env_vars(self, config: Any) -> Any:
        """Recursively substitute ${VAR} patterns with environment variables.

        Supports ${VAR} and ${VAR:-default} syntax.

        Args:
            config: Configuration value (dict, list, or string)

        Returns:
            Configuration with environment variables substituted
        """
        if isinstance(config, str):
            # Match ${VAR} or ${VAR:-default} patterns
            pattern = r'\$\{([^}:]+)(:-([^}]*))?\}'

            def replacer(match):
                var_name = match.group(1)
                default = match.group(3) or ""
                return os.getenv(var_name, default)

            return re.sub(pattern, replacer, config)
        elif isinstance(config, dict):
            return {k: self._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]

        return config

    def _build_config(self) -> Config:
        """Build Config dataclass from raw config dict.

        Returns:
            Config object
        """
        # Build nested configs
        pipeline_cfg = self._raw_config.get("pipeline", {})
        io_cfg = self._raw_config.get("io", {})
        logging_cfg = self._raw_config.get("logging", {})
        retry_cfg = self._raw_config.get("retry", {})
        progress_cfg = self._raw_config.get("progress", {})
        defaults_cfg = self._raw_config.get("defaults", {})

        return Config(
            converter=self._raw_config.get("converter", {}),
            pipeline=PipelineConfig(
                preprocess=pipeline_cfg.get("preprocess", []),
                provider=ProviderConfig(
                    active=pipeline_cfg.get("provider", {}).get("active", "groq"),
                    settings=pipeline_cfg.get("provider", {}).get("settings", {})
                ),
                postprocess=pipeline_cfg.get("postprocess", []),
                verification=VerificationConfig(**pipeline_cfg.get("verification", {})),
                fixing=FixingConfig(**pipeline_cfg.get("fixing", {}))
            ),
            io=IOConfig(**{k: Path(v) if isinstance(v, str) and ('dir' in k or 'path' in k) else v
                           for k, v in io_cfg.items()}),
            logging=LoggingConfig(**{k: Path(v) if isinstance(v, str) and k == 'log_dir' else v
                                    for k, v in logging_cfg.items()}),
            retry=RetryConfig(**retry_cfg),
            progress=ProgressConfig(**progress_cfg),
            defaults=DefaultsConfig(**defaults_cfg)
        )
