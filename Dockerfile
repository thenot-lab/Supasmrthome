FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY neuro_arousal/ neuro_arousal/
COPY main.py .

# Default: personal mode, no auth required
ENV NEUROAROUSAL_AUTH_REQUIRED=false
ENV NEUROAROUSAL_USERS_FILE=/app/data/users.json

EXPOSE 7860

# Create data directory for user store
RUN mkdir -p /app/data

CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "7860"]
