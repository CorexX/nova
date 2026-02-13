"""
Tests fuer tools/paths.py (Standalone + Embedded Layouts).
"""

from pathlib import Path

from tools.paths import load_config


class TestLoadConfigDefaults:
    """Default-Resolution ohne ENV/TOML."""

    def test_standalone_defaults_use_workspace_as_core_root(self, tmp_path: Path):
        (tmp_path / "mcp").mkdir()
        (tmp_path / "core").mkdir()

        cfg = load_config(tmp_path)

        assert cfg.core_root == tmp_path
        assert cfg.knowledge_root == tmp_path / "nova-knowledge"

    def test_embedded_defaults_use_workspace_nova_core(self, tmp_path: Path):
        (tmp_path / "nova-core" / "mcp").mkdir(parents=True)

        cfg = load_config(tmp_path)

        assert cfg.core_root == tmp_path / "nova-core"
        assert cfg.knowledge_root == tmp_path / "nova-knowledge"


class TestConfigFileResolution:
    """Konfigurations-Datei wird layout-robust gefunden."""

    def test_prefers_parent_nova_toml_when_present(self, tmp_path: Path):
        core_root = tmp_path / "nova-core"
        core_root.mkdir()
        parent_cfg = tmp_path / "nova.toml"
        parent_cfg.write_text("", encoding="utf-8")

        (tmp_path / "nova-core" / "mcp").mkdir(parents=True)

        cfg = load_config(tmp_path)
        assert cfg.config_file == parent_cfg

    def test_uses_core_local_nova_toml_when_parent_missing(self, tmp_path: Path):
        (tmp_path / "mcp").mkdir()
        (tmp_path / "core").mkdir()
        local_cfg = tmp_path / "nova.toml"
        local_cfg.write_text("", encoding="utf-8")

        cfg = load_config(tmp_path)
        assert cfg.config_file == local_cfg
