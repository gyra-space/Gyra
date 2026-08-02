# gyra-core

Core package for Gyra, the AI-Native Multi-Agent development and runtime framework.

## Overview

`gyra-core` is the foundational package that contains core modules and utilities used across all Gyra packages and services. It provides the fundamental infrastructure for building, debugging, and running collaborating AI agents.

## Features

- **Multi-Agent Architecture**: Framework for building collaborative AI agents
- **ReAct Master Agent**: Advanced reasoning agent with doom loop detection, session compaction, and output truncation
- **Model Proxy**: Support for multiple LLM providers (OpenAI, Anthropic, Azure, etc.)
- **AWEL Operators**: Rich set of operators for building AI workflows
- **Tools & Permissions**: Tool abstraction with risk levels and permission rulesets

## Installation

```bash
# From source
uv sync --all-packages --frozen
```

## Dependencies

Key dependencies include:
- `aiohttp` - Async HTTP client
- `pydantic` - Data validation
- `SQLAlchemy` - Database ORM
- `duckdb` - Embedded analytical database
- `uvicorn` - ASGI server

Optional dependencies:
- `agent` - Agent-related functionality
- `framework` - Full framework features
- `hf` - HuggingFace integration
- `code` - Code execution support

## Usage

```python
from gyra import ...

# Build your Multi-Agent application
```

## Documentation

- [Gyra Documents](https://deepwiki.com/gyra-ai/Gyra)
- [GitHub Repository](https://github.com/gyra-ai/Gyra)

## License

MIT