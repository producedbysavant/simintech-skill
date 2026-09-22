"""Тесты каталога скиллов: структура, frontmatter, манифесты, ссылки.

`yaml` импортируется на уровне модуля намеренно: он объявлен в extras `test`,
а `pytest.importorskip("yaml")` превращал проверки манифестов в молчаливые
скипы — то есть в чистом окружении они проходили вхолостую.
"""

import json
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


def test_catalog_has_skills():
    """В каталоге есть хотя бы один скилл.

    Без этой проверки исчезновение всех каталогов-скиллов не роняло бы набор:
    параметризованные тесты просто не порождались бы, и прогон оставался зелёным.
    """
    skills = _skill_dirs()
    assert skills, f"в {CATALOG} нет ни одного каталога скилла"
    for skill in skills:
        assert (skill / "SKILL.md").is_file(), f"{skill.name}: нет SKILL.md"
        assert (skill / "manifest.yaml").is_file(), f"{skill.name}: нет manifest.yaml"


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


def _doc_id(path: pathlib.Path) -> str:
    """Идентификатор для параметризации: у двух README.md имена совпадают."""
    return f"{path.parent.name}/{path.name}"


def _all_docs():
    """Все документы, где операционные факты вообще встречаются."""
    return _all_skill_files() + list(README_PATHS)


def _artifact_is_linked(line: str, artifact: str) -> bool:
    """Артефакт упомянут внутри URL на simintech-code, а не отдельным путём."""
    for match in re.finditer(re.escape(artifact), line):
        head = line[:match.start()]
        if head.rstrip().endswith(("blob/main/", "tree/main/", "/")):
            return True
    return False


def _referenced_code_paths(text: str):
    """Пути внутри simintech-code, на которые ссылаются файлы скиллов."""
    paths = []
    for raw in CODE_REF_RE.findall(text):
        path = raw.split("#")[0].split(":")[0].rstrip(".,;").rstrip("/")
        if path:
            paths.append(path)
    return paths


def _find_code_dir():
    """Каталог checkout'а simintech-code, если он есть рядом с этим репозиторием.

    `SIMINTECH_CODE_DIR` — явная настройка: если она задана и указывает не на
    каталог, это ошибка конфигурации, а не повод молча пропустить проверку.
    Без переменной и без соседнего checkout проверка существования путей
    недоступна (репозитории разделены) — тогда тест скипается с причиной.
    """
    env = os.environ.get("SIMINTECH_CODE_DIR")
    if env:
        candidate = pathlib.Path(env)
        if not candidate.is_dir():
            pytest.fail(f"SIMINTECH_CODE_DIR={env!r} — не каталог")
        return candidate
    for parent in ROOT.parents:
        candidate = parent / "simintech-code"
        if candidate.is_dir():
            return candidate
    return None


CODE_DIR = _find_code_dir()


@pytest.mark.parametrize("path", _all_skill_files(), ids=_doc_id)
def test_no_stale_relative_paths(path):
    """Скиллы не ссылаются на пути старой раскладки репозитория.

    После разделения `docs/simintech-language/`, `simintech_api/` и
    `scripts/generate_block_catalog.py` живут в другом репозитории. Такие
    ссылки ломаются молча — поэтому проверяем явно.
    """
    text = path.read_text(encoding="utf-8")

    for prefix in STALE_PREFIXES:
        assert prefix not in text, f"{path.name}: устаревший путь {prefix!r}"


@pytest.mark.parametrize("path", _all_docs(), ids=_doc_id)
def test_references_point_to_simintech_code(path):
    """Артефакт simintech-code упоминается **ссылкой на него**, а не путём.

    Проверка построчная: требовалось лишь наличие любой ссылки на
    simintech-code где-то в файле, поэтому относительный путь рядом с валидной
    ссылкой на другой строке проходил незамеченным. Теперь у каждого упоминания
    артефакта URL должен стоять в той же строке.

    README каталога и корня проверяются наравне со скиллами: расхождение в них
    уже случалось.
    """
    text = path.read_text(encoding="utf-8")

    for artifact in CODE_ARTIFACTS:
        for number, line in enumerate(text.splitlines(), start=1):
            if artifact not in line:
                continue
            if CODE_URL in line or _artifact_is_linked(line, artifact):
                continue
            pytest.fail(
                f"{_doc_id(path)}:{number}: {artifact!r} упомянут без ссылки на "
                f"simintech-code в той же строке: {line.strip()!r}"
            )


@pytest.mark.parametrize("path", _all_skill_files(), ids=_doc_id)
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


@pytest.mark.parametrize("path", _all_skill_files(), ids=_doc_id)
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


@pytest.mark.parametrize("path", _all_skill_files(), ids=_doc_id)
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


# ─── Реестр функций языка ──────────────────────────────────────────

LANGUAGE_FUNCTIONS = "simintech_api/data/language_functions.json"


def test_language_core_points_at_function_registry():
    """Скилл языка отсылает к реестру функций, а не к угадыванию имён.

    Перечень имён в `language/*.md` — малая часть реестра, а правдоподобные
    имена (`tan`, `asin`, `pow`) в языке отсутствуют вовсе. Без ссылки агенту
    нечем спросить, существует ли имя, и ошибка всплывает только на
    кодогенерации.
    """
    text = (CATALOG / "simintech-language-core" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    assert LANGUAGE_FUNCTIONS in text, "нет ссылки на реестр функций языка"
    assert "find_function" in text, "не назван поиск по реестру"


# ─── Контракт инструментов, которому учат скиллы ──────────────────

# `CLAUDE.md` — инструкции агента: файл рабочей копии, в публикации его может
# не быть (он в `.gitignore`). Поэтому в набор попадают только существующие
# документы: отсутствие рабочей заметки — не повод падать гейту, а вот её
# содержимое, если она есть, проверяется наравне со скиллами.
CATALOG_CONTRACT_DOCS = tuple(
    path for path in (
        ROOT / "CLAUDE.md",
        CATALOG / "simintech-model-building" / "SKILL.md",
        CATALOG / "simintech-library-curation" / "SKILL.md",
    ) if path.exists()
)

# Фразы, описывающие снятый контракт `set_block_param`: он не «предупреждает»
# после записи, а отвергает запись ДО вызова COM (`isError`), а примечание о
# непроверенном имени осталось только для класса вне каталога. Агент, поверив
# такому тексту, идёт включать `allow_unknown=True` и возвращает себе
# молчаливую запись в никуда — ровно тот дефект, от которого защищает сверка.
STALE_CONTRACT_PHRASES = (
    "вернёт предупреждение",
    "set_block_param предупреждает",
    "предупреждение `set_block_param`",
    "значение применено, но имя не проверено",
    # Снято работой 13: чтение решает ветку по каталогу, а не по пустоте
    # ответа COM, поэтому «параметры неизвестны» больше не приходит —
    # ни для класса вне каталога, ни для отказавшего чтения.
    "параметры неизвестны",
)


@pytest.mark.parametrize("path", CATALOG_CONTRACT_DOCS, ids=_doc_id)
def test_docs_name_the_allow_unknown_escape_hatch(path):
    """Обход `allow_unknown` назван там, где описан отказ по имени."""
    assert "allow_unknown" in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", CATALOG_CONTRACT_DOCS, ids=_doc_id)
def test_docs_do_not_teach_the_removed_warning_contract(path):
    """Скиллы не обещают предупреждение там, где инструмент теперь отказывает."""
    text = " ".join(path.read_text(encoding="utf-8").split())

    for phrase in STALE_CONTRACT_PHRASES:
        assert phrase not in text, f"{_doc_id(path)}: снятый контракт — {phrase!r}"


@pytest.mark.skipif(
    CODE_DIR is None,
    reason="рядом нет checkout simintech-code (задайте SIMINTECH_CODE_DIR)",
)
@pytest.mark.parametrize("path", _all_skill_files(), ids=_doc_id)
def test_referenced_paths_exist_in_simintech_code(path):
    """Ссылки ведут на реально существующие пути simintech-code."""
    text = path.read_text(encoding="utf-8")

    for ref in _referenced_code_paths(text):
        assert (CODE_DIR / ref).exists(), (
            f"{path.name}: в simintech-code нет пути {ref!r} "
            f"(искали в {CODE_DIR})"
        )


# ─── Сверка с simintech-code: константы, каталог, таблицы свойств ────
#
# Скиллы пересказывают числа и списки из simintech-code: «2 класса через COM не
# создаются», «958 классов в каталоге», имена свойств. Копия и источник уже
# расходились — здесь стояло «12 классов» против 958, а «(5)» — против двух
# записей, — потому что связи между ними не было никакой. Дальше она машинная.
#
# `simintech_api` при этом НЕ импортируется: в `pyproject.toml` у репозитория
# `dependencies = []`, и библиотеки рядом может не быть вовсе. `constants.py`
# читается как текст, `block_catalog.json` — как JSON.

CONSTANTS_PATH = "simintech_api/constants.py"
BLOCK_CATALOG_PATH = "simintech_api/data/block_catalog.json"

requires_code = pytest.mark.skipif(
    CODE_DIR is None,
    reason="рядом нет checkout simintech-code (задайте SIMINTECH_CODE_DIR)",
)


def _code_text(relative: str) -> str:
    """Файл simintech-code как текст — без импорта библиотеки."""
    assert CODE_DIR is not None
    return (CODE_DIR / relative).read_text(encoding="utf-8")


def _code_json(relative: str) -> dict:
    """Файл simintech-code как JSON — без импорта библиотеки."""
    return json.loads(_code_text(relative))


def _constants_names(text: str, name: str) -> set:
    """Имена из множества `name = { … }` в constants.py."""
    match = re.search(rf"^{name}\s*=\s*\{{(.*?)^\}}", text, re.S | re.M)
    assert match, f"в constants.py нет множества {name}"
    return set(re.findall(r'"([^"]+)"', match.group(1)))


def _quoted(text: str) -> set:
    """Имена в кавычках-ёлочках, с нормализованными переводами строк."""
    return {" ".join(q.split()) for q in re.findall(r"«([^»]+)»", text)}


def _skill(name: str) -> str:
    return (CATALOG / name / "SKILL.md").read_text(encoding="utf-8")


def _flat(text: str) -> str:
    """Текст без переносов строк: перенос в markdown не смысловой."""
    return " ".join(text.split())


def _class_paragraphs(skill_text: str):
    """Абзацы об отвергаемых библиотекой и создаваемых классах — без FSM-раздела.

    Заголовок правится вместе с прозой (см. проверку смысла ниже), поэтому
    здесь он один и тот же источник, что и в `simintech-model-building`.
    """
    section = _flat(skill_text).split("## Классы, которые отвергает библиотека", 1)[1]
    section = section.split("## Библиотека", 1)[0]
    return section.split("Проверенно создаваемые", 1)


@requires_code
def test_unsupported_classes_in_skill_match_constants():
    """Список несоздаваемых классов — тот же, что в constants.py.

    «(5)» из прошлой редакции против двух записей в коде — тот самый дрейф,
    который ловится здесь: и число, и имена берутся из источника, а не из
    памяти агента, правившего текст.
    """
    unsupported = _constants_names(
        _code_text(CONSTANTS_PATH), "UNSUPPORTED_COM_BLOCK_CLASSES"
    )
    paragraph, _ = _class_paragraphs(_skill("simintech-model-building"))

    match = re.search(r"UNSUPPORTED_COM_BLOCK_CLASSES`\s*\((\d+)\)", paragraph)
    assert match, "скилл не называет число записей UNSUPPORTED_COM_BLOCK_CLASSES"
    assert int(match.group(1)) == len(unsupported), (
        f"скилл называет {match.group(1)} записей, в constants.py — {len(unsupported)}"
    )

    # Цитата-пояснение из комментария constants.py («создаётся (id != 0), …») —
    # не имя класса: у имён нет ни скобок, ни запятых.
    listed = {
        name for name in _quoted(paragraph) if "(" not in name and "," not in name
    }
    assert listed == unsupported, (
        f"скилл: {sorted(listed)}, constants.py: {sorted(unsupported)}"
    )


@requires_code
def test_supported_classes_in_skill_match_constants():
    """Список создаваемых классов — тот же, что в constants.py."""
    supported = _constants_names(
        _code_text(CONSTANTS_PATH), "SUPPORTED_COM_BLOCK_CLASSES"
    )
    _, paragraph = _class_paragraphs(_skill("simintech-model-building"))

    match = re.search(r"SUPPORTED_COM_BLOCK_CLASSES`,\s*(\d+)\)", paragraph)
    assert match, "скилл не называет число записей SUPPORTED_COM_BLOCK_CLASSES"
    assert int(match.group(1)) == len(supported), (
        f"скилл называет {match.group(1)} классов, в constants.py — {len(supported)}"
    )
    assert _quoted(paragraph) == supported, (
        f"скилл: {sorted(_quoted(paragraph))}, constants.py: {sorted(supported)}"
    )


@requires_code
def test_language_core_unsupported_classes_match_constants():
    """Перечень классов «вне COM» в скилле языка — тот же, что в constants.py.

    Именно эта пара строк и разрослась когда-то до пяти классов, включая
    «Флаг входа в состояние», который создаётся.
    """
    unsupported = _constants_names(
        _code_text(CONSTANTS_PATH), "UNSUPPORTED_COM_BLOCK_CLASSES"
    )
    flat = _flat(_skill("simintech-language-core"))
    section = flat.split("которые отвергает библиотека:", 1)[1]
    listed = _quoted(section.split("См. набор", 1)[0])

    assert listed == unsupported, (
        f"скилл языка: {sorted(listed)}, constants.py: {sorted(unsupported)}"
    )


# Имена и число сверялись и раньше — а проза нет: «CreateBlock для них не
# работает» пережило и гейты выше, и замер 2026-09-18, по которому `CreateBlock`
# создаёт **обе** записи и возвращает ненулевой id. Отказ идёт от библиотеки
# (`Page.create_block` → `UnsupportedBlockError`) и по другой причине: годность
# этих блоков в расчёте не проверена. Списки совпадали — расходился смысл.
#
# Разница для агента принципиальна: «создать нельзя» отправляет в другой
# инструмент (встроенный язык), «создать можно, но работать не доказано» —
# означает отказ библиотеки, который снимут, когда пригодность подтвердят.
# Поэтому проверка держит смысл, а не только перечень.

#: Скиллы, которые называют классы, отвергаемые библиотекой.
REFUSED_CLASSES_SKILLS = (
    "simintech-model-building",
    "simintech-language-core",
    "simintech-library-curation",
)

#: Формулировки, опровергнутые замером 2026-09-18. Именно они утверждают, что
#: создание невозможно, тогда как невозможен только расчёт с этими блоками.
REFUTED_CLAIMS = ("не создаются", "для них не работает")

#: Причина отказа, которую скилл обязан назвать рядом с перечнем.
UNPROVEN_STEMS = ("не проверена", "не проверено", "не подтверждена", "не подтверждено")


def _refused_classes_window(skill_text: str, width: int = 400) -> str:
    """Отрезок скилла вокруг перечня классов, отвергаемых библиотекой.

    Окно, а не якорь-заголовок: заголовок правится вместе с прозой, и гейт,
    привязанный к нему дословно, ломался бы на каждой правке формулировки,
    ничего не проверяя по существу.
    """
    flat = _flat(skill_text)
    at = flat.index("«Из памяти»")
    return flat[max(0, at - width):at + width]


@requires_code
def test_skills_do_not_claim_refused_classes_cannot_be_created():
    """Проза о классах вне COM совпадает с замером, а не только их список.

    Проверка парная: сначала опровергнутое утверждение не должно встречаться,
    затем рядом обязан стоять настоящий повод отказа. Одного запрета мало —
    формулировку можно «починить» так, что причина исчезнет совсем, и агент
    снова останется без объяснения, почему класс в списке.
    """
    for skill in REFUSED_CLASSES_SKILLS:
        window = _refused_classes_window(_skill(skill)).lower()
        for claim in REFUTED_CLAIMS:
            assert claim not in window, (
                f"{skill}: формулировка «{claim}» опровергнута замером "
                "2026-09-18 — CreateBlock создаёт обе записи"
            )
        assert any(stem in window for stem in UNPROVEN_STEMS), (
            f"{skill}: рядом с перечнем не названа причина отказа — "
            "годность блоков в расчёте"
        )


#: Описание скилла — то, по чему агент выбирает скилл, ещё до чтения тела.
#: Ложное «создать нельзя» маршрутизирует не туда ровно так же, поэтому
#: держится отдельной проверкой: она не требует checkout'а simintech-code и
#: работает на любом PR.
REFUTED_DESCRIPTION_CLAIMS = ("cannot be created", "cannot create")


def test_skill_descriptions_do_not_claim_blocks_cannot_be_created():
    """Описания скиллов не утверждают, что блок нельзя создать через COM.

    Замер 2026-09-18: `CreateBlock` создаёт отвергаемые библиотекой классы.
    Описание, обещающее обратное, уводит агента в встроенный язык там, где
    достаточно COM, — и это стоит ему попытки, а не только неточности.
    """
    for skill in _skill_dirs():
        description = _read_frontmatter(skill / "SKILL.md").get("description", "")
        for claim in REFUTED_DESCRIPTION_CLAIMS:
            assert claim not in description.lower(), (
                f"{skill.name}: описание утверждает «{claim}» — опровергнуто "
                "замером 2026-09-18"
            )


def test_skill_descriptions_name_who_refuses():
    """Сказано, **кто** отказывает, — запрета на формулировку для этого мало.

    Парная половина проверки выше: описание можно «починить» так, что про
    отказ не останется ни слова, и агент снова не поймёт, куда идти — в COM
    или в библиотеку. Требование включается только там, где описание вообще
    говорит об отказе: описание, не касающееся темы, ничего не должно
    называть.
    """
    for skill in _skill_dirs():
        description = _read_frontmatter(skill / "SKILL.md").get("description", "")
        if "refus" not in description.lower():
            continue
        assert "library" in description.lower(), (
            f"{skill.name}: описание говорит об отказе, не называя, кто "
            "отказывает — отказ идёт от библиотеки, а не от COM"
        )


@requires_code
def test_fsm_example_matches_constants():
    """Пример создания блока FSM идёт по полному имени записи из constants.py.

    Короткий заголовок с палитры `CreateBlock` не принимает, поэтому имя в
    примере обязано быть записью библиотеки — иначе пример молча не работает.
    """
    text = _code_text(CONSTANTS_PATH)
    prefix_match = re.search(r'^FSM_RECORD_PREFIX\s*=\s*"([^"]+)"', text, re.M)
    assert prefix_match, "в constants.py нет FSM_RECORD_PREFIX"
    prefix = prefix_match.group(1)
    records = {
        prefix + suffix
        for suffix in re.findall(r'FSM_RECORD_PREFIX\s*\+\s*"([^"]+)"', text)
    }
    assert records, "в constants.py нет записей FSM_BLOCK_RECORDS"

    skill = _flat(_skill("simintech-model-building"))
    assert prefix in skill, "скилл не называет префикс полного имени записи"

    examples = re.findall(r'add_block\(class_name="([^"]+)"\)', skill)
    assert examples, "в скилле нет примера создания блока по полному имени записи"
    for name in examples:
        assert name in records, f"{name!r} — не запись библиотеки конечных автоматов"


@requires_code
def test_catalog_class_count_in_skill_matches_source():
    """Число классов каталога в скилле — то же, что в block_catalog.json.

    Здесь стояло «12 классов» при 958 в каталоге: число, за которым ничего не
    проверяло, устарело молча.
    """
    total = len(_code_json(BLOCK_CATALOG_PATH)["classes"])
    text = _skill("simintech-library-curation")

    match = re.search(r"\*\*(\d+) классов\*\*", text)
    assert match, "скилл не называет число классов каталога"
    assert int(match.group(1)) == total, (
        f"скилл называет {match.group(1)} классов, в block_catalog.json — {total}"
    )


# Работа 18 плана аудита, действие 4, решена этим тестом: таблицы свойств
# ОСТАВЛЕНЫ, и наличие таблицы закреплено здесь сознательно. Действие 4
# предлагало снять пересказ таблиц источника, оставив ссылку; но строки таблицы
# несут не только имена из `block_catalog.json` (у «Сумматора» число входов
# задаёт `in_ports` у `add_block`, а не длина массива `a`; `value`/`signs`/
# `numInputs` — вообще не свойства), а сам каталог в контекст целиком не
# влезает (958 классов, ≈40k токенов). От дрейфа копию стережёт именно этот
# тест — потому он и требует, чтобы таблица была на месте.
# Снять таблицу можно только вместе с тестом и только как решение, а не как
# уборку «невыполненного пункта»: без теста копия теряет связь с источником.
@requires_code
def test_property_tables_use_real_property_names():
    """Имена свойств в таблицах скиллов есть в block_catalog.json.

    Ограничитель того же класса, что `test_default_catalog_uses_real_property_names`
    в simintech-code: выдуманное имя (`y0` у «Константы», `xn` у «Сумматора»)
    роняет таблицу, а не уезжает к агенту как правдоподобный факт.
    """
    catalog = _code_json(BLOCK_CATALOG_PATH)
    classes = catalog["classes"]
    common = set(catalog["common"])

    text = _skill("simintech-model-building")
    section = text.split("## Имена свойств", 1)[1].split("## Формат значений", 1)[0]

    checked = 0
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 2 or cells[0] in ("Класс", "---"):
            continue
        class_name, params = cells
        allowed = common if class_name == "любой" else set(classes.get(class_name, {}))
        assert allowed, f"{class_name}: класса нет в block_catalog.json"
        # Имена перечислены до первой скобки-пояснения; дальше идут аргументы
        # инструментов (`in_ports`, `add_block`) — это не свойства блока.
        for param in re.findall(r"`([^`]+)`", params.split("(")[0]):
            assert param in allowed, (
                f"{class_name}: параметра {param!r} нет в block_catalog.json"
            )
        checked += 1

    assert checked >= 5, "таблица свойств не разобралась"


@requires_code
def test_simulation_file_block_props_match_catalog():
    """Свойства блока «В файл» в скилле расчёта — из block_catalog.json."""
    allowed = set(_code_json(BLOCK_CATALOG_PATH)["classes"]["В файл"])
    text = _skill("simintech-simulation")
    sentence = text.split("Свойства блока «В файл»:", 1)[1].split("Блок пишет", 1)[0]

    named = {
        prop
        for prop in re.findall(r"`([^`]+)`", sentence)
        if re.fullmatch(r"[A-Za-z_]\w*", prop)
    }
    assert named, "свойства блока «В файл» не названы"
    assert named <= allowed, f"выдуманные свойства: {sorted(named - allowed)}"
