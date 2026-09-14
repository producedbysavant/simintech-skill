"""Тесты каталога скиллов: структура, frontmatter, согласованность имён."""

import os
import pathlib
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest  # noqa: E402

CATALOG = pathlib.Path(__file__).resolve().parents[2] / "skills-catalog"


def _skill_dirs():
    if not CATALOG.is_dir():
        return []
    return sorted(p for p in CATALOG.iterdir() if p.is_dir())


def _read_frontmatter(path: pathlib.Path) -> dict:
    """Разобрать YAML-frontmatter между первыми `---` файла."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    result = {}
    for line in block.splitlines():
        if ":" in line and not line.startswith((" ", "\t", "#")):
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def test_catalog_dir_exists():
    assert CATALOG.is_dir(), f"нет каталога скиллов: {CATALOG}"


def test_catalog_readme_exists():
    assert (CATALOG / "README.md").is_file()


@pytest.mark.parametrize("skill", _skill_dirs(), ids=lambda p: p.name)
def test_skill_has_required_files(skill):
    """В каждом скилле есть SKILL.md и manifest.yaml."""
    assert (skill / "SKILL.md").is_file(), f"{skill.name}: нет SKILL.md"
    assert (skill / "manifest.yaml").is_file(), f"{skill.name}: нет manifest.yaml"


@pytest.mark.parametrize("skill", _skill_dirs(), ids=lambda p: p.name)
def test_skill_frontmatter_matches_dirname(skill):
    """`name` во frontmatter совпадает с именем каталога."""
    front = _read_frontmatter(skill / "SKILL.md")

    assert front.get("name") == skill.name
    assert front.get("description"), f"{skill.name}: пустое описание"


@pytest.mark.parametrize("skill", _skill_dirs(), ids=lambda p: p.name)
def test_manifest_name_matches_dirname(skill):
    """`name` в manifest.yaml совпадает с именем каталога."""
    yaml = pytest.importorskip("yaml")

    data = yaml.safe_load((skill / "manifest.yaml").read_text(encoding="utf-8"))

    assert data.get("name") == skill.name
    assert data.get("source_of_truth"), f"{skill.name}: не указан источник"


@pytest.mark.parametrize("skill", _skill_dirs(), ids=lambda p: p.name)
def test_skill_declares_verification_status(skill):
    """У каждого скилла явно указано, проверен ли он."""
    yaml = pytest.importorskip("yaml")

    data = yaml.safe_load((skill / "manifest.yaml").read_text(encoding="utf-8"))

    assert "verified" in data, f"{skill.name}: не указан статус проверки"


# ─── Ссылки на simintech-code ─────────────────────────────────────

# Пути, которые были верны в объединённом репозитории и стали ложными после
# разделения: контент и библиотека переехали в simintech-code.
STALE_PREFIXES = (
    "docs/simintech-language/",
    "scripts/generate_block_catalog.py",
    "sitECRT/",
)

CODE_URL = "https://github.com/producedbysavant/simintech-code"


def _all_skill_files():
    files = []
    for skill in _skill_dirs():
        files.extend(skill.glob("*.md"))
        files.extend(skill.glob("*.yaml"))
    return files


@pytest.mark.parametrize("path", _all_skill_files(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_no_stale_relative_paths(path):
    """Скиллы не ссылаются на пути старой раскладки репозитория.

    После разделения `docs/simintech-language/`, `simintech_api/` и
    `scripts/generate_block_catalog.py` живут в другом репозитории. Такие
    ссылки ломаются молча — поэтому проверяем явно.
    """
    text = path.read_text(encoding="utf-8")

    for prefix in STALE_PREFIXES:
        assert prefix not in text, f"{path.name}: устаревший путь {prefix!r}"


@pytest.mark.parametrize("path", _all_skill_files(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_references_point_to_simintech_code(path):
    """Упоминания контента ведут по URL к simintech-code, а не в пустоту."""
    text = path.read_text(encoding="utf-8")

    if "block_catalog.json" in text or "com_api_inventory" in text:
        assert CODE_URL in text, (
            f"{path.name}: ссылка на артефакты simintech-code без URL"
        )


def test_readme_has_no_stale_paths():
    """README каталога скиллов тоже не должен ссылаться на старую раскладку."""
    text = (CATALOG / "README.md").read_text(encoding="utf-8")

    for prefix in STALE_PREFIXES:
        assert prefix not in text, f"README.md: устаревший путь {prefix!r}"
