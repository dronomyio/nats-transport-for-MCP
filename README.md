# MCP NATS Transport

NATS transport implementation for Model Context Protocol (MCP). This package enables using NATS.io as a transport mechanism for MCP clients and servers, providing distributed and scalable deployments.

## Features

- NATS client transport implementation
- NATS server transport implementation
- Support for distributed MCP deployments
- Service discovery and load balancing
- High availability and fault tolerance

## Installation

```bash
pip install mcp-nats-transport
```

## Quick Start

### Server

```python
from mcp.server.fastmcp.server import FastMcpServer
from mcp.server.fastmcp.tools import tool
from mcp.shared.session import Session
from mcp_nats_transport import NatsServerParameters, nats_server

# Define a simple tool
@tool
async def echo(text: str) -> str:
    """Echo the input text."""
    return text

# Create an MCP server
server = FastMcpServer()
server.tools.register(echo)

# Configure NATS transport
nats_params = NatsServerParameters(
    url="nats://localhost:4222",
    request_subject="mcp.request",
    response_subject="mcp.response",
)

# Start the server using NATS transport
async with nats_server(nats_params) as (read_stream, write_stream):
    session = Session()
    await server.run(session, read_stream, write_stream)
```

### Client

```python
from mcp.client.session import ClientSession
from mcp_nats_transport import NatsClientParameters, nats_client

# Configure NATS transport
nats_params = NatsClientParameters(
    url="nats://localhost:4222",
    request_subject="mcp.request",
    response_subject="mcp.response",
)

# Connect to the server using NATS transport
async with nats_client(nats_params) as (read_stream, write_stream):
    # Create a client session
    client = ClientSession()
    
    # Run initialization
    await client.initialize(read_stream, write_stream)
    
    # Get available tools
    tools = await client.list_tools()
    print(f"Available tools: {[tool.name for tool in tools.tools]}")
    
    # Call the echo tool
    result = await client.call_tool("echo", {"text": "Hello via NATS!"})
    print(f"Echo result: {result.content[0].text}")
```

## Docker Deployment

A Docker Compose configuration is provided for easy deployment of NATS server with examples:

```bash
docker-compose up
```

This will start:
- A NATS server
- An example MCP server with tools
- An example MCP client that connects to the server

## Documentation

For more detailed documentation, see [the documentation](./docs/README.md).

## Examples

Check out the examples directory for more usage patterns:

- [Simple Example](./examples/simple_example.py): Basic usage of NATS transport
- [Distributed Example](./examples/distributed_example.py): Advanced distributed deployment with multiple servers and clients

## Architecture

![NATS Transport Architecture](./docs/architecture.svg)

## Requirements

- Python 3.8+
- MCP Python SDK
- NATS.io server (for production use)

## License

dronomy.io License
