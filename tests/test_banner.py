# -*- coding: utf-8 -*-
"""Startup banner: static fallback off-TTY, CLI subcommand wiring."""

from d3ltool import __version__, banner


def test_banner_static_when_not_a_tty(capsys):
    """非 TTY（MCP stdio / 管道 / CI）退化为静态版——块状艺术字 + 版本行，
    无 ANSI 色码（机器可读流不受污染）。"""
    banner.show_banner(animate=True)          # capsys 非 tty → 静态
    out = capsys.readouterr().out
    assert out.count("\n") == 6               # 5 行艺术字 + 1 行版本
    assert "█" in out and f"D3LTool v{__version__}" in out
    assert "MODIS / VIIRS / MERRA-2 / GLASS" in out
    assert "\x1b" not in out                  # 非 TTY 无 ANSI


def test_cli_banner_subcommand(capsys):
    from d3ltool import cli

    assert cli.main(["banner"]) == 0
    out = capsys.readouterr().out
    assert "█" in out and f"D3LTool v{__version__}" in out
