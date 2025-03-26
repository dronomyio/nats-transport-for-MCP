FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir pip setuptools wheel
RUN pip install --no-cache-dir "mcp>=0.1.0" "nats-py>=2.1.0" "anyio>=3.6.0" "pydantic>=2.0.0"

# Copy source code
COPY src ./src
COPY examples ./examples

# Install the package
RUN pip install -e .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "-m", "examples.simple_example"]