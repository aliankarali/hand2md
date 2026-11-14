# hand2md

Offline handwriting → Markdown CLI for Apple Silicon Macs.

- **Engine:** Qwen3-VL-4B-Instruct (4-bit, MLX) via `mlx-vlm`
- **Fallback:** Apple Vision, used automatically if the model is missing or its output looks broken (repetition loop / token limit). A fallback is marked with an `<!-- hand2md: Apple Vision fallback … -->` comment in the output.
- **Offline:** Hugging Face libraries are forced into offline mode and an in-process guard blocks every non-loopback connection and DNS lookup. Only `scripts/download-model.sh` touches the network.
- **Images:** EXIF-rotated and downscaled (no upscaling) to `--max-side` px (default 1600) before processing. Supported: jpg, png, tiff, webp, bmp.

## Requirements

- Mac with Apple Silicon (M1 or later), macOS 13+
- Python 3.10+ (native arm64)
- ~3 GB disk space for the model, 16 GB RAM recommended

## Setup

```bash
git clone https://github.com/aliankarali/hand2md.git && cd hand2md
python3 -m venv .venv && .venv/bin/pip install -e .
scripts/download-model.sh        # one-time, ~3 GB → ~/Developer/models/Qwen3-VL-4B-Instruct-4bit
```

## Usage

```bash
.venv/bin/hand2md scan.jpg                    # Markdown to stdout
.venv/bin/hand2md *.jpg -o out/               # one .md per image
.venv/bin/hand2md scan.jpg -o scan.md         # single file
.venv/bin/hand2md --engine vision scan.jpg    # Apple Vision only
```

Progress and timing go to stderr (`-q` silences them). Exit code is 1 if any image failed.

Unreadable words are written as `[?]`; the model is instructed not to guess or correct spelling. Always review numbers, dates and amounts.

## Verify offline operation

```bash
sandbox-exec -p '(version 1)(allow default)(deny network-outbound (remote ip))' .venv/bin/hand2md samples/meeting-notes.png
```

## Performance (M1 Pro, 16 GB)

~4 s model load, ~12–16 s per page at 1600 px (≈2,150 image tokens), ~2.4 GB peak RSS. Lower `--max-side` for speed, raise it for small handwriting.

## Samples

`samples/` holds two synthetic test pages (fictional text set in macOS handwriting-style fonts), useful as a smoke test. Real handwriting is harder; measure accuracy on your own pages before relying on the output.

## License

MIT; see [LICENSE](LICENSE). The model is not part of this repository: [Qwen3-VL-4B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct) is released by the Qwen team under Apache 2.0, and the MLX conversion is downloaded from [mlx-community](https://huggingface.co/mlx-community/Qwen3-VL-4B-Instruct-4bit). Dependencies ([mlx-vlm](https://github.com/Blaizzy/mlx-vlm), [Pillow](https://github.com/python-pillow/Pillow), [PyObjC](https://github.com/ronaldoussoren/pyobjc)) are installed from PyPI under their own licenses.
