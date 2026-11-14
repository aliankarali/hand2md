"""Primary engine: Qwen3-VL running locally through mlx-vlm."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

PROMPT = """Transcribe all handwritten and printed text in this image exactly as written.

Rules:
- Output Markdown only: no preamble, no explanations, no code fences.
- Keep the original language. Do not translate.
- Do not correct spelling, grammar or punctuation. Copy numbers, dates and amounts digit by digit.
- Keep the line breaks and paragraphs of the original.
- Use Markdown headings, lists, checkboxes (- [ ] / - [x]) and tables only where the page visibly has them.
- Write crossed-out text as ~~text~~.
- If a word or character cannot be read with confidence, write [?] in its place. Never guess.
- If the image contains no text, output nothing."""


class GenerationProblem(RuntimeError):
    """The model output looks unusable (repetition loop or hit the token limit)."""


@dataclass
class QwenResult:
    text: str
    prompt_tokens: int
    generation_tokens: int
    seconds: float


_FENCE = re.compile(r"^```[a-zA-Z]*\s*\n(.*?)\n```\s*$", re.DOTALL)


def _clean(text: str) -> str:
    text = text.strip()
    m = _FENCE.match(text)
    if m:
        text = m.group(1).strip()
    return text


def _looping(text: str) -> bool:
    lines = [ln.strip() for ln in text.splitlines() if len(ln.strip()) >= 6]
    if len(lines) >= 4 and len(set(lines[-4:])) == 1:
        return True
    if len(text) > 600:
        tail = text[-60:]
        if text[:-60].count(tail) >= 3:
            return True
    return False


class QwenEngine:
    def __init__(self, model_path: Path):
        if not (model_path / "config.json").is_file():
            raise FileNotFoundError(f"no model found at {model_path} (run scripts/download-model.sh)")
        from mlx_vlm import load
        from mlx_vlm.prompt_utils import apply_chat_template

        self.model, self.processor = load(str(model_path))
        self.prompt = apply_chat_template(self.processor, self.model.config, PROMPT, num_images=1)

    def _run(self, image: Image.Image, max_tokens: int, repetition_penalty: float | None) -> QwenResult:
        from mlx_vlm import stream_generate

        kwargs = {"max_tokens": max_tokens, "temperature": 0.0}
        if repetition_penalty:
            kwargs["repetition_penalty"] = repetition_penalty

        start = time.perf_counter()
        text, last, n = "", None, 0
        for chunk in stream_generate(self.model, self.processor, self.prompt, image=[image], **kwargs):
            text += chunk.text
            last = chunk
            n += 1
            if n % 32 == 0 and _looping(text):
                raise GenerationProblem("repetition loop detected")
        if _looping(text):
            raise GenerationProblem("repetition loop detected")
        if last is not None and last.finish_reason == "length":
            raise GenerationProblem(f"output hit the {max_tokens}-token limit")
        return QwenResult(
            text=_clean(text),
            prompt_tokens=getattr(last, "prompt_tokens", 0),
            generation_tokens=getattr(last, "generation_tokens", 0),
            seconds=time.perf_counter() - start,
        )

    def transcribe(self, image: Image.Image, max_tokens: int) -> QwenResult:
        try:
            return self._run(image, max_tokens, None)
        except GenerationProblem:
            # One retry with a mild repetition penalty before giving up.
            return self._run(image, max_tokens, 1.1)
