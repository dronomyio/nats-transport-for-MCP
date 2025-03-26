# NATS Transport for MCP

MCP supports multiple transport mechanisms for communication between clients and servers. This page details how to use NATS.io as a transport for MCP, enabling distributed and scalable deployments.

## What is NATS?

[NATS](https://nats.io/) is a simple, secure and high-performance messaging system for cloud-native applications, IoT messaging, and microservices architectures. It provides:

- Publish/Subscribe messaging
- Request/Reply services
- Queueing
- Load balancing
- Persistence
- Scalability

Using NATS as an MCP transport provides several advantages:

- **Scalability**: Connect multiple clients to multiple servers
- **Service Discovery**: Automatically find available MCP servers
- **Load Balancing**: Distribute requests across server instances
- **Fault Tolerance**: Resilience to individual server failures
- **Reduced Latency**: Efficient message routing

## Using NATS Transport in MCP

### Client-Side Configuration

To use NATS as a transport on the client side:

```python
from mcp.client.nats_transport import NatsClientParameters, nats_client
from mcp.client.session import ClientSession

# Configure NATS transport
nats_params = NatsClientParameters(
    url="nats://localhost:4222",
    request_subject="mcp.request",
    response_subject="mcp.response",
    client_id="my-mcp-client"
)

# Connect using NATS transport
async with nats_client(nats_params) as (read_stream, write_stream):
    # Create a client session
    client = ClientSession()
    
    # Initialize the connection
    await client.initialize(read_stream, write_stream)
    
    # Use the client as normal
    tools = await client.list_tools()
    result = await client.call_tool("some_tool", {"arg": "value"})
```

### Server-Side Configuration

To use NATS as a transport on the server side:

```python
from mcp.server.nats_transport import NatsServerParameters, nats_server
from mcp.server.fastmcp.server import FastMcpServer
from mcp.shared.session import Session

# Create an MCP server
server = FastMcpServer()

# Register tools, prompts, etc.
server.tools.register(my_tool)

# Configure NATS transport
nats_params = NatsServerParameters(
    url="nats://localhost:4222",
    request_subject="mcp.request",
    response_subject="mcp.response",
    server_id="my-mcp-server"
)

# Start the server using NATS transport
async with nats_server(nats_params) as (read_stream, write_stream):
    # Create a session and run the server
    session = Session()
    await server.run(session, read_stream, write_stream)
```

## Architecture

The NATS transport for MCP works by:

1. Connecting to a NATS server
2. Publishing JSON-RPC messages to request subjects
3. Subscribing to response subjects
4. Translating between NATS messages and MCP's internal streams

![NATS Transport Architecture](/images/nats-transport-architecture.svg)

## Distributed MCP Deployment

NATS enables distributed MCP deployments where multiple servers and clients communicate through a central NATS server or cluster:

```
┌────────────┐    ┌────────────┐    ┌────────────┐
│ MCP Client │    │ MCP Client │    │ MCP Client │
└─────┬──────┘    └─────┬──────┘    └─────┬──────┘
      │                 │                 │
      └─────────────────┼─────────────────┘
                        │
                  ┌─────┴──────┐
                  │ NATS Server│
                  └─────┬──────┘
                        │
      ┌─────────────────┼─────────────────┐
      │                 │                 │
┌─────┴──────┐    ┌─────┴──────┐    ┌─────┴──────┐
│ MCP Server │    │ MCP Server │    │ MCP Server │
│ (Tools A)  │    │ (Tools B)  │    │ (Tools C)  │
└────────────┘    └────────────┘    └────────────┘
```

This setup enables:

- **Specialized Servers**: Different MCP servers can provide different sets of tools
- **High Availability**: Multiple servers can provide the same tools
- **Horizontal Scaling**: Add more server instances as needed
- **Service Discovery**: Clients automatically discover all available tools

## Subject Naming Patterns

When using NATS with MCP, you can implement different patterns for subject names:

### Basic Request/Response

The simplest pattern uses a single request subject and a single response subject:

- `mcp.request`: For all client requests to any server
- `mcp.response`: For all server responses to any client

This works well for simple deployments but doesn't provide message routing control.

### Service-Based Subjects

For more control, use service-specific subjects:

- `mcp.service.weather.request`: Requests for weather tools
- `mcp.service.weather.response`: Responses from weather servers
- `mcp.service.calculator.request`: Requests for calculator tools
- `mcp.service.calculator.response`: Responses from calculator servers

### Client-Specific Responses

For targeted responses to specific clients:

- `mcp.request`: Shared request subject
- `mcp.response.client_123`: Responses for client_123 only

## Examples

See the provided examples for complete implementations:

- [Basic NATS Transport Example](/examples/fastmcp/nats_transport.py)
- [Distributed MCP with NATS](/examples/fastmcp/distributed_nats.py)

## Requirements

- A running NATS server (see [NATS.io documentation](https://docs.nats.io/) for setup instructions)
- MCP Python SDK with the NATS Python client installed