# Stage 1: Build the React frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Setup the Python backend
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
# ffmpeg is required for moviepy (video generation)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the built frontend from Stage 1
COPY --from=frontend-builder /app/dist ./dist

# Copy the rest of the application code
COPY . .

# Ensure the static directory exists for generated files
RUN mkdir -p static/audio static/videos static/slides

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose the port (Cloud Run uses 8080 by default)
EXPOSE 8080

# Run the application
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
