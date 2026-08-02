# gyra-client

Python client library for OpenGyra.

## Overview

`gyra-client` provides a Python SDK for interacting with OpenGyra services. It allows developers to integrate OpenGyra's AI-SRE capabilities into their own applications.

## Features

- **REST API Client**: Easy-to-use Python client for OpenGyra services
- **Async Support**: Full async/await support
- **Type Hints**: Comprehensive type annotations for IDE support

## Installation

```bash
pip install gyra-client
```

## Usage

```python
from gyra_client import GyraClient

# Create a client
client = GyraClient(base_url="http://localhost:7777")

# Use the client
result = await client.analyze_issue(...)
```

## Documentation

- [Gyra Main Documentation](../README.md)
- [GitHub Repository](https://github.com/gyra-ai/Gyra)

## License

MIT