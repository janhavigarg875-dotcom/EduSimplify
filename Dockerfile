# ── EduSimplify Dockerfile ───────────────────────────────────────────────────
# Build:  docker build -t edusimplify .
# Run:    docker run -p 5000:5000 --env-file .env edusimplify

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies first (layer is cached unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source (excludes anything in .dockerignore)
COPY . .

# Expose the port Flask/Gunicorn will listen on
EXPOSE 5000

# Production server — gunicorn with 2 workers and 120s timeout for AI responses
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120"]
