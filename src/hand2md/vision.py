"""Fallback engine: Apple Vision text recognition (on-device, via PyObjC)."""

from __future__ import annotations

import io
from statistics import median

from PIL import Image

DEFAULT_LANGUAGES = ("de-DE", "en-US")


def transcribe(image: Image.Image, languages=DEFAULT_LANGUAGES) -> str:
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

    items = []
    for obs in request.results() or []:
        candidates = obs.topCandidates_(1)
        if not candidates:
            continue
        box = obs.boundingBox()  # normalised, origin bottom-left
        top = box.origin.y + box.size.height
        items.append((top, box.origin.x, box.size.height, str(candidates[0].string())))
    if not items:
        return ""

    # Group observations into visual rows (top to bottom, then left to right).
    items.sort(key=lambda t: (-t[0], t[1]))
    rows: list[list[tuple]] = []
    for it in items:
        if rows and abs(rows[-1][0][0] - it[0]) < 0.5 * it[2]:
            rows[-1].append(it)
        else:
            rows.append([it])

    line_h = median(it[2] for it in items)
    out: list[str] = []
    prev_top = None
    for row in rows:
        row.sort(key=lambda t: t[1])
        top = row[0][0]
        if prev_top is not None and (prev_top - top) > 2.2 * line_h:
            out.append("")  # paragraph break on a large vertical gap
        out.append(" ".join(t[3] for t in row))
        prev_top = top
    return "\n".join(out).strip()
