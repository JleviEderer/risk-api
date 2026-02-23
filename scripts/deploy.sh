#!/usr/bin/env bash
#
# Deploy risk-api to a fresh Ubuntu/Debian VPS.
# Usage: ssh user@your-vps 'bash -s' < scripts/deploy.sh
#   OR:  scp this to the VPS and run it there.
#
set -euo pipefail

REPO="https://github.com/JleviEderer/risk-api.git"
APP_DIR="$HOME/risk-api"

echo "=== Installing Docker (if needed) ==="
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
  echo "Docker installed. You may need to log out and back in for group changes."
  echo "Then re-run this script."
  exit 0
fi

echo "=== Cloning/updating repo ==="
if [ -d "$APP_DIR" ]; then
  cd "$APP_DIR"
  git pull
else
  git clone "$REPO" "$APP_DIR"
  cd "$APP_DIR"
fi

echo "=== Setting up .env ==="
if [ ! -f .env ]; then
  cp .env.production .env
  echo "Created .env from .env.production — review and edit if needed:"
  echo "  nano $APP_DIR/.env"
fi

echo "=== Building and starting ==="
docker compose up -d --build

echo ""
echo "=== Deployed! ==="
echo "Health check: curl http://localhost:8000/health"
echo "Analyze:      curl 'http://localhost:8000/analyze?address=0x...'"
echo ""
echo "Logs: docker compose logs -f"
echo "Stop: docker compose down"
