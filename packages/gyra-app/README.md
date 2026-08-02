# gyra-app

Main application package for Gyra.

## Overview

`gyra-app` is the main application package that provides the Gyra server and web interface. It integrates all the core components and extensions to provide a complete Multi-Agent development and runtime platform.

## Features

- **Web Server**: FastAPI-based REST API server
- **Web UI**: Next.js based chat interface
- **Static Assets**: Pre-built web assets for deployment

## Installation

```bash
uv sync --all-packages --frozen
```

## Quick Start

1. Configure the API_KEY in your config file (e.g., `gyra-proxy-aliyun.toml`)
2. Run the server:
```bash
uv run python packages/gyra-app/src/gyra_app/gyra_server.py --config configs/gyra-proxy-aliyun.toml
```
3. Access the web UI at http://localhost:7777

## Project Structure

```
packages/gyra-app/
├── src/gyra_app/
│   ├── static/web/     # Pre-built web assets
│   ├── gyra_server.py  # Main server entry
│   └── ...
└── pyproject.toml
```

## Documentation

- [Gyra Main Documentation](../README.md)
- [DeepWiki](https://deepwiki.com/gyra-ai/Gyra)

## License

MIT