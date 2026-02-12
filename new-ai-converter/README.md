# AI MD to CSV Converter

A modular, configurable, AI-powered system for converting Markdown question files to CSV format with built-in preprocessing, postprocessing, and verification.

## Features

- **Multiple AI Providers**: Support for Groq API and Claude CLI
- **Configurable Pipeline**: YAML-based configuration with environment variable substitution
- **Preprocessing**: Automatic markdown formatting fixes and option normalization
- **Postprocessing**: CSV cleanup and validation
- **Built-in Verification**: Integration with js-verify for CSV validation
- **Async/Await**: Future-proof architecture for concurrent processing
- **Extensible**: Factory pattern for easy addition of new providers, preprocessors, and validators

## Installation

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (fast Python package manager)
- bun (for js-verify integration)
- Claude CLI (optional, for claude_cli provider)

### Setup

1. Clone or navigate to the project:
```bash
cd /home/positron/Documents/Guvi/test-automation/hyrenet-question-lib/new-ai-converter
```

2. Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Install dependencies with uv:
```bash
uv sync
```

4. Initialize configuration:
```bash
uv run python -m src.main init
```

5. Set up AI provider API keys:

**For Groq:**
```bash
export GROQ_API_KEY="your-groq-api-key"
```

**For Claude CLI:**
```bash
npm install -g @anthropic-ai/claude-cli
```

## Usage

### Basic Commands

**Convert all MD files in a directory:**
```bash
uv run python -m src.main convert
```

**Convert a specific file:**
```bash
uv run python -m src.main convert input/test.md
```

**Use custom output location:**
```bash
uv run python -m src.main convert input/ -o output/
```

**Use specific AI provider:**
```bash
uv run python -m src.main convert --provider groq
uv run python -m src.main convert --provider claude_cli
```

**Skip verification:**
```bash
uv run python -m src.main convert --no-verify
```

**Dry run (show what would be done):**
```bash
uv run python -m src.main convert --dry-run
```

**Verify an existing CSV file:**
```bash
uv run python -m src.main verify output/test.csv
```

**Show system status:**
```bash
uv run python -m src.main status
```

### Configuration

The converter uses YAML configuration files. See `config/default.yaml` for all options:

```yaml
pipeline:
  provider:
    active: "${AI_PROVIDER:-groq}"
  verification:
    enabled: true
    js_verify_path: "../js-verify/verfifyCSV.js"

io:
  input_dir: "../md"
  output_dir: "output"
  csv_subdir: "csv"
  parallel_workers: 1
```

### Environment Variables

You can override configuration using environment variables:

```bash
export AI_PROVIDER=claude_cli
uv run python -m src.main convert
```

### Development

**Install dev dependencies:**
```bash
uv sync --dev
```

**Run tests:**
```bash
uv run pytest
```

**Format code:**
```bash
uv run black src/
```

**Lint code:**
```bash
uv run ruff check src/
```

## Architecture

### Pipeline Stages

1. **Preprocessing**: MD format fixing, option normalization, answer validation
2. **Conversion**: AI-based MD to CSV conversion
3. **Postprocessing**: CSV cleanup, conversational text removal
4. **Verification**: js-verify integration for validation

### Directory Structure

```
new-ai-converter/
├── config/              # Configuration files
├── src/
│   ├── core/           # Pipeline, config, exceptions
│   ├── providers/      # AI providers (Groq, Claude CLI)
│   ├── preprocessors/  # MD preprocessing
│   ├── postprocessors/ # CSV postprocessing
│   ├── validators/     # Verification wrappers
│   ├── utils/          # Logging, retry, file utilities
│   └── models/         # Dataclasses for results
├── templates/
│   └── prompts/        # System and conversion prompts
├── docs/               # Documentation
└── output/             # Generated files
```

## Extending the System

### Adding a New AI Provider

1. Create `src/providers/new_provider.py`:
```python
from .base import BaseProvider

class NewProvider(BaseProvider):
    async def convert(self, system_prompt: str, user_prompt: str) -> str:
        # Implementation
        pass

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> Optional[float]:
        # Cost calculation
        pass

    @property
    def supports_async(self) -> bool:
        return True
```

2. Register in `src/providers/factory.py`:
```python
class ProviderFactory:
    _providers = {
        "groq": GroqProvider,
        "claude_cli": ClaudeCliProvider,
        "new_provider": NewProvider,  # Add here
    }
```

3. Add configuration in `config/default.yaml`:
```yaml
pipeline:
  provider:
    settings:
      new_provider:
        model: "model-name"
        # Provider-specific options
```

### Adding a New Preprocessor

1. Create `src/preprocessors/new_preprocessor.py`:
```python
from .base import BasePreprocessor

class NewPreprocessor(BasePreprocessor):
    async def process(self, content: str, context) -> str:
        # Implementation
        return content
```

2. Register in factory and enable in config.

## Preparing MD Files

See [docs/MD_PREPARATION_GUIDE.md](docs/MD_PREPARATION_GUIDE.md) for detailed guidelines on preparing markdown files for conversion.

## Troubleshooting

### "Groq API key not provided"
Set the `GROQ_API_KEY` environment variable or add it to your config.

### "bun: command not found"
Install bun from https://bun.sh or disable verification with `--no-verify`.

### Verification fails
The CSV may have formatting issues. Check the verification report at `js-verify/verification-report.json`.

## License

This project is part of the hyrenet-question-lib system.
