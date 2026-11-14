"""Join transcribed lines into paragraphs (the default output layout).

The engines keep one output line per line on the page and mark paragraph
breaks with a blank line. This pass joins the lines of each paragraph, so the
model never has to rewrite text itself. Headings, tables, comments and code
stay line by line; a list item absorbs its own wrapped continuation lines.
"""

from __future__ import annotations

import re

LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")

_STANDALONE = re.compile(
    r"""^\s*(?:
        \#{1,6}\s          # heading
      | \|                 # table row
      | >                  # blockquote
      | <!--               # HTML comment (e.g. the fallback marker)
      | (?:[-*_]\s*){3,}$  # horizontal rule
    )""",
    re.VERBOSE,
)
_FENCE = ("```", "~~~")

# "Kar-" + "toffeln": a hyphen directly after a letter at the end of a line.
_HYPHEN_END = re.compile(r"[^\W\d_]-$")
# German/English suspended hyphens keep their hyphen and a space: "Kunden- und Vertragsdaten".
_SUSPENDED_HYPHEN_NEXT = {"und", "oder", "bzw.", "sowie", "bis", "and", "or"}


def _join(prev: str, nxt: str) -> str:
    if _HYPHEN_END.search(prev):
        first_word = nxt.split(maxsplit=1)[0]
        if first_word in _SUSPENDED_HYPHEN_NEXT:
            return f"{prev} {nxt}"
        if first_word[:1].islower():
            return prev[:-1] + nxt  # line-break hyphenation: drop the hyphen
        return prev + nxt  # compound such as "E-" + "Mail"
    return f"{prev} {nxt}"


def reflow(text: str) -> str:
    out: list[str] = []
    current: str | None = None  # paragraph or list item being built
    in_fence = False

    def flush() -> None:
        nonlocal current
        if current is not None:
            out.append(current)
            current = None

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith(_FENCE):
            flush()
            out.append(line)
            in_fence = not in_fence
            continue
        if in_fence:
            out.append(line)
            continue
        if not stripped:
            flush()
            out.append("")
            continue
        if _STANDALONE.match(line):
            flush()
            out.append(line)
            continue
        if LIST_ITEM.match(line):
            flush()
            current = line
            continue
        # Plain text: continue the current paragraph or list item. Leading
        # indentation is dropped, since 4 spaces would turn it into a code block.
        current = stripped if current is None else _join(current, stripped)
    flush()

    # Collapse runs of blank lines and trim the ends.
    result: list[str] = []
    for line in out:
        if line == "" and (not result or result[-1] == ""):
            continue
        result.append(line)
    return "\n".join(result).strip()
