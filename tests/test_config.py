# -*- coding: utf-8 -*-
"""Config load/save roundtrip (uses a temp HOME)."""

import d3ltool.config as config


def test_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path / ".d3ltool")
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / ".d3ltool" / "config.json")

    cfg = config.load_config()
    assert cfg["language"] == "zh"
    assert cfg["max_workers"] == 3

    cfg = config.update_config(language="en", max_workers=5, bogus_key=1)
    assert cfg["language"] == "en"
    assert "bogus_key" not in cfg

    reloaded = config.load_config()
    assert reloaded["language"] == "en"
    assert reloaded["max_workers"] == 5
    assert reloaded["proxy_url"] == ""


def test_ai_chat_bg_persists(tmp_path, monkeypatch):
    """New-in-2.2 chat background key round-trips through the DEFAULTS filter."""
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path / ".d3ltool")
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / ".d3ltool" / "config.json")

    cfg = config.update_config(ai_chat_bg=str(tmp_path / "bg.png"))
    assert cfg["ai_chat_bg"] == str(tmp_path / "bg.png")
    assert config.load_config()["ai_chat_bg"] == str(tmp_path / "bg.png")


def test_corrupt_file_falls_back_to_defaults(tmp_path, monkeypatch):
    cfg_dir = tmp_path / ".d3ltool"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "config.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(config, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(config, "CONFIG_FILE", cfg_dir / "config.json")

    cfg = config.load_config()
    assert cfg == dict(config.DEFAULTS)
