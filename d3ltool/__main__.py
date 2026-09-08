# -*- coding: utf-8 -*-
"""`python -m d3ltool` -> CLI (no args -> GUI)."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
