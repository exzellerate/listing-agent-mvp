#!/usr/bin/env bash
set -e

echo "==> Installing frontend dependencies..."
cd frontend && npm install

echo "==> Building frontend..."
npm run build
cd ..

echo "==> Copying frontend build to backend/static..."
rm -rf backend/static
cp -r frontend/dist backend/static

echo "==> Installing backend dependencies..."
cd backend && pip install -r requirements.txt

echo "==> Build complete!"
