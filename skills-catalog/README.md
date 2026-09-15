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
| `simintech-language-core/` | Встроенный язык SimInTech, блоки вне COM API |
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

Имена свойств блоков и поведение COM API в этих скиллах взяты из проверенных
источников — все они лежат в
[`simintech-code`](https://github.com/producedbysavant/simintech-code):
рабочий код [`examples/`](https://github.com/producedbysavant/simintech-code/tree/main/examples),
карта методов
[`docs/reference/com_api_inventory.md`](https://github.com/producedbysavant/simintech-code/blob/main/docs/reference/com_api_inventory.md)
и [`REPORT.md`](https://github.com/producedbysavant/simintech-code/blob/main/REPORT.md).

**Чего в скиллах нет намеренно:** имён свойств из
[`blocks/`](https://github.com/producedbysavant/simintech-code/tree/main/blocks).
Там используются читаемые имена
(`value`, `signs`, `numInputs`), которые с реальными (`a`, `y0`, `k`)
**не совпадают**. Опираться на них нельзя — см. `simintech-library-curation/`.

## Проверка

```bash
pip install -e ".[test]"
python3.11 -m pytest tests/unit -q      # 72 теста
```

Тесты проверяют структуру каталога, frontmatter и манифесты, а также что
ссылки ведут на `simintech-code`, а не на пути старой раскладки. `pyyaml`
объявлен в extras `test` и импортируется на уровне модуля: без него набор
падает, а не проходит вхолостую.

Проверка, что пути внутри `simintech-code` реально существуют, требует его
checkout рядом (или `SIMINTECH_CODE_DIR`); без него она пропускается с причиной.
