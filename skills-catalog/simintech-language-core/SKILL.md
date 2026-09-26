---
name: simintech-language-core
description: Use when writing SimInTech built-in language code (the "Язык программирования" block), or when a block cannot be created via COM CreateBlock. Pascal-like syntax, not C. Covers banned identifiers, comparison operators, and static arrays.
---

# Встроенный язык SimInTech

Справочник целиком: `https://github.com/producedbysavant/simintech-code/blob/main/` (`language/`, `blocks/`,
`patterns/`, `tutorials/`). Здесь — то, что чаще всего ломает работу агента.

**Официальная справка:**
[Язык программирования SimInTech](https://help.simintech.ru/11_yazyk_programmirovaniya/KEY_yazik_programmirovania.html)
— первоисточник по синтаксису и функциям.

## Когда нужен этот язык

Второй (после COM API) способ построения моделей: `createblock` /
`createmodel`. **Обязателен** для классов, которые не создаются через
`CreateBlock`:

- «Из памяти»
- «Порт выхода»

См. набор `UNSUPPORTED_COM_BLOCK_CLASSES` в
[`simintech_api/constants.py`](https://github.com/producedbysavant/simintech-code/blob/main/simintech_api/constants.py).
Синтаксис `файл.py:ИМЯ` якоря на символ в GitHub не работает — ссылка даёт 404.

Блоки библиотеки «Конечные автоматы» языку **не** требуются: они создаются
через `CreateBlock` — но только по полному имени записи с префиксом
«Конечные автоматы - » (например, `Конечные автоматы - Флаг входа в
состояние`); короткий заголовок с палитры (`Флаг входа в состояние`)
`CreateBlock` не принимает. Собрать автомат целиком через MCP всё равно нельзя
(состояния живут на внутренней странице карты) — см. скилл
`simintech-model-building`.

## Синтаксис — Pascal, не C

**Самая частая ошибка** — писать C-подобный код.

| Неправильно (C) | Правильно (SimInTech) |
|---|---|
| `==` | `=` |
| `!=` | `<>` |
| `&&` `\|\|` `!` | `and` `or` `not` |
| `{ }` как блок кода | `begin ... end;` |
| `//` в конце строки без `;` | обязательна `;` |

Полный набор операторов:

- арифметика: `+ - * /`, `div` (целочисленное), `mod` (остаток)
- сравнение: `= <> < > <= >=`
- логика: `and or not xor`
- биты: `shl shr`

## Функции языка — по реестру, не по догадке

Правдоподобные имена (`tan`, `asin`, `pow`) в языке **отсутствуют** — в
реестре справки таких записей нет. Существование имени проверяется по реестру
[`simintech_api/data/language_functions.json`](https://github.com/producedbysavant/simintech-code/blob/main/simintech_api/data/language_functions.json),
поиск по имени — `simintech_api.language.find_function`. Реестр отвечает, есть
ли такое имя, и даёт его назначение, но **не** даёт сигнатур — порядок
аргументов по нему не узнать; угаданное имя всплывёт только на кодогенерации.

## Область видимости и объявления

```simintech
input u: double;
output y: double;
const k = 2.5;
var counter: integer;

begin
    y = u * k;
end;
```

Правила:

- **Регистр не различается**: `Speed` и `speed` — одно и то же
- **У каждой переменной явный тип**: `var a: double, b: double;`
- **Запрещены имена `i`, `j`, `c`** — конфликтуют с авто-счётчиками транслятора
- `var` сохраняет значение между расчётными шагами
- Код исполняется на каждом расчётном шаге

## Типы

| Тип | Кодогенерация |
|---|---|
| `double`, `integer`, `boolean` | ✅ |
| `array`, `intarray` (только статические) | ✅ |
| `string` | ❌ не генерируется |

## Комментарии

`{ ... }` — блочный, `//` — до конца строки.

## Подводный камень: генерация Pascal-кода в `.inc`

Если строите Pascal-код строками в секции `beforecompile`, у языка выражений
**нет экранирования кавычек** — литерал `"` внутри строки закрывает её
досрочно, и остаток кода парсится как выражения. Симптом: «Символ X не может
быть использован» или «Ключевое слово if задано неверно» для символа, который
виден внутри строки.

Правило: одна строка — одно выражение; для встраиваемых Pascal-литералов
используйте `quotes = chr(34)`, для переводов строк — `CLRF`.
