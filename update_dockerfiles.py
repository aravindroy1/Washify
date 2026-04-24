import os

services = ["auth_service", "booking_service", "car_wash_service", "notification_service", "review_service"]

dockerfile_content = """# Stage 1: Build Environment
FROM python:3.9-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Minimal Runtime Environment
FROM python:3.9-slim
# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source code
COPY . .

# Secure permissions
RUN chown -R appuser:appuser /app

# Switch to non-privileged user
USER appuser

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

dockerignore_content = """__pycache__/
*.py[cod]
*$py.class
.env
.venv
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
Dockerfile
.git
.gitignore
"""

for service in services:
    with open(f"{service}/Dockerfile", "w") as f:
        f.write(dockerfile_content)
    with open(f"{service}/.dockerignore", "w") as f:
        f.write(dockerignore_content)

# Update Frontend Dockerfile
frontend_dockerfile = """# Use unprivileged Nginx image for security out of the box
FROM nginxinc/nginx-unprivileged:alpine

COPY . /usr/share/nginx/html

# Expose port 8080 (unprivileged port)
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
"""
with open("frontend_service/Dockerfile", "w") as f:
    f.write(frontend_dockerfile)

with open("frontend_service/.dockerignore", "w") as f:
    f.write(dockerignore_content)
