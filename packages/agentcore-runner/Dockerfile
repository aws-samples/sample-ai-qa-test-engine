FROM public.ecr.aws/docker/library/python:3.13-slim

WORKDIR /var/task

# Install system deps for Playwright browsers
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    bedrock-agentcore>=1.0.3 \
    boto3 \
    nova-act \
    ai-qa-test-engine \
    pydantic>=2.0 \
    pydantic-settings>=2.0 \
    python-dotenv>=1.0.0 \
    gherkin-official>=28.0.0 \
    openpyxl>=3.1.0 \
    aws-opentelemetry-distro

# Copy application code
COPY main.py .
COPY scenario_executor.py .
COPY s3_utils.py .

# Expose port for AgentCore runtime
EXPOSE 8080

# AgentCore entrypoint
CMD ["python", "main.py"]
