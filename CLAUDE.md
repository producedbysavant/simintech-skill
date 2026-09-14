# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Что это

Скиллы (доменные знания) для ИИ-агента, работающего с SimInTech. Скиллы
дополняют MCP-инструменты: инструменты дают **возможности**, скиллы — **знания**.

## Состав

`skills-catalog/` — по каталогу на скилл, в каждом `SKILL.md` (frontmatter
`name`/`description` + инструкции) и `manifest.yaml` (метаданные).

Установочных зависимостей нет: скиллы — это markdown и yaml, сборка не нужна.

## Связь с другими репозиториями

- [`simintech-code`](https://github.com/producedbysavant/simintech-code) —
  библиотека `simintech-api` и знаниевый контент (`blocks/`, `language/`,
  `patterns/`, `tutorials/`, `automation/`). Скиллы **ссылаются** на него и не
  содержат копий: иначе появятся расходящиеся версии одного текста.
- [`simintech-mcp`](https://github.com/producedbysavant/simintech-mcp) —
  MCP-сервер, инструменты которого скиллы описывают.

## Команды

```bash
python3.11 -m pytest tests/unit -q     # проверка структуры каталога скиллов
```

## Правила

- **Имена параметров блоков SimInTech короткие и неочевидные**: у «Константы» —
  `a`, а не `y0`; у «Сумматора» нет `xn`. Источник истины —
  `simintech_api/data/block_catalog.json` в `simintech-code`, **не**
  `docs/simintech-language/blocks/` и не примеры: там встречаются несуществующие
  имена.
- **`SetBlockProp` не отвергает неизвестное имя свойства** — ошибка в имени
  приводит к молчаливому отказу, а не к исключению. Поэтому предупреждение
  `set_block_param` о том, что имени нет в каталоге, — не косметика.
- **Сигналы читаются только у проекта с базой сигналов.** Имена блоков сигналами
  не являются.
- Официальная справка: https://help.simintech.ru/
