# UNS-MCP with NATS Transport

This project integrates UNS-MCP (Unstructured API MCP Server) with NATS.io as a transport layer, enabling distributed deployment of Unstructured API tools and connectors.

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
- Original UNS-MCP codebase accessible in the parent directory

## Installation

1. Set up a NATS server:
   ```
   docker run -p 4222:4222 -p 8222:8222 --name nats-server nats:latest -js -m 8222
   ```

2. Install dependencies:
   ```
   pip install unstructured-client anthropic mcp nats-py python-dotenv rich
   ```

3. Set up environment variables in `.env`:
   ```
   NATS_URL=nats://localhost:4222
   NATS_SERVICE_NAME=uns.mcp.service
   UNSTRUCTURED_API_KEY=your_unstructured_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   ```

## Usage

1. Start the server:
   ```
   python server.py
   ```

2. In a separate terminal, start the client:
   ```
   python client.py
   ```

3. Interact with the client by typing queries about document processing:
   - "List available sources"
   - "Create a workflow to process PDFs from S3"
   - "Run workflow X and check its status"

## Architecture

The system follows a distributed architecture:

- **Client**: Connects to NATS server, discovers MCP service, sends user queries to Claude and executes the recommended tools
- **NATS**: Provides service discovery, load balancing, and messaging
- **Server**: Hosts MCP tools, connects to Unstructured API, processes requests

Multiple servers can be deployed for load balancing or specialized functionality, with clients automatically discovering available services through NATS.

## Docker Deployment

A docker-compose file is provided for easy deployment:

```
docker-compose up -d
```

This starts a NATS server, UNS-MCP server, and an optional client container.

## Development

See the parent UNS-MCP project for details on adding new connectors or tools.

## License

This project is licensed under the same terms as the parent UNS-MCP project.