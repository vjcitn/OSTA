#!/usr/bin/env python3
"""Convert bare Quarto chapter QMD files (no YAML front matter) to .ipynb."""

import json
import re
import sys
import uuid
from pathlib import Path

KERNEL = {
    "display_name": "R",
    "language": "R",
    "name": "ir",
}

LANG_INFO = {
    "name": "R",
    "codemirror_mode": "r",
    "file_extension": ".r",
    "mimetype": "text/x-r-source",
    "pygments_lexer": "r",
}

CODE_FENCE = re.compile(r"^```\{r[^}]*\}\s*$", re.MULTILINE)
CLOSE_FENCE = re.compile(r"^```\s*$", re.MULTILINE)


def uid():
    return str(uuid.uuid4())[:8]


def make_md_cell(src: str) -> dict:
    return {
        "cell_type": "markdown",
        "id": uid(),
        "metadata": {},
        "source": src.strip("\n"),
    }


def make_code_cell(src: str) -> dict:
    return {
        "cell_type": "code",
        "id": uid(),
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": src.strip("\n"),
    }


def parse_qmd(text: str) -> list:
    cells = []
    pos = 0

    while pos < len(text):
        m = CODE_FENCE.search(text, pos)
        if m is None:
            # rest is markdown
            chunk = text[pos:]
            if chunk.strip():
                cells.append(make_md_cell(chunk))
            break

        # markdown before the code fence
        before = text[pos:m.start()]
        if before.strip():
            cells.append(make_md_cell(before))

        # find closing ```
        close = CLOSE_FENCE.search(text, m.end())
        if close is None:
            # unclosed fence — treat rest as markdown
            chunk = text[m.start():]
            if chunk.strip():
                cells.append(make_md_cell(chunk))
            break

        code = text[m.end():close.start()]
        if code.strip():
            cells.append(make_code_cell(code))

        pos = close.end()

    return cells


def convert(src: Path, dst: Path):
    text = src.read_text(encoding="utf-8")
    # strip Quarto shortcodes (e.g. {{< include _start.qmd >}})
    text = re.sub(r"\{\{<[^>]+>\}\}", "", text)

    cells = parse_qmd(text)

    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": KERNEL,
            "language_info": LANG_INFO,
        },
        "cells": cells,
    }

    dst.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  {src.name} -> {dst.name}  ({len(cells)} cells)")


def main():
    pages_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("inst/pages")
    out_dir   = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("inst/jupyter")
    out_dir.mkdir(parents=True, exist_ok=True)

    skip = {"_start.qmd", "_stop.qmd"}
    qmds = sorted(p for p in pages_dir.glob("*.qmd") if p.name not in skip)

    print(f"Converting {len(qmds)} QMD files -> {out_dir}/")
    for qmd in qmds:
        dst = out_dir / (qmd.stem + ".ipynb")
        convert(qmd, dst)


if __name__ == "__main__":
    main()
