#!/usr/bin/env bash
# One-time model download. This is the ONLY part of hand2md that uses the network;
# the hand2md CLI itself runs fully offline and blocks outbound connections.
set -euo pipefail

REPO="mlx-community/Qwen3-VL-4B-Instruct-4bit"
MODEL_DIR="${HAND2MD_MODEL:-$HOME/Developer/models/Qwen3-VL-4B-Instruct-4bit}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"

mkdir -p "$MODEL_DIR"
"$HERE/.venv/bin/hf" download "$REPO" --local-dir "$MODEL_DIR"
echo "Model ready at $MODEL_DIR"
