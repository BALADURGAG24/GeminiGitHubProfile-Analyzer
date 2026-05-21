FROM python:3.12-slim

# Install uv
RUN pip install uv

WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Copy application source
COPY . .

# Create static directory
RUN mkdir -p static/cards

# Expose port
EXPOSE 8080

# Start server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
