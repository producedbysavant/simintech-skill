---
name: simintech-model-ir
description: "Use when the whole SimInTech model must be understood without reading XML: load_model, model_ref snapshots, manifest, exact graph queries, block contracts and build_and_verify(SystemSpec) verdicts. Covers coverage, unknown and partial semantics."
---

# Model IR: полная модель вне контекста

## Когда применять

- модель большая и читать `.xprt` в контекст нельзя;
- нужны точные ответы по всей системе: связи, пути, циклы, сравнение версий;
- нужно понять, что парсер не разобрал, а не принять `unknown` за пустое множество;
- нужно собрать систему по `SystemSpec` и получить вердикт по фактической модели.

Не разбирайте `.xprt` и `.prt` самодельно. Полная модель живёт в снимке
сервера, агенту выдаются паспорт и точные ответы.

## Порядок

```
doctor -> load_model -> get_model_manifest -> query_model
       -> build_and_verify(spec=SystemSpec(...)) -> simulate
```

Краткое руководство сервера: `simintech://guides/model-ir`. Полные описания
инструментов: `simintech://tools/<name>`.

`build_and_verify` нужен, когда модель строится по спецификации. Для анализа
уже открытого проекта достаточно цепочки `load_model -> manifest -> query_model`.

## 1. load_model

```
load_model(path="", sources=None, strict=False)
```

- `path=""` читает текущий проект: `.xprt` снимается `SaveProjectXML` без
  запуска расчёта. Проект должен быть открыт.
- `path` указывает файл в каталоге результатов. Источник выбирается по
  расширению: `.xprt`/`.xml`, `.txt` (`savemodeltofile`), `.topology`/`.tsv`.
- `sources` для текущего проекта: `xprt` (по умолчанию), `model_text`,
  `topology`. `.xprt` первичен; текст и топология идут контуром, сдвигают
  модельное время и служат сверкой.
- `strict=True` превращает расхождение источников в отказ, а не в запись
  `discrepancies`.

Ответ содержит `model_ref`, `model_hash`, `content_hash`, `ir_schema`,
`sources`, `source_name`, счётчики, покрытие, первые расхождения и подсказки.
XML, скрипты и полные значения свойств не возвращаются.

### model_ref

`model_ref` - непрозрачный снимок в памяти, вид `mir1.<hash>.<generation>.<seq>`.
Сервер держит не больше двух снимков.

- после правки проекта или смены проекта старый `model_ref` устаревает;
- вытесненный снимок становится неизвестной ссылкой;
- в обоих случаях нужен новый `load_model`, а не догадка о содержимом.

Не сохраняйте `model_ref` в заметках между правками: он не переживёт изменение
проекта.

### Покрытие

Смотрите `coverage` раньше списков:

- `source_status`: `ok` или `partial`;
- `unresolved_ends`, `unresolved_branches`: концы и ветви, которые не удалось
  разрешить;
- `unconnected_ends`: нормальные висячие концы, не потеря;
- `unknown_object_types`, `external_submodels`: что не входит в известную
  модель;
- `skipped`: что пропущено и почему.

`partial`, `unknown` и `not_evaluated` не означают пустое множество. Если
покрытие частичное, вердикт `passed` по структуре не доказывает полноту.

## 2. Паспорт

```
get_model_manifest(model_ref, budget_tokens=3000, focus="")
```

Markdown-паспорт в бюджете 2000..5000 токенов. Разделы: `Header`, `Coverage`,
`Structure`, `Classes`, `Signals`, `Hot nodes`, `Contracts`, `Discrepancies`,
`Omitted`. `focus` оставляет выбранный раздел плюс заголовок и покрытие.
`Omitted` называет, что не поместилось: это не пустой раздел.

Паспорт строится кодом. Не просите агента писать паспорт по прочитанному XML.

## 3. Запросы к графу

```
query_model(model_ref, query, arguments={...})
```

| Запрос | Аргументы | Когда нужен |
|---|---|---|
| `inspect_node` | `node` | контракт одного объекта или порта |
| `find_objects` | `query`, `class_name`, `kind`, `limit` | поиск объектов |
| `trace_signal` | `signal`, `direction`: `forward`/`backward`/`both`, `max_depth` | распространение сигнала |
| `ancestors` | `node`, `max_depth` | источники влияния |
| `descendants` | `node`, `max_depth` | потребители влияния |
| `find_path` | `src`, `dst`, `max_length` | цепочка между объектами |
| `find_cycles` | `max_cycles` | обратные связи |
| `check_connections` | нет | висячие входы, несколько драйверов, неразрешённые концы |
| `compare_models` | `other_ref`, `include_geometry` | сравнение двух снимков |
| `validate_invariants` | `invariants` | инженерные инварианты |
| `list_discrepancies` | `severity`, `code`, `limit` | расхождения источников |
| `coverage` | нет | покрытие снимка |

Ответ несёт `scope`, `model_hash`, `evidence`, `unknown` и `truncated`.
`unknown` означает, что ссылка не разрешена, а не что связей нет.
`truncated` означает, что ответ обрезан: увеличьте лимит или сузьте запрос.

`find_cycles` не является ошибкой. В динамической системе обратная связь
ожидаема; вердикт даёт контракт конкретной модели, а не наличие цикла.

`compare_models` сравнивает структуру; геометрия включается только
`include_geometry=True`. Для двух версий сначала сделайте два `load_model`.

## 4. Контракты блоков

`query_model(check_connections)` добавляет в `evidence.contracts` оценку портов
по реестру 958 классов:

- `fixed` и `nport`: порты проверяются, статус `evaluated`;
- `portnames`: порты задаёт значение `PortNames` экземпляра, образец реестра
  не эталон, поэтому `not_evaluated` с причиной `portnames_instance_defined`;
- `submodel` и `unknown`: `not_evaluated` с причиной.

`query_model(validate_invariants)` с инвариантом `contract_ports_match`
заменяет общий `not_evaluated` результатом реестра. Для `portnames` результат
остаётся `not_evaluated`, а не `passed`: это честно.

Свойства и порты одного класса:

```
simintech://blocks/contracts/<класс>
```

Сводка покрытия реестра:

```
simintech://blocks/contracts
```

Полный дамп реестра в контекст не выводится.

## 5. build_and_verify

```
build_and_verify(spec=SystemSpec(...), project_hint="model", end_time=None,
                 new_project=True, layout=True, fit_sizes=True, max_items=50)
```

`SystemSpec` - декларативная спецификация системы:

- `schema: "system-spec/1"`;
- `blocks`: `name`, `class`, `props`, `ports`, `portnames`, `subsystem`;
- `wires`: `src` и `dst` в форме `блок:out:N` и `блок:in:N`;
- `invariants`, `requirements`, `assertions`;
- `verification_profile`: `readback`, `simulate`, `tolerance`,
  `check_geometry`, `build_strategy="auto"`;
- `provenance`.

`ports` - подсказки `inputs`/`outputs` для проверки, а не команда создать
порты. `portnames` - поле записи для порт-блоков и ячеек памяти; то же имя в
`props` переносится в поле только у portnames-классов. Схема строгая:
неизвестные поля верхнего уровня и блока, опечатки в `ports` и
неподдержанный профиль отвергаются до COM.

Порядок работы инструмента:

1. компиляция спецификации: классы, свойства, имена, концы проводов,
   самопетли, инварианты, требования и assertions; ошибки собираются все за
   один вызов;
2. сборка как `ModelSpec`: блоки и субмодели текстом, верхнеуровневые провода
   через `connect`, подгонка размеров и раскладка;
3. readback фактического `.xprt` без запуска расчёта;
4. сверка объектов, классов, портов, проводов, вложенных субмоделей и
   инвариантов;
5. отчёт с вердиктом.

### Вердикт

- `failed`: хотя бы одно расхождение;
- `partial`: есть `unknown` или `not_evaluated`, но нет `failed`;
- `passed`: все запрошенные проверки прошли.

`partial` не равен `passed`. Расчётные `assertions`, `simulate`,
`check_geometry` и readback не через `.xprt` остаются `not_evaluated`.
Сейчас readback всегда идёт по `.xprt`.

`portnames`-класс без подсказок `ports` даёт `port_unknown` и `partial`:
порты задаются значением экземпляра. Чтобы проверить порты, задайте `ports`;
если точные порты не нужны, примите `partial` осознанно.

`contract_ports_match` для `portnames` остаётся `not_evaluated` по той же
причине.

### Отчёт

Отчёт содержит вердикт, имя спецификации, счётчики сборки, хеш модели,
покрытие, счётчики проверок, ограниченный список пунктов (сначала `failed`),
предупреждения сборки и подсказки. `max_items` ограничивает список, но не
счётчики и не вердикт.

`model_ref` не возвращается: сборка помечает проект изменённым, ссылка
устарела бы сразу. Для запросов к собранной модели вызовите `load_model`.

`new_project=True` по умолчанию строит чистую модель; при несохранённых
правках вызов отказывает, пока их не сохранить. `new_project=False` дополняет
текущий проект, и лишние объекты дадут расхождения.

Поля `contracts` и `signals` из расширенного плана в M3 не входят: схема их
отвергает, чтобы не терять молча.

## 6. Ограничения

- Живой приёмки на Windows в M3 не было: unit-набор и CI не заменяют прогон
  на SimInTech.
- Расчётные испытания assertions не реализованы; произвольный код не
  исполняется.
- `topology` не содержит геометрии, ветвей, свойств и скриптов; это сверка, а
  не замена `.xprt`.
- `.prt` не разбирается вручную; интроспекция только инструментами сервера.

## Примеры

### Анализ существующей модели

```
doctor
load_model()                         # model_ref, покрытие, расхождения
get_model_manifest(model_ref)        # паспорт в бюджете
query_model(model_ref, "find_objects", {"query": "ТПр"})
query_model(model_ref, "trace_signal", {"signal": "01Tp1_On",
                                        "direction": "both"})
query_model(model_ref, "check_connections")
```

После правки проекта или смены проекта повторите `load_model`: старый
`model_ref` устарел.

### Сборка и проверка

```
build_and_verify(spec={
  "schema": "system-spec/1",
  "name": "chain",
  "blocks": [
    {"name": "Step", "class": "Ступенька", "ports": {"outputs": ["y"]}},
    {"name": "Gain", "class": "Усилитель",
     "ports": {"inputs": ["u"], "outputs": ["y"]}},
    {"name": "Graph", "class": "Временной график",
     "ports": {"inputs": ["u"]}}
  ],
  "wires": [
    {"src": "Step:out:0", "dst": "Gain:in:0"},
    {"src": "Gain:out:1", "dst": "Graph:in:0"}
  ]
})
```

Если вердикт `failed`, читайте пункты `wire_missing`, `object_missing`,
`port_mismatch` и предупреждения сборки. Если `partial` из-за `port_unknown`,
добавьте `ports` или примите частичную проверку.

### Сравнение версий

```
one = json.loads(load_model(path="before.xprt"))
two = json.loads(load_model(path="after.xprt"))
query_model(one["model_ref"], "compare_models",
            {"other_ref": two["model_ref"]})
```

## Что не делать

- не читать `.xprt` целиком и не пересказывать XML вручную;
- не считать `unknown`, `partial` и `not_evaluated` пустым множеством или
  успехом;
- не переиспользовать `model_ref` после правки проекта;
- не ждать `model_ref` от `build_and_verify`;
- не передавать в `SystemSpec` поля `contracts` и `signals`;
- не заменять реестр контрактов энциклопедией классов в скилле.
