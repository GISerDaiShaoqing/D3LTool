# -*- coding: utf-8 -*-
"""Regenerate docs/copyright/source_code_document.txt for the current source.

50 lines per page, front 30 + back 30 pages — the CPCC submission format.
Run:  python tools_gen_source_doc.py
"""

from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs" / "copyright" / "source_code_document.txt"

FILES = []
for pattern in ("d3ltool/*.py", "d3ltool/agent/*.py", "d3ltool/gui/*.py",
                "D3LToolNASA.py", "D3LToolMCP.py"):
    FILES.extend(sorted(ROOT.glob(pattern)))

LINES_PER_PAGE = 50
FRONT_PAGES = 30
BACK_PAGES = 30

banner = [
    "====================================================================================================",
    "D3L Tool of NASA Satellite V2.1.0  软件著作权登记  源程序文档",
    "开发语言: Python 3.10+    生成日期: %s    代码总行数: %d" % (
        date.today().isoformat(),
        sum(len(p.read_text(encoding="utf-8").splitlines()) for p in FILES),
    ),
    "====================================================================================================",
]

pages = []          # list of page strings
current = []        # lines in current page


def new_page():
    if current:
        pages.append(current[:])


def push(line):
    current.append(line)
    if len(current) >= LINES_PER_PAGE:
        new_page()
        current.clear()


for path in FILES:
    rel = path.relative_to(ROOT).as_posix()
    push("# ===== 文件: %s =====" % rel)
    for line in path.read_text(encoding="utf-8").splitlines():
        push(line.rstrip())

new_page()

total_pages = len(pages)
if total_pages <= FRONT_PAGES + BACK_PAGES:
    chosen = list(range(total_pages))
else:
    chosen = list(range(FRONT_PAGES)) + list(range(total_pages - BACK_PAGES, total_pages))

with OUT.open("w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(banner) + "\n\n")
    for pno in chosen:
        head = ("D3L Tool of NASA Satellite V2.1.0    源程序（前30页+后30页节选）"
                "    第 %d 页 / 共 %d 页" % (pno + 1, total_pages))
        fh.write(head + "\n")
        fh.write("=" * 100 + "\n")
        fh.write("\n".join(pages[pno]) + "\n\n")

print("files:", len(FILES), "total pages:", total_pages, "->", OUT)
