#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " Starting Drishti — MPLADS Risk Intelligence Platform"
echo "=========================================================="

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    echo "[✓] Docker Compose detected."
    echo "[*] Launching services at http://localhost:5317 ..."
    docker compose up --build "$@"
elif command -v docker-compose >/dev/null 2>&1; then
    echo "[✓] Legacy docker-compose detected."
    echo "[*] Launching services at http://localhost:5317 ..."
    docker-compose up --build "$@"
else
    echo "[!] Docker is not installed or not found in PATH."
    echo "    Please install Docker Desktop or Docker Engine:"
    echo "    https://docs.docker.com/get-docker/"
    exit 1
fi
