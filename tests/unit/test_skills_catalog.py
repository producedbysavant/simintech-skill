"""Тесты каталога скиллов: структура, frontmatter, манифесты, ссылки.

`yaml` импортируется на уровне модуля намеренно: он объявлен в extras `test`,
а `pytest.importorskip("yaml")` превращал проверки манифестов в молчаливые
скипы — то есть в чистом окружении они проходили вхолостую.
"""

import os
import pathlib
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest  # noqa: E402
import yaml  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
CATALOG = ROOT / "skills-catalog"


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
    data = yaml.safe_load((skill / "manifest.yaml").read_text(encoding="utf-8"))

    assert data.get("name") == skill.name
    assert data.get("source_of_truth"), f"{skill.name}: не указан источник"


@pytest.mark.parametrize("skill", _skill_dirs(), ids=lambda p: p.name)
def test_skill_declares_verification_status(skill):
    """У каждого скилла явно указано, проверен ли он."""
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

# Ссылка вида `.../simintech-code/blob/main/<путь>`. Двоеточие и `#` в наборе
# не исключаются намеренно: якорь `файл.py:СИМВОЛ` надо поймать, а не срезать.
CODE_REF_RE = re.compile(
    r"simintech-code/(?:blob|tree)/main/([^\s`)\"'\]}]+)"
)

# Артефакты, которые после разделения живут только в simintech-code: рядом с
# их упоминанием обязан стоять URL, а не относительный путь.
CODE_ARTIFACTS = (
    "block_catalog.json",
    "com_api_inventory",
    "REPORT.md",
    "simintech_api/",
    "examples/",
)

# Ключи манифеста, значения которых обязаны быть URL.
URL_KEYS = ("source_of_truth", "data", "scripts")

README_PATHS = (ROOT / "README.md", CATALOG / "README.md")


def _all_skill_files():
    files = []
    for skill in _skill_dirs():
        files.extend(skill.glob("*.md"))
        files.extend(skill.glob("*.yaml"))
    return files


def _referenced_code_paths(text: str):
    """Пути внутри simintech-code, на которые ссылаются файлы скиллов."""
    paths = []
    for raw in CODE_REF_RE.findall(text):
        path = raw.split("#")[0].split(":")[0].rstrip(".,;").rstrip("/")
        if path:
            paths.append(path)
    return paths


def _find_code_dir():
    """Каталог checkout'а simintech-code, если он есть рядом с этим репозиторием."""
    env = os.environ.get("SIMINTECH_CODE_DIR")
    candidates = [pathlib.Path(env)] if env else []
    for parent in ROOT.parents:
        candidates.append(parent / "simintech-code")
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


CODE_DIR = _find_code_dir()


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
    """Упоминания артефактов simintech-code идут по URL, а не относительным путём."""
    text = path.read_text(encoding="utf-8")

    for artifact in CODE_ARTIFACTS:
        if artifact not in text:
            continue
        assert CODE_URL in text, (
            f"{path.name}: упомянут {artifact!r}, но ссылки на simintech-code нет"
        )


@pytest.mark.parametrize("path", _all_skill_files(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_no_symbol_anchor_in_github_urls(path):
    """Ссылки не используют якорь `файл.py:СИМВОЛ` — GitHub его не понимает.

    Такой URL отдаёт 404 (проверено на `constants.py:UNSUPPORTED_COM_BLOCK_CLASSES`):
    GitHub поддерживает только `#L<строка>`. Ошибка молчаливая — ссылка
    выглядит правдоподобно, но не открывается.
    """
    text = path.read_text(encoding="utf-8")

    for raw in re.findall(r"simintech-code/(?:blob|tree)/main/([^\s`)\"'\]}]+)", text):
        assert ":" not in raw, (
            f"{path.name}: якорь на символ в ссылке {raw!r} не поддерживается GitHub"
        )


@pytest.mark.parametrize("path", _all_skill_files(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_code_urls_use_blob_or_tree(path):
    """Ссылка на simintech-code указывает файл через `blob/` или `tree/`.

    Ссылка вида `.../simintech-code/REPORT.md` (без `blob/main/`) тоже 404:
    GitHub не показывает файл по такому адресу.
    """
    text = path.read_text(encoding="utf-8")

    for raw in re.findall(r"simintech-code/([^\s`)\"'\]}]*)", text):
        ref = raw.rstrip(".,;")
        if not ref:
            continue
        assert ref.startswith(("blob/", "tree/")), (
            f"{path.name}: ссылка на simintech-code/{ref!r} без blob/ или tree/ — 404"
        )


@pytest.mark.parametrize("path", _all_skill_files(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_manifest_sources_are_urls(path):
    """`source_of_truth` и `requires.{data,scripts}` содержат URL, а не пути.

    Относительный путь (`REPORT.md`, `examples/model2_pid.py`) после разделения
    указывает в пустоту: этих файлов в репозитории скиллов нет.
    """
    if path.name != "manifest.yaml":
        return

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = list(data.get("source_of_truth") or [])
    requires = data.get("requires") or {}
    for key in URL_KEYS:
        if key == "source_of_truth":
            continue
        value = requires.get(key)
        if isinstance(value, list):
            entries.extend(value)

    assert entries, f"{path.parent.name}: не указаны источники"
    for value in entries:
        assert isinstance(value, str) and "://" in value, (
            f"{path.parent.name}/manifest.yaml: {value!r} — не URL; после "
            f"разделения относительный путь ведёт в пустоту"
        )


@pytest.mark.parametrize("readme", README_PATHS, ids=lambda p: p.name)
def test_readme_has_no_stale_paths(readme):
    """README не должен ссылаться на старую раскладку репозитория."""
    text = readme.read_text(encoding="utf-8")

    for prefix in STALE_PREFIXES:
        assert prefix not in text, f"{readme.name}: устаревший путь {prefix!r}"


def test_readmes_are_in_sync():
    """Корневой README и README каталога — один текст.

    Они уже расходились: в корневом остался `docs/simintech-language/blocks/`,
    в каталог же был подставлен URL. Проверка не даёт разойтись снова.
    """
    root, catalog = README_PATHS
    assert root.read_text(encoding="utf-8") == catalog.read_text(
        encoding="utf-8"
    ), "README.md и skills-catalog/README.md разошлись"


@pytest.mark.skipif(CODE_DIR is None,
                    reason="рядом нет checkout simintech-code (задайте SIMINTECH_CODE_DIR)")
@pytest.mark.parametrize("path", _all_skill_files(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_referenced_paths_exist_in_simintech_code(path):
    """Ссылки ведут на реально существующие пути simintech-code."""
    text = path.read_text(encoding="utf-8")

    for ref in _referenced_code_paths(text):
        assert (CODE_DIR / ref).exists(), (
            f"{path.name}: в simintech-code нет пути {ref!r} "
            f"(искали в {CODE_DIR})"
        )
