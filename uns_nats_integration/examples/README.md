# UNS-MCP with NATS Transport Examples

This directory contains examples demonstrating how to use the UNS-MCP (Unstructured API MCP Server) with NATS.io as a transport layer.

## Examples

### 1. Simple Workflow Example

`simple_workflow.py` demonstrates the basic usage of UNS-MCP with NATS transport:
- Connecting to the UNS-MCP server via NATS
- Listing available sources and destinations
- Interacting with the API's tools

Run the example:
```bash
python simple_workflow.py
```

### 2. AI-Assisted Workflow Example

The same file also includes an AI-assisted workflow that uses Claude to help create and manage document processing workflows.

Run the AI-assisted example:
```bash
python simple_workflow.py --ai
```

This example shows how to:
- Integrate Claude with UNS-MCP via NATS
- Use Claude to recommend appropriate tools
- Create a conversational interface for document processing

## Configuration

Before running the examples, make sure to set the required environment variables:

```bash
# NATS Configuration
export NATS_URL=nats://localhost:4222
export NATS_SERVICE_NAME=uns.mcp.service

# API Keys
export UNSTRUCTURED_API_KEY=your_unstructured_api_key
export ANTHROPIC_API_KEY=your_anthropic_api_key  # Required for AI-assisted example
```

You can also create a `.env` file in the root directory with these variables.

## Running with Docker

You can run these examples using Docker:

```bash
# First, start the UNS-MCP server and NATS
docker-compose -f ../docker-compose.yml up -d nats uns-mcp-server

# Then run the example in a container
docker run --rm -it --network uns-net \
  -e NATS_URL=nats://nats:4222 \
  -e NATS_SERVICE_NAME=uns.mcp.service \
  -e UNSTRUCTURED_API_KEY=your_key \
  -e ANTHROPIC_API_KEY=your_key \
  -v $(pwd):/app/examples \
  uns-mcp-client python /app/examples/simple_workflow.py
```