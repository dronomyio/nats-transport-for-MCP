# UNS-MCP-NATS

A Python package that integrates UNS-MCP (Unstructured API MCP Server) with NATS.io as a transport layer, enabling distributed deployment of Unstructured API tools and connectors.

## Features

- **Distributed Architecture**: Deploy UNS-MCP services across multiple instances with NATS
- **Service Discovery**: Automatic discovery of available UNS-MCP tools and connectors
- **Load Balancing**: Distribute requests across multiple server instances
- **LLM Integration**: Built-in Claude integration for AI-assisted document workflows
- **Docker Support**: Multi-stage Docker builds for containerized deployment

## Installation

### From PyPI (Recommended)

```bash
# Install core package
pip install uns-mcp-nats

# Install with client dependencies (for using the Claude integration)
pip install uns-mcp-nats[client]
```

### From Source

```bash
git clone https://github.com/dronomyio/nats-transport-for-MCP.git
cd nats-transport-for-MCP/uns_mcp_nats
pip install -e .
```

## Dependencies

This package requires:

- UNS-MCP (will be installed automatically when using PyPI)
- NATS.io Python client
- Unstructured API client
- Anthropic Python SDK (optional, for client usage)

## Usage

### Server

```python
import asyncio
from uns_mcp_nats import UNSMcpNatsServer, UNSMcpNatsConfig

async def main():
    # Create server with default configuration from environment variables
    server = UNSMcpNatsServer()
    
    # Or with custom configuration
    config = UNSMcpNatsConfig(
        nats=UNSMcpNatsConfig.NatsConfig(
            url="nats://localhost:4222",
            service_name="uns.mcp.service"
        ),
        unstructured=UNSMcpNatsConfig.UnstructuredConfig(
            api_key="your-api-key"
        )
    )
    server = UNSMcpNatsServer(config)
    
    # Run the server
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### Client

```python
import asyncio
from uns_mcp_nats import UNSMcpNatsClient, UNSMcpNatsConfig

async def main():
    # Create client with default configuration from environment variables
    client = UNSMcpNatsClient()
    
    # Connect to server
    await client.connect()
    
    # Process a query with LLM integration
    await client.process_query("List available sources")
    
    # Or run an interactive chat loop
    await client.chat_loop()
    
    # Clean up
    await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

### Command Line Usage

The package also provides command-line scripts:

```bash
# Start the server
python -m uns_mcp_nats.server

# Start the client
python -m uns_mcp_nats.client
```

## Configuration

Configuration can be provided through environment variables or a `.env` file:

```
# NATS Configuration
NATS_URL=nats://localhost:4222
NATS_SERVICE_NAME=uns.mcp.service

# Unstructured API Configuration
UNSTRUCTURED_API_KEY=your_unstructured_api_key

# Client Configuration (optional)
ANTHROPIC_API_KEY=your_anthropic_api_key
CONFIRM_TOOL_USE=true
```

## Docker Deployment

The package includes Docker support for easy deployment:

```bash
# Build and run with Docker Compose
docker-compose -f docker-compose.yml up -d
```

## Examples

See the `examples` directory for more detailed usage examples:

- `simple_workflow.py`: Basic workflow example
- `ai_assisted_workflow.py`: AI-assisted workflow example using Claude

## License

This project is licensed under the MIT License.