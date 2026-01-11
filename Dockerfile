# Stage 1: Build the React frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
ARG VITE_FIREBASE_API_KEY
ARG VITE_FIREBASE_AUTH_DOMAIN
ARG VITE_FIREBASE_PROJECT_ID
ARG VITE_FIREBASE_STORAGE_BUCKET
ARG VITE_FIREBASE_MESSAGING_SENDER_ID
ARG VITE_FIREBASE_APP_ID

ENV VITE_FIREBASE_API_KEY=$VITE_FIREBASE_API_KEY
ENV VITE_FIREBASE_AUTH_DOMAIN=$VITE_FIREBASE_AUTH_DOMAIN
ENV VITE_FIREBASE_PROJECT_ID=$VITE_FIREBASE_PROJECT_ID
ENV VITE_FIREBASE_STORAGE_BUCKET=$VITE_FIREBASE_STORAGE_BUCKET
ENV VITE_FIREBASE_MESSAGING_SENDER_ID=$VITE_FIREBASE_MESSAGING_SENDER_ID
ENV VITE_FIREBASE_APP_ID=$VITE_FIREBASE_APP_ID

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

# Copy the rest of the application code
COPY . .

# Copy the built frontend from Stage 1 (ensure it overwrites any local dist if present)
COPY --from=frontend-builder /app/dist ./dist

# Ensure the static directory exists for generated files
RUN mkdir -p static/audio static/videos static/slides static/docs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose the port (Cloud Run uses 8080 by default)
EXPOSE 8080

# Run the application
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
