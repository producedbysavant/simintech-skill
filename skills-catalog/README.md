# Каталог скиллов SimInTech

Доменные знания для ИИ-агента, работающего с SimInTech через MCP-сервер
(`simintech-mcp`) или библиотеку `simintech-api`.

Скиллы дополняют MCP-инструменты: инструменты дают **возможности** (создать
блок, соединить, запустить расчёт), скиллы — **знания** (какие имена свойств
реальны, где молчаливый отказ, как обходить ограничения COM API).

## Состав

| Скилл | Когда применять |
|---|---|
| `simintech-model-building/` | Создание и правка модели: блоки, связи, параметры |
| `simintech-simulation/` | Запуск расчёта, шаги, чтение сигналов |
| `simintech-language-core/` | Встроенный язык SimInTech, классы, которые отвергает библиотека |
| `simintech-library-curation/` | Регенерация каталога свойств блоков |

## Что не вошло

`simintech-code-generation` (генерация C/ST-кода) в исходном плане
предусматривался, но материала по нему в репозитории нет — писать скилл
пришлось бы целиком из общих соображений. Не добавлен сознательно.

## Формат

Каждый скилл — каталог с `SKILL.md` (frontmatter `name`/`description` +
инструкции) и `manifest.yaml` (метаданные). Такой формат понимают Claude Code
и родственные агентские платформы.

## Достоверность знаний

Поведение COM API в этих скиллах описано по проверенным источникам из
[`simintech-code`](https://github.com/producedbysavant/simintech-code):
рабочему коду [`examples/`](https://github.com/producedbysavant/simintech-code/tree/main/examples),
карте методов
[`docs/reference/com_api_inventory.md`](https://github.com/producedbysavant/simintech-code/blob/main/docs/reference/com_api_inventory.md)
и [`REPORT.md`](https://github.com/producedbysavant/simintech-code/blob/main/REPORT.md).
Имена свойств из примеров при этом недостоверны (там ставили `xn`
«Сумматору», хотя такого параметра нет): источник истины по именам —
[`simintech_api/data/block_catalog.json`](https://github.com/producedbysavant/simintech-code/blob/main/simintech_api/data/block_catalog.json).

**Чего в скиллах нет намеренно:** имён свойств из
[`blocks/`](https://github.com/producedbysavant/simintech-code/tree/main/blocks).
Там используются читаемые имена
(`value`, `signs`, `numInputs`), которые с реальными (`a`, `y0`, `k`)
**не совпадают**. Опираться на них нельзя — см. `simintech-library-curation/`.

## Проверка

```bash
pip install -e ".[test]"
python3.11 -m pytest tests/unit -q      # 86 тестов
python3.11 -m flake8 tests --max-line-length=88 --extend-ignore=E203,W503
```

Тесты проверяют структуру каталога, frontmatter и манифесты, а также что
ссылки ведут на `simintech-code`, а не на пути старой раскладки. `pyyaml`
объявлен в extras `test` и импортируется на уровне модуля: без него набор
падает, а не проходит вхолостую.

Проверка, что пути внутри `simintech-code` реально существуют, требует его
checkout рядом (или `SIMINTECH_CODE_DIR`); без него она пропускается с причиной.
Оттуда же берётся и сверка пересказанного с источником: набор несоздаваемых
классов — из
[`simintech_api/constants.py`](https://github.com/producedbysavant/simintech-code/blob/main/simintech_api/constants.py),
число классов каталога и имена свойств в таблицах — из
[`block_catalog.json`](https://github.com/producedbysavant/simintech-code/blob/main/simintech_api/data/block_catalog.json).
Оба файла читаются как текст и JSON: `simintech_api` этот репозиторий
намеренно не импортирует.
