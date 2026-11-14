"""Fallback engine: Apple Vision text recognition (on-device, via PyObjC)."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from statistics import median

from PIL import Image

from .reflow import LIST_ITEM

DEFAULT_LANGUAGES = ("de-DE", "en-US")


@dataclass
class _Row:
    top: float  # px from the top of the image
    left: float  # px from the left edge
    parts: list = field(default_factory=list)  # (left, text)

    @property
    def text(self) -> str:
        return " ".join(t for _, t in sorted(self.parts))


def transcribe(image: Image.Image, languages=DEFAULT_LANGUAGES) -> str:
    """Return one line per visual row, with a blank line before each paragraph.

    A paragraph starts after a vertical gap clearly larger than the normal line
    pitch, or at a row indented relative to the row above (list items excepted).
    """
    import Vision
    from Foundation import NSData

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    raw = buf.getvalue()
    data = NSData.dataWithBytes_length_(raw, len(raw))

    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setUsesLanguageCorrection_(True)
    request.setRecognitionLanguages_(list(languages))

    handler = Vision.VNImageRequestHandler.alloc().initWithData_options_(data, None)
    ok, err = handler.performRequests_error_([request], None)
    if not ok:
        raise RuntimeError(f"Apple Vision failed: {err}")

    W, H = image.size
    items = []  # (top px, left px, height px, text)
    for obs in request.results() or []:
        candidates = obs.topCandidates_(1)
        if not candidates:
            continue
        box = obs.boundingBox()  # normalised, origin bottom-left
        top = (1.0 - box.origin.y - box.size.height) * H
        items.append((top, box.origin.x * W, box.size.height * H, str(candidates[0].string())))
    if not items:
        return ""

    # Group observations into visual rows (top to bottom, then left to right).
    items.sort(key=lambda t: (t[0], t[1]))
    rows: list[_Row] = []
    for top, left, height, text in items:
        if rows and abs(rows[-1].top - top) < 0.5 * height:
            row = rows[-1]
            row.left = min(row.left, left)
        else:
            row = _Row(top=top, left=left)
            rows.append(row)
        row.parts.append((left, text))

    line_h = median(t[2] for t in items)
    pitches = [b.top - a.top for a, b in zip(rows, rows[1:])]
    # Normal line pitch = lower quartile of row distances, so pages where many
    # rows are separated by blank lines don't inflate it.
    pitch = min(sorted(pitches)[len(pitches) // 4], 1.8 * line_h) if pitches else line_h
    margin = median(r.left for r in rows)

    out: list[str] = []
    for i, row in enumerate(rows):
        text = row.text
        if i:
            prev = rows[i - 1]
            gap = row.top - prev.top > 1.6 * pitch
            # Compare with the row above (robust against a tilted page) and
            # with the page margin (so a line after an outdented one doesn't count).
            indent = (
                row.left - prev.left > 0.75 * line_h
                and row.left - margin > 0.5 * line_h
                and not LIST_ITEM.match(text)
                and not LIST_ITEM.match(prev.text)
            )
            if gap or indent:
                out.append("")
        out.append(text)
    return "\n".join(out).strip()
