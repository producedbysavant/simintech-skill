---
name: simintech-library-curation
description: Use when block property names need to be known, verified, or added to the catalog — before writing a block catalog by hand, or when set_block_param reports a parameter missing from the catalog.
---

# Каталог свойств блоков

## Зачем каталог существует

В COM API **нет метода перечисления свойств блока**: ни `GetPropCount`, ни
`GetPropName`. Есть только:

- `GetBlockPropAsString(BlockId, PropName)` — прочитать
- `SetBlockProp(BlockId, PropName, StrValue)` — записать
- `GetPropHandle(BlockId, PropName)` — handle

Всем трём имя свойства нужно **знать заранее**. Поэтому имена хранятся в
каталоге: `https://github.com/producedbysavant/simintech-code/blob/main/simintech_api/data/block_catalog.json`.

## Почему нельзя писать каталог вручную

`SetBlockProp` **не отвергает неизвестное имя свойства**. Опечатка или
выдуманное имя не даёт ошибки: параметр «устанавливается», вызов успешен, а
расчёт идёт по прежнему значению. **Отказ молчаливый.**

Прямое подтверждение — [карта COM API](https://github.com/producedbysavant/simintech-code/blob/main/docs/reference/com_api_inventory.md), раздел
«Критические ограничения»: `SetBlockProp("a")` не влияет на симуляцию, если
блок уже инициализирован.

Отсюда правило: **каталог генерировать, а не сочинять.**

## Как сгенерировать

Обход (снятие выгрузки) требует Windows и зарегистрированного COM-сервера;
разбор готовой выгрузки и измерение покрытия работают где угодно, включая Linux.

**Полный обход (Windows).** Классы берутся из индекса библиотек `.csl`,
ограниченного профилем, поэтому каталог покрывает всё, что профиль грузит:

```bash
# требуется Windows и зарегистрированный COM-сервер
mmain.exe /regserver
simintech-generate-catalog --bin-dir /mnt/c/SimInTech64/bin \
    --profile /mnt/c/SimInTech64/bin/profiles/simintech_rus_64/base.xml \
    --dump /tmp/all-blocks.xprt --out /tmp/catalog.json
```

Обход создаёт по одному блоку каждого класса, экспортирует проект в `.xprt` и
разбирает секцию **`<custom_props>`** каждого объекта.
`--merge <существующий каталог>` дополняет готовый каталог: обходятся только
те классы, которых в нём ещё нет.

**Разбор готовой выгрузки (где угодно, включая Linux).** Долгая часть — снятие
выгрузки — отделена от разбора, поэтому сохранённый `.xprt` разбирается без
COM:

```bash
simintech-generate-catalog --xprt /tmp/all-blocks.xprt --out catalog.json
```

**Измерение покрытия.** Показывает, для какой доли классов профиля имена
параметров действительно проверены:

```bash
simintech-generate-catalog --coverage --bin-dir <bin> --profile <base.xml>
```

**Голый `simintech-generate-catalog` затирает поставку.** Без `--bin-dir`
список классов не читается из индекса библиотек, и обход идёт по
`SUPPORTED_COM_BLOCK_CLASSES` — это 13 классов. `--out` по умолчанию указывает
на [`simintech_api/data/block_catalog.json`](https://github.com/producedbysavant/simintech-code/blob/main/simintech_api/data/block_catalog.json)
в `simintech-code`, поэтому такой запуск печатает «Классов с известными
свойствами: 13» и **переписывает поставляемый каталог** — после этого сверка
имён в MCP лишается данных для сотен классов, и запись в несуществующее имя
снова проходит молча. Указывайте `--out` на отдельный файл.

Два места, где легко ошибиться (обе ошибки уже были допущены):

- **`<custom_props>`, а не `<visual_props>`.** В `visual_props` лежит
  оформление (`Color`, `Points`, `LabelFont`); параметров расчёта там нет.
  Парсер, читавший `visual_props`, давал пустой каталог без ошибок.
- **UTF-8 с BOM, а не cp1251.** cp1251 декодирует любые байты, поэтому
  неверная кодировка не падает, а портит русские имена классов — и фильтр
  молча отбрасывает все классы.

Проверить результат:

```bash
python -m pytest tests/unit/test_catalog.py -v
```

Тест `test_default_catalog_uses_real_property_names` — ограничитель: он упадёт,
если в каталог попадут выдуманные имена (`value`, `signs`, `numInputs`).

## Текущее состояние каталога

Каталог в поставке собран из реального SimInTech (`meta.source == "generated"`).
Число классов в этом тексте не постоянно — оно устаревает молча, и скилл уже
ошибался так: стоявшее здесь число отставало от каталога на десятки раз.
Актуальную цифру даёт `--coverage` (см. «Как сгенерировать») или
`len(load_default_catalog().classes())` (см. «Проверить состояние» ниже).

На 2026-09-17 измерено: **958 классов**; покрытие имён — 81.6% (848 из 1039).
Даты выгрузки в `meta` каталога нет — её даёт git-история
[`simintech_api/data/block_catalog.json`](https://github.com/producedbysavant/simintech-code/blob/main/simintech_api/data/block_catalog.json).

`CreateBlock` создаёт и «Из памяти», и «Порт выхода» (замерено на живом COM
2026-09-18), но библиотека их отвергает: годность в расчёте не проверена
(`UNSUPPORTED_COM_BLOCK_CLASSES`); блоки «Конечные автоматы» — в том числе
«Состояние автомата» и «Выход данных состояния» — создаются, но только по
полному имени записи, с префиксом «Конечные автоматы - » (см.
[`simintech_api/constants.py`](https://github.com/producedbysavant/simintech-code/blob/main/simintech_api/constants.py)).

**Не копируйте имена из примеров.** Первая версия каталога была засеяна вручную
по [`examples/`](https://github.com/producedbysavant/simintech-code/tree/main/examples)
— и оказалась неверной: там ставили `y0` «Константе» (реальный
параметр `a`) и `xn` «Сумматору» (параметра нет). Ошибка была молчаливой:
модель строилась с дефолтной константой вместо заданной.

Проверить состояние:

```python
from simintech_api.catalog import load_default_catalog
cat = load_default_catalog()
print(cat.meta["source"])      # "seed" или "generated"
print(cat.classes())
```

## Ловушка: посторонняя документация

`https://github.com/producedbysavant/simintech-code/blob/main/blocks/` содержит таблицы параметров блоков с
**читаемыми** именами: `value`, `signs`, `numInputs`, `num`, `den`, `reset`.
Реальные имена — короткие: `a`, `y0`, `k`, `yk`, и они **не совпадают** с
читаемыми. (`xn` нет ни у одного класса каталога — это как раз пример
выдуманного имени.)

Эта документация писалась из общих знаний теории управления, а не из
фактических имён свойств SimInTech. **Не используйте её как источник имён.**

То же относится и к остальной документации `simintech-code` —
[`automation/com-api.md`](https://github.com/producedbysavant/simintech-code/blob/main/automation/com-api.md)
и [`tutorials/`](https://github.com/producedbysavant/simintech-code/tree/main/tutorials):
это описания работы с COM и уроки, а не реестр. Имя свойства ищите в
[`block_catalog.json`](https://github.com/producedbysavant/simintech-code/blob/main/simintech_api/data/block_catalog.json),
а не в тексте: в тексте правдоподобное имя выглядит настоящим, и ошибка видна
только по неизменившемуся расчёту.

## Если каталог неполон

Для класса вне каталога `get_block_params` покажет прочитанное и добавит
примечание «Класс '…' отсутствует в каталоге блоков — прочитаны только общие
свойства, имена не проверяются», а `set_block_param` — примечание к успешному
ответу, что имена проверить нечем. Это значит: значение **записано**, но имя не
проверено — убедитесь расчётом, что параметр влияет на модель, либо
отрегенерируйте каталог.

Обратный случай: класс в каталоге **есть**, но не прочиталось ни одно его
свойство — это отказ чтения COM, а не отсутствие класса. `get_block_params`
отвечает на него отказом (`isError`) и говорит об этом прямо, чтобы агент не
искал причину в установке каталога.

Другое дело — класс, который в каталоге **есть**, а имени в нём нет:
`set_block_param` отвечает отказом (`isError`) **до** записи в COM, в
сообщении — список известных имён. Тем же отказом (со списком задаваемых
параметров) заканчивается запись в вычисляемый параметр: COM её принимает, а
значение не меняется.

Осознанный обход — `allow_unknown=True` у `set_block_param` (и
`allow_unknown_props=True` у `add_block`): сверка с каталогом снимается, имя
пишется как есть. Применяйте, только когда уверены, что параметр существует
(например, каталог отстаёт от сборки), — иначе это запись в никуда без
единого сигнала.
