#!/bin/bash

# Display header
echo "========================================"
echo "  MCP NATS Transport Docker Environment"
echo "========================================"
echo

# Check if Docker is installed
if ! command -v docker &>/dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &>/dev/null; then
    echo "Error: Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Build and start the containers
echo "Starting containers..."
docker-compose up --build

# Handle shutdown
function cleanup {
    echo
    echo "Shutting down..."
    docker-compose down
}

trap cleanup EXIT

# Wait for user to press Ctrl+C
echo "Press Ctrl+C to stop"
while true; do
    sleep 1
done