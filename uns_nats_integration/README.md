# UNS-MCP with NATS Transport

This project integrates UNS-MCP (Unstructured API MCP Server) with NATS.io as a transport layer, enabling distributed deployment of Unstructured API tools and connectors.

## Important: External Dependency

⚠️ **This integration requires the UNS-MCP project code which is not included in this repository.**

Before using this integration, you must:
1. Clone the UNS-MCP repository (contact Unstructured for access if necessary)
2. Place it in the same parent directory as this repository or install it as a package
3. Ensure the UNS-MCP Python package is in your Python path

## Overview

The Unstructured API provides tools for processing unstructured data through document processing workflows. This implementation:

1. Uses the MCP (Model Context Protocol) to expose Unstructured API functionality to LLMs
2. Replaces the standard stdio/SSE transport with NATS.io for distributed operation
3. Preserves all the connectors and tools from the original UNS-MCP
4. Provides a client implementation for LLM-powered interactions

## Components

- **UNS-MCP Server**: Provides document processing tools via MCP and NATS
- **UNS-MCP Client**: Connects to the server via NATS and integrates with Claude
- **Connectors**: Source and destination connectors for various data systems
- **NATS Transport**: Distributed communication and service discovery

## Requirements

- Python 3.9+
- NATS server
- Unstructured API key
- Anthropic API key (for client)
- Original UNS-MCP codebase accessible in the Python path

## Directory Structure

For this integration to work correctly, your directory structure should look like:

```
parent_directory/
├── UNS-MCP/              # Original UNS-MCP project
│   ├── connectors/
│   │   ├── source/
│   │   ├── destination/
│   │   └── ...
│   └── ...
└── nats-transport-for-MCP/  # This repository
    └── uns_nats_integration/
        └── ...
```

## Installation

1. Clone the UNS-MCP repository (if you have access):
   ```bash
   git clone https://github.com/unstructured-io/uns-mcp.git UNS-MCP
   ```

2. Clone this repository:
   ```bash
   git clone https://github.com/dronomyio/nats-transport-for-MCP.git
   ```

3. Install dependencies:
   ```bash
   pip install -e ./UNS-MCP
   pip install -e ./nats-transport-for-MCP
   pip install unstructured-client anthropic mcp nats-py python-dotenv rich
   ```

## Usage

1. Set up a NATS server:
   ```
   docker run -p 4222:4222 -p 8222:8222 --name nats-server nats:latest -js -m 8222
   ```

2. Set up environment variables in `.env`:
   ```
   NATS_URL=nats://localhost:4222
   NATS_SERVICE_NAME=uns.mcp.service
   UNSTRUCTURED_API_KEY=your_unstructured_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   ```

3. Start the server:
   ```bash
   python uns_nats_integration/server.py
   ```

4. In a separate terminal, start the client:
   ```bash
   python uns_nats_integration/client.py
   ```

## Docker Deployment

A docker-compose file is provided for easy deployment:

```
docker-compose -f uns_nats_integration/docker-compose.yml up -d
```

This starts a NATS server, UNS-MCP server, and an optional client container.

**Note:** The Dockerfiles assume that the UNS-MCP code is available in a directory at the same level as this repository.

## Development

To develop the UNS-MCP integration without Docker:

1. Install dependencies as described above

2. Set up environment variables:
   ```bash
   export NATS_URL=nats://localhost:4222
   export NATS_SERVICE_NAME=uns.mcp.service
   export UNSTRUCTURED_API_KEY=your_unstructured_api_key
   export ANTHROPIC_API_KEY=your_anthropic_api_key
   ```

3. Start the server:
   ```bash
   python uns_nats_integration/server.py
   ```

4. In a separate terminal, start the client:
   ```bash
   python uns_nats_integration/client.py
   ```

## License

This project is licensed under the MIT License.