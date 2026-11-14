"""hand2md – offline handwriting-to-Markdown CLI (Qwen3-VL via MLX, Apple Vision fallback)."""

import os

# Force every Hugging Face / transformers code path into offline mode before any
# of those libraries are imported. The model is loaded from a local folder only.
for _var in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY"):
    os.environ[_var] = "1"
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

__version__ = "0.2.0"
