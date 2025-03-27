FROM python:3.10-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir pip setuptools wheel
RUN pip install --no-cache-dir "nats-py>=2.1.0" "anyio>=3.6.0"

# Copy source code and examples
COPY docker-example.py ./

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "docker-example.py"]