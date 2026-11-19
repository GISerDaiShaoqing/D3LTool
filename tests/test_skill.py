# -*- coding: utf-8 -*-
"""Bundled agent skill: package source, installer idempotency, CLI wiring."""

from pathlib import Path

import pytest

from d3ltool import skill


def test_skill_source_ships_complete():
    """单一事实源随包分发：SKILL.md + README + LICENSE + 两份 references。"""
    src = skill.skill_source()
    assert src.name == "d3ltool"
    for name in ("SKILL.md", "README.md", "LICENSE"):
        assert (src / name).is_file()
    for ref in ("products.md", "troubleshooting.md"):
        assert (src / "references" / ref).is_file()
    text = (src / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---") and "name: d3ltool" in text   # 合法 skill 头


def test_install_is_idempotent(tmp_path):
    """安装 = 复制到 agent 发现目录；重复执行即更新（作者同步路径）。"""
    dest = tmp_path / ".agents" / "skills" / "d3ltool"
    target = skill.install(dest)
    assert target == dest
    assert (target / "SKILL.md").is_file()
    assert (target / "references" / "products.md").is_file()
    first = {p.name: p.stat().st_mtime for p in target.rglob("*") if p.is_file()}
    skill.install(dest)                        # 再装一次 → 原地刷新
    again = {p.name: p.stat().st_mtime for p in target.rglob("*") if p.is_file()}
    assert set(first) == set(again)
    assert skill.installed_files(target) == sorted(again)


def test_cli_skill_install(tmp_path, capsys):
    """`d3ltool skill install --dest`：写目标目录、打印路径与文件数。"""
    from d3ltool import cli

    dest = tmp_path / "skills"
    rc = cli.main(["skill", "install", "--dest", str(dest)])
    assert rc == 0
    assert (dest / "SKILL.md").is_file()
    out = capsys.readouterr().out
    assert "skill installed" in out and str(dest) in out


def test_gui_menu_installs_skill(tmp_path, monkeypatch):
    """帮助菜单「安装 AI Skill」：默认装到用户级目录（monkeypatch 隔离）。"""
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    import d3ltool.config as config

    from PySide6.QtWidgets import QApplication

    from d3ltool.gui.main_window import MainWindow

    monkeypatch.setattr(skill, "user_dest", lambda: tmp_path / "u" / "skills")
    cfg = dict(config.DEFAULTS)
    cfg["download_dir"] = str(tmp_path / "downloads")
    monkeypatch.setattr(config, "load_config", lambda: cfg)
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "config.json")

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        window._install_skill()
        assert (tmp_path / "u" / "skills" / "SKILL.md").is_file()
        assert "AI Skill" in window.statusBar().currentMessage()
    finally:
        window.close()
