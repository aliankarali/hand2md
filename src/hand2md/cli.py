"""hand2md command-line entry point."""

from __future__ import annotations

import argparse
import os
import sys
import time
import warnings
from pathlib import Path

from . import __version__, netguard

DEFAULT_MODEL = Path.home() / "Developer" / "models" / "Qwen3-VL-4B-Instruct-4bit"


def _log(msg: str, quiet: bool) -> None:
    if not quiet:
        print(msg, file=sys.stderr, flush=True)


def _parse(argv) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="hand2md",
        description="Transcribe handwritten text in images to Markdown, fully offline.",
    )
    p.add_argument("images", nargs="+", type=Path, help="image files (jpg, png, tiff, webp, bmp)")
    p.add_argument("-o", "--output", type=Path,
                   help="output directory (one .md per image), or a .md file for a single image; default: stdout")
    p.add_argument("--engine", choices=("auto", "qwen", "vision"), default="auto",
                   help="auto = Qwen3-VL, falling back to Apple Vision on failure (default: auto)")
    p.add_argument("--model", type=Path, default=Path(os.environ.get("HAND2MD_MODEL", DEFAULT_MODEL)),
                   help=f"local model folder (default: $HAND2MD_MODEL or {DEFAULT_MODEL})")
    p.add_argument("--max-side", type=int, default=1600,
                   help="downscale so the longest side is at most this many pixels (default: 1600)")
    p.add_argument("--max-tokens", type=int, default=2048, help="token limit per image (default: 2048)")
    p.add_argument("-q", "--quiet", action="store_true", help="no progress output on stderr")
    p.add_argument("--version", action="version", version=f"hand2md {__version__}")
    return p.parse_args(argv)


def _output_target(args, n_inputs: int):
    """Return (mode, path): mode is 'stdout', 'file' or 'dir'."""
    if args.output is None:
        return "stdout", None
    if args.output.suffix.lower() == ".md":
        if n_inputs != 1:
            sys.exit("hand2md: -o FILE.md only works with a single image; pass a directory for several images")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        return "file", args.output
    args.output.mkdir(parents=True, exist_ok=True)
    return "dir", args.output


def main(argv=None) -> int:
    netguard.install()
    warnings.filterwarnings("ignore")
    args = _parse(argv)

    from .imageprep import SUPPORTED_SUFFIXES, load_and_resize

    for img in args.images:
        if not img.is_file():
            sys.exit(f"hand2md: file not found: {img}")
        if img.suffix.lower() not in SUPPORTED_SUFFIXES:
            sys.exit(f"hand2md: unsupported format {img.suffix!r} ({img}); use jpg, png, tiff, webp or bmp")

    mode, out_path = _output_target(args, len(args.images))

    qwen = None
    qwen_unavailable = None
    if args.engine in ("auto", "qwen"):
        _log(f"loading model from {args.model} …", args.quiet)
        t0 = time.perf_counter()
        try:
            from .qwen import QwenEngine
            qwen = QwenEngine(args.model)
            _log(f"model ready ({time.perf_counter() - t0:.1f}s)", args.quiet)
        except Exception as e:  # noqa: BLE001
            if args.engine == "qwen":
                sys.exit(f"hand2md: could not load model: {e}")
            qwen_unavailable = f"model unavailable: {e}"
            _log(f"warning: {qwen_unavailable} – using Apple Vision", args.quiet)

    failures = 0
    total = len(args.images)
    for i, img_path in enumerate(args.images, 1):
        label = f"[{i}/{total}] {img_path.name}"
        try:
            image = load_and_resize(img_path, args.max_side)
            fallback_reason = qwen_unavailable
            info = ""
            if qwen is not None:
                try:
                    res = qwen.transcribe(image, args.max_tokens)
                    markdown, engine = res.text, "qwen"
                    info = f"{res.prompt_tokens}+{res.generation_tokens} tok, {res.seconds:.1f}s"
                except Exception as e:  # noqa: BLE001
                    if args.engine == "qwen":
                        raise
                    fallback_reason = f"Qwen failed: {e}"
                    _log(f"{label}: warning: {fallback_reason} – falling back to Apple Vision", args.quiet)
            if qwen is None or fallback_reason:
                from . import vision
                t0 = time.perf_counter()
                markdown, engine = vision.transcribe(image), "vision"
                info = f"{time.perf_counter() - t0:.1f}s"
                if fallback_reason:
                    markdown = f"<!-- hand2md: Apple Vision fallback ({fallback_reason}) -->\n\n{markdown}"
        except Exception as e:  # noqa: BLE001
            failures += 1
            _log(f"{label}: error: {e}", False)
            continue

        markdown = markdown.rstrip() + "\n"
        if mode == "stdout":
            if total > 1:
                sys.stdout.write(f"{'' if i == 1 else chr(10)}<!-- file: {img_path.name} -->\n\n")
            sys.stdout.write(markdown)
            sys.stdout.flush()
            dest = "stdout"
        else:
            dest_path = out_path if mode == "file" else out_path / f"{img_path.stem}.md"
            dest_path.write_text(markdown, encoding="utf-8")
            dest = str(dest_path)
        _log(f"{label} → {dest} ({engine}, {image.width}x{image.height}px, {info})", args.quiet)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
