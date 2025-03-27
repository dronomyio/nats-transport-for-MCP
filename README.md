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

### Running the Full MCP Example

```bash
docker-compose up
```

This will start:
- A NATS server
- An example MCP server with tools
- An example MCP client that connects to the server

### Running the Simple NATS Example

A simplified example that demonstrates the core NATS request/reply pattern is available:

```bash
docker-compose -f docker-compose-simple.yml up
```

This runs a single container that demonstrates both the server and client sides of NATS communication.

### Testing Individually in Separate Windows

To test the components separately:

1. **Start the NATS server in one terminal**:
   ```bash
   docker run -p 4222:4222 -p 8222:8222 nats:latest --jetstream
   ```

2. **Run the server component in another terminal**:
   ```bash
   python -c "
   import asyncio
   import logging
   from docker_example import run_server
   logging.basicConfig(level=logging.INFO)
   asyncio.run(run_server('nats://localhost:4222'))
   "
   ```

3. **Run the client component in a third terminal**:
   ```bash
   python -c "
   import asyncio
   import logging
   from docker_example import run_client
   logging.basicConfig(level=logging.INFO)
   asyncio.run(run_client('nats://localhost:4222'))
   "
   ```

You can also create simple server.py and client.py files to make this easier:

**server.py**:
```python
import asyncio
import logging
from docker_example import run_server

logging.basicConfig(level=logging.INFO)
asyncio.run(run_server('nats://localhost:4222'))
```

**client.py**:
```python
import asyncio
import logging
from docker_example import run_client

logging.basicConfig(level=logging.INFO)
asyncio.run(run_client('nats://localhost:4222'))
```

Then run each script in a separate terminal after starting the NATS server.

## Documentation

For more detailed documentation, see [the documentation](./docs/README.md).

## Examples

Check out the examples directory for more usage patterns:

- [Simple Example](./examples/simple_example.py): Basic usage of NATS transport
- [Distributed Example](./examples/distributed_example.py): Advanced distributed deployment with multiple servers and clients

## Architecture

![NATS Transport Architecture](./docs/architecture.svg)

## Distributed Multi-Cloud Setup

You can deploy MCP servers with NATS transport across multiple cloud providers to create a distributed, cross-cloud AI/ML architecture. Below is an example of deploying fine-tuned LLMs on different cloud platforms:

### Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    AWS EC2      │     │ NATS.io Server  │     │  GCP Instance   │
│ Llama 3 (FT)    │     │    (AWS EC2)    │     │ Llama 2 (FT)    │
│ MCP Server 1    │     │                 │     │ MCP Server 2    │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                                 │
                          ┌──────┴───────┐
                          │ Your App     │
                          │ (MCP Client) │
                          │ Any Location │
                          └──────────────┘
```

### 1. Set Up NATS Server (AWS EC2)

```bash
# Provision EC2 instance
aws ec2 run-instances --image-id ami-xxxxxxxxx --instance-type t3.medium --key-name your-key

# SSH into instance and install Docker
ssh -i your-key.pem ec2-user@your-nats-instance
sudo yum update -y && sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user

# Create NATS config
mkdir -p ~/nats/config
cat > ~/nats/config/nats.conf << EOF
jetstream {
  store_dir: "/data"
  max_mem: 1G
  max_file: 10G
}

# Authentication
accounts {
  MCP {
    users: [
      {user: "mcp", password: "your-secure-password"}
    ]
  }
}
EOF

# Run NATS with Docker
docker run -d --name nats-server \
  -p 4222:4222 -p 8222:8222 \
  -v ~/nats/config:/etc/nats \
  -v ~/nats/data:/data \
  nats:latest -c /etc/nats/nats.conf
```

Configure security groups to allow inbound traffic on ports 4222 and 8222.

### 2. Deploy MCP Server with Llama 3 on AWS

```bash
# Install dependencies
pip3 install --upgrade pip
pip3 install mcp-nats-transport llama-cpp-python

# Create server script
cat > ~/mcp-server-llama3/server.py << EOF
import asyncio
import logging
from mcp.server.fastmcp.server import FastMcpServer
from mcp.server.fastmcp.tools import tool
from mcp.shared.session import Session
from mcp_nats_transport import NatsServerParameters, nats_server
from llama_cpp import Llama

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Llama model
model = Llama(
    model_path="/home/ec2-user/models/llama3-ft-model.bin",
    n_ctx=4096,
    n_gpu_layers=-1
)

# Define LLM tool
@tool
async def llama3_generate(prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
    """Generate text using fine-tuned Llama 3 model."""
    output = model(prompt, max_tokens=max_tokens, temperature=temperature)
    return output["choices"][0]["text"]

async def main():
    # Create MCP server
    server = FastMcpServer()
    server.tools.register(llama3_generate)
    
    # Configure NATS transport
    nats_params = NatsServerParameters(
        url="nats://mcp:your-secure-password@your-nats-instance:4222",
        service_name="mcp.llama3",
        server_id="llama3-server"
    )
    
    # Start server with NATS transport
    async with nats_server(nats_params) as (read_stream, write_stream):
        session = Session()
        await server.run(session, read_stream, write_stream)

if __name__ == "__main__":
    asyncio.run(main())
EOF

# Create systemd service
sudo systemctl enable mcp-llama3
sudo systemctl start mcp-llama3
```

### 3. Deploy MCP Server with Llama 2 on GCP

```bash
# SSH into GCP instance
gcloud compute ssh llama2-instance

# Install dependencies
pip3 install mcp-nats-transport transformers torch

# Create server script
cat > ~/mcp-server-llama2/server.py << EOF
import asyncio
import logging
from mcp.server.fastmcp.server import FastMcpServer
from mcp.server.fastmcp.tools import tool
from mcp.shared.session import Session
from mcp_nats_transport import NatsServerParameters, nats_server
from transformers import AutoModelForCausalLM, AutoTokenizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Llama 2 model
tokenizer = AutoTokenizer.from_pretrained("/home/user/models/llama2-ft")
model = AutoModelForCausalLM.from_pretrained(
    "/home/user/models/llama2-ft",
    device_map="auto"
)

# Define LLM tool
@tool
async def llama2_generate(prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
    """Generate text using fine-tuned Llama 2 model."""
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(
        inputs["input_ids"],
        max_new_tokens=max_tokens,
        temperature=temperature,
        do_sample=True
    )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response[len(prompt):]

async def main():
    # Create MCP server
    server = FastMcpServer()
    server.tools.register(llama2_generate)
    
    # Configure NATS transport
    nats_params = NatsServerParameters(
        url="nats://mcp:your-secure-password@your-nats-instance:4222",
        service_name="mcp.llama2",
        server_id="llama2-server"
    )
    
    # Start server with NATS transport
    async with nats_server(nats_params) as (read_stream, write_stream):
        session = Session()
        await server.run(session, read_stream, write_stream)

if __name__ == "__main__":
    asyncio.run(main())
EOF
```

### 4. Create Client Application

Your application can run anywhere with network access to the NATS server:

```python
import asyncio
import logging
from mcp.client.session import ClientSession
from mcp_nats_transport import NatsClientParameters, nats_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_client():
    # Configure NATS transport
    nats_params = NatsClientParameters(
        url="nats://mcp:your-secure-password@your-nats-instance:4222",
        service_name="mcp",  # Will discover all MCP services
        client_id="my-app-client"
    )
    
    # Connect to NATS
    async with nats_client(nats_params) as (read_stream, write_stream):
        # Create client session
        client = ClientSession()
        await client.initialize(read_stream, write_stream)
        
        # Discover available tools
        tools = await client.list_tools()
        logger.info(f"Available tools: {[tool.name for tool in tools.tools]}")
        
        # Call Llama 3 on AWS
        if "llama3_generate" in [t.name for t in tools.tools]:
            result = await client.call_tool(
                "llama3_generate", 
                {"prompt": "Explain quantum computing", "max_tokens": 500}
            )
            logger.info(f"Llama 3 result: {result.content[0].text}")
        
        # Call Llama 2 on GCP
        if "llama2_generate" in [t.name for t in tools.tools]:
            result = await client.call_tool(
                "llama2_generate", 
                {"prompt": "Describe machine learning applications", "max_tokens": 500}
            )
            logger.info(f"Llama 2 result: {result.content[0].text}")

if __name__ == "__main__":
    asyncio.run(run_client())
```

### Key Benefits of This Architecture

1. **Cross-Cloud Deployment**: Run specialized models on different cloud providers
2. **Automatic Service Discovery**: Clients automatically discover all available tools 
3. **Load Balancing**: Deploy multiple instances of each server for high availability
4. **Location Transparency**: Clients don't need to know where servers are deployed
5. **Scalability**: Easily add more servers or models without changing client code

## Requirements

- Python 3.8+
- MCP Python SDK
- NATS.io server (for production use)

## License

dronomy.io License
