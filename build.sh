#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
pip install -r backend/requirements.txt

# Build Frontend
cd frontend
npm install
npm run build
cd ..

# Create static directory in backend if it doesn't exist
mkdir -p backend/static

# Move build artifacts to backend static directory
# Vite builds to 'dist', we want to serve this
# We'll copy the contents of dist to backend/static
cp -r frontend/dist/* backend/static/
