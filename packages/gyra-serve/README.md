# gyra-serve

Backend service package for Gyra.

## Overview

`gyra-serve` provides the backend API services for Gyra, including:

- **Agent Services**: Multi-agent collaboration and management
- **Conversation Management**: Chat session handling
- **Knowledge Management**: RAG-based knowledge retrieval
- **Data Source Management**: Database and data source connections
- **Skill Management**: Agent skill registration and execution
- **Flow Management**: Workflow orchestration

## Features

- **RESTful APIs**: Comprehensive API endpoints for all services
- **Async Support**: Full async/await architecture
- **Database Integration**: Support for MySQL, PostgreSQL, DuckDB
- **Vector Storage**: ChromaDB, Milvus, Weaviate integration

## Installation

```bash
uv sync --all-packages --frozen
```

## Project Structure

```
packages/gyra-serve/
├── src/gyra_serve/
│   ├── agent/           # Agent services
│   ├── conversation/    # Conversation management
│   ├── datasource/      # Data source connections
│   ├── gyras/         # Risk management
│   ├── memory/          # Memory services
│   ├── skill/           # Skill management
│   ├── flow/            # Flow orchestration
│   └── ...
└── pyproject.toml
```

## Documentation

- [Gyra Main Documentation](../README.md)
- [DeepWiki](https://deepwiki.com/gyra-ai/Gyra)

## License

MIT