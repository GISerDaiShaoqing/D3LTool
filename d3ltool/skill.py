# -*- coding: utf-8 -*-
"""Bundled agent skill (SKILL.md + references) and its installer.

The skill teaches MCP-capable AI clients (ZCode / Claude / Cursor…) to
orchestrate d3ltool's MCP tools the right way — routing, auth boundaries,
politeness policy, CLI fallbacks.  Single source of truth lives in the
package at ``d3ltool/resources/skill/d3ltool/`` (shipped with pip wheels
and the PyInstaller bundles); :func:`install` copies it into an agent's
skill discovery directory (``~/.agents/skills/d3ltool`` by default).
Re-running install over an existing copy is the intended update path —
also how the author syncs an edited working-tree skill back into an
installed location."""

import shutil
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "resources" / "skill" / "d3ltool"


SKILL_REPO_URL = "https://github.com/GISerDaiShaoqing/d3ltool-skill"


def skill_source() -> Path:
    """Directory holding the bundled skill. The D3LTool repo carries no copy:
    release builds clone the d3ltool-skill repo into resources/skill (see
    .github/workflows/build.yml), wheels/installers ship it from there."""
    if not (_SRC / "SKILL.md").is_file():
        raise FileNotFoundError(
            f"bundled skill not found at {_SRC} — release builds fetch it "
            f"from {SKILL_REPO_URL}; or clone it there manually")
    return _SRC


def user_dest() -> Path:
    return Path.home() / ".agents" / "skills" / "d3ltool"


def project_dest() -> Path:
    return Path.cwd() / ".agents" / "skills" / "d3ltool"


def install(dest: Path | None = None) -> Path:
    """Copy the bundled skill into ``dest`` (default: the user-level agent
    skill directory).  Idempotent — re-running refreshes/updates in place.
    ``.git`` is never copied: working-tree copies of the skill carry their
    own publishing repo, and git object files are read-only (a second
    install would hit Permission denied)."""
    target = Path(dest) if dest else user_dest()
    shutil.copytree(skill_source(), target, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(".git"))
    return target


def installed_files(target: Path) -> list:
    return sorted(p.name for p in Path(target).rglob("*") if p.is_file())
