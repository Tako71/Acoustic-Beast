# Топ 50 вопросов на собеседовании по Python

---

## 1. Что такое GIL (Global Interpreter Lock)?

GIL — это мьютекс в CPython, который гарантирует, что в каждый момент времени только один поток выполняет байт-код Python. Это сделано для защиты внутренних объектов интерпретатора от гонок данных при работе с памятью.

**Последствия:**
- Многопоточность не даёт прироста производительности для CPU-bound задач (вычисления).
- Для I/O-bound задач (сеть, диск) многопоточность работает нормально, т.к. GIL отпускается во время ожидания I/O.
- Для параллельных вычислений используют `multiprocessing` (отдельные процессы, каждый со своим GIL) или `concurrent.futures.ProcessPoolExecutor`.

```python
# I/O-bound — threading работает хорошо
import threading, requests

def fetch(url):
    requests.get(url)

threads = [threading.Thread(target=fetch, args=('https://example.com',)) for _ in range(10)]
for t in threads: t.start()
for t in threads: t.join()

# CPU-bound — нужен multiprocessing
from multiprocessing import Pool

def heavy(n):
    return sum(i*i for i in range(n))

with Pool(4) as p:
    results = p.map(heavy, [10**6]*4)
```

---

## 2. Разница между list и tuple

| | list | tuple |
|---|---|---|
| Мутабельность | Изменяемый | Неизменяемый |
| Синтаксис | `[1, 2, 3]` | `(1, 2, 3)` |
| Память | Больше | Меньше |
| Скорость | Медленнее | Быстрее |
| Хешируемость | Нет | Да (если элементы хешируемы) |
| Применение | Коллекции данных | Фиксированные структуры, ключи словаря |

```python
# tuple можно использовать как ключ словаря
d = {(1, 2): 'point'}

# list — нельзя
d = {[1, 2]: 'point'}  # TypeError: unhashable type: 'list'

# tuple быстрее создаётся
import timeit
timeit.timeit('(1,2,3)', number=10**7)   # ~0.07s
timeit.timeit('[1,2,3]', number=10**7)   # ~0.15s
```

---

## 3. Что такое декораторы?

Декоратор — это функция, которая принимает функцию и возвращает новую функцию с расширенным поведением. Это применение паттерна «Обёртка» (Wrapper).

```python
import functools

def logger(func):
    @functools.wraps(func)  # сохраняет __name__, __doc__ оригинальной функции
    def wrapper(*args, **kwargs):
        print(f'Вызов {func.__name__} с {args}, {kwargs}')
        result = func(*args, **kwargs)
        print(f'Результат: {result}')
        return result
    return wrapper

@logger
def add(a, b):
    return a + b

add(2, 3)
# Вызов add с (2, 3), {}
# Результат: 5
```

**Декоратор с параметрами:**
```python
def repeat(n):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(n):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(3)
def hello():
    print('Hello')
```

---

## 4. Генераторы и итераторы

**Итератор** — объект с методами `__iter__` и `__next__`. Возвращает элементы по одному.

**Генератор** — функция с `yield`, автоматически реализующая протокол итератора. Значения вычисляются лениво (lazy evaluation).

```python
# Генераторная функция
def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

gen = fibonacci()
print([next(gen) for _ in range(8)])  # [0, 1, 1, 2, 3, 5, 8, 13]

# Генераторное выражение (экономит память)
squares = (x**2 for x in range(10**6))  # не создаёт список в памяти

# Разница: список vs генератор
import sys
lst = [x**2 for x in range(10**6)]
gen = (x**2 for x in range(10**6))
print(sys.getsizeof(lst))  # ~8 МБ
print(sys.getsizeof(gen))  # 120 байт
```

**yield from** — делегирование генератору:
```python
def chain(*iterables):
    for it in iterables:
        yield from it
```

---

## 5. Управление памятью в Python

Python использует два механизма:

1. **Подсчёт ссылок (Reference Counting)** — каждый объект хранит счётчик ссылок. Когда он падает до 0, память освобождается немедленно.

2. **Циклический сборщик мусора (Cyclic GC)** — обнаруживает и удаляет объекты с циклическими ссылками, которые не может поймать подсчёт ссылок.

```python
import sys, gc

a = []
print(sys.getrefcount(a))  # 2 (a + аргумент getrefcount)

b = a
print(sys.getrefcount(a))  # 3

del b
print(sys.getrefcount(a))  # 2

# Циклическая ссылка
class Node:
    def __init__(self):
        self.ref = None

n1 = Node()
n2 = Node()
n1.ref = n2
n2.ref = n1
del n1, n2
# Подсчёт ссылок не поможет — нужен cyclic GC
gc.collect()  # принудительный сбор
```

Python также использует **memory pools** (pymalloc) для мелких объектов (<= 512 байт) — аллокатор работает на уровне арен и пулов, избегая частых вызовов `malloc`.

---

## 6. Разница между == и is

- `==` сравнивает **значения** (вызывает `__eq__`)
- `is` сравнивает **идентичность объектов** (один и тот же объект в памяти, сравнивает `id()`)

```python
a = [1, 2, 3]
b = [1, 2, 3]
print(a == b)  # True  — одинаковые значения
print(a is b)  # False — разные объекты

# Интернирование малых целых [-5, 256]
x = 256
y = 256
print(x is y)  # True — один объект (кеш CPython)

x = 257
y = 257
print(x is y)  # False — разные объекты (за пределами кеша)

# Правило: используй is только для сравнения с None, True, False
if value is None:
    ...
```

---

## 7. Множественное наследование и MRO

MRO (Method Resolution Order) — порядок, в котором Python ищет метод в иерархии классов. Используется алгоритм **C3-линеаризации**.

```python
class A:
    def method(self): print('A')

class B(A):
    def method(self): print('B')

class C(A):
    def method(self): print('C')

class D(B, C):
    pass

d = D()
d.method()  # B — найден в B первым

print(D.__mro__)
# (<class 'D'>, <class 'B'>, <class 'C'>, <class 'A'>, <class 'object'>)

# super() следует MRO
class B(A):
    def method(self):
        super().method()  # вызовет следующий в MRO, не обязательно A
        print('B')
```

---

## 8. Контекстные менеджеры (with)

Контекстный менеджер реализует методы `__enter__` и `__exit__`. Гарантирует выполнение кода очистки даже при исключениях.

```python
class ManagedFile:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.file = open(self.path)
        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()
        return False  # False — не подавляем исключение

with ManagedFile('data.txt') as f:
    data = f.read()

# Через contextlib
from contextlib import contextmanager

@contextmanager
def managed_file(path):
    f = open(path)
    try:
        yield f
    finally:
        f.close()
```

---

## 9. *args и **kwargs

- `*args` — принимает произвольное количество позиционных аргументов как кортеж
- `**kwargs` — принимает произвольное количество именованных аргументов как словарь

```python
def func(*args, **kwargs):
    print(args)   # tuple
    print(kwargs) # dict

func(1, 2, 3, name='Alice', age=30)
# (1, 2, 3)
# {'name': 'Alice', 'age': 30}

# Распаковка при вызове
def add(a, b, c):
    return a + b + c

nums = [1, 2, 3]
add(*nums)  # эквивалентно add(1, 2, 3)

params = {'a': 1, 'b': 2, 'c': 3}
add(**params)
```

---

## 10. List/Dict/Set Comprehensions

```python
# List comprehension
squares = [x**2 for x in range(10) if x % 2 == 0]

# Dict comprehension
word_len = {word: len(word) for word in ['apple', 'banana', 'cherry']}

# Set comprehension
unique_lengths = {len(word) for word in ['apple', 'banana', 'cherry']}

# Вложенные
matrix = [[1,2,3],[4,5,6],[7,8,9]]
flat = [x for row in matrix for x in row]

# Walrus operator := (Python 3.8+)
results = [y for x in range(10) if (y := x**2) > 20]
```

---

## 11. Разница между copy и deepcopy

```python
import copy

original = [[1, 2, 3], [4, 5, 6]]

shallow = copy.copy(original)      # новый список, но те же вложенные объекты
deep = copy.deepcopy(original)     # полностью независимая копия

original[0].append(99)
print(shallow[0])  # [1, 2, 3, 99] — затронуто (тот же объект)
print(deep[0])     # [1, 2, 3]     — не затронуто

# Для простых (плоских) объектов разницы нет:
a = [1, 2, 3]
b = a.copy()  # эквивалентно shallow copy для плоского списка
```

---

## 12. Что такое замыкание (closure)?

Замыкание — функция, которая запоминает переменные из окружающей области видимости, даже после того, как та область завершила выполнение.

```python
def make_multiplier(n):
    def multiplier(x):
        return x * n  # n — свободная переменная, захвачена из внешней функции
    return multiplier

double = make_multiplier(2)
triple = make_multiplier(3)

print(double(5))  # 10
print(triple(5))  # 15

# Просмотр захваченных переменных
print(double.__closure__[0].cell_contents)  # 2

# Частая ловушка с циклами:
funcs = [lambda x: x * i for i in range(3)]
print([f(2) for f in funcs])  # [4, 4, 4] — все захватили последнее i=2

# Исправление:
funcs = [lambda x, i=i: x * i for i in range(3)]
print([f(2) for f in funcs])  # [0, 2, 4]
```

---

## 13. Что такое метаклассы?

Метакласс — это класс классов. Определяет, как создаётся класс. По умолчанию все классы создаются метаклассом `type`.

```python
# type(name, bases, dict) — создаёт класс динамически
MyClass = type('MyClass', (object,), {'greet': lambda self: 'Hello'})

# Собственный метакласс
class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class Database(metaclass=SingletonMeta):
    def __init__(self):
        self.connection = 'connected'

db1 = Database()
db2 = Database()
print(db1 is db2)  # True — один объект
```

Метаклассы используются во фреймворках (Django ORM, SQLAlchemy) для магии моделей.

---

## 14. Обработка исключений

```python
try:
    result = 10 / 0
except ZeroDivisionError as e:
    print(f'Ошибка: {e}')
except (TypeError, ValueError) as e:
    print(f'Другая ошибка: {e}')
else:
    print('Успех')        # выполняется если исключения не было
finally:
    print('Всегда')       # выполняется всегда

# Своё исключение
class InsufficientFundsError(ValueError):
    def __init__(self, amount, balance):
        self.amount = amount
        self.balance = balance
        super().__init__(f'Недостаточно средств: нужно {amount}, есть {balance}')

# raise from — цепочка исключений
try:
    int('abc')
except ValueError as e:
    raise RuntimeError('Ошибка конвертации') from e
```

---

## 15. @staticmethod vs @classmethod vs instance method

```python
class MyClass:
    class_var = 0

    def instance_method(self):
        # Имеет доступ к self (экземпляру) и cls через type(self)
        return self.class_var

    @classmethod
    def class_method(cls):
        # Получает класс, не экземпляр. Используется как фабричный метод
        return cls()

    @staticmethod
    def static_method():
        # Не получает ни self, ни cls. Просто функция в пространстве имён класса
        return 'static'

# classmethod как фабрика
class Date:
    def __init__(self, year, month, day):
        self.year, self.month, self.day = year, month, day

    @classmethod
    def from_string(cls, date_string):
        year, month, day = map(int, date_string.split('-'))
        return cls(year, month, day)

d = Date.from_string('2024-01-15')
```

---

## 16. Что такое property?

`property` — дескриптор, позволяющий управлять доступом к атрибутам через методы (getter, setter, deleter) с синтаксисом атрибута.

```python
class Temperature:
    def __init__(self, celsius=0):
        self._celsius = celsius

    @property
    def celsius(self):
        return self._celsius

    @celsius.setter
    def celsius(self, value):
        if value < -273.15:
            raise ValueError('Температура ниже абсолютного нуля')
        self._celsius = value

    @property
    def fahrenheit(self):
        return self._celsius * 9/5 + 32

t = Temperature(25)
print(t.celsius)     # 25
print(t.fahrenheit)  # 77.0
t.celsius = -300     # ValueError
```

---

## 17. Mutable vs Immutable

**Immutable (неизменяемые):** `int`, `float`, `str`, `tuple`, `frozenset`, `bytes`
**Mutable (изменяемые):** `list`, `dict`, `set`, `bytearray`, пользовательские объекты

```python
# Аргументы по умолчанию — классическая ловушка
def append_to(element, lst=[]):  # [] создаётся один раз при определении функции!
    lst.append(element)
    return lst

print(append_to(1))  # [1]
print(append_to(2))  # [1, 2] — а не [2]!

# Правильно:
def append_to(element, lst=None):
    if lst is None:
        lst = []
    lst.append(element)
    return lst

# str неизменяем — каждая конкатенация создаёт новый объект
s = ''
for i in range(1000):
    s += str(i)  # O(n²) — медленно

# Правильно:
s = ''.join(str(i) for i in range(1000))  # O(n)
```

---

## 18. Разница между __str__ и __repr__

- `__repr__` — строка для разработчика. Должна однозначно идентифицировать объект. Вызывается в консоли, при отладке, в `repr()`.
- `__str__` — строка для пользователя. Вызывается в `print()`, `str()`.

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return f'Point({self.x!r}, {self.y!r})'  # можно воссоздать объект

    def __str__(self):
        return f'({self.x}, {self.y})'  # читаемо для пользователя

p = Point(1, 2)
print(repr(p))  # Point(1, 2)
print(str(p))   # (1, 2)
print(p)        # (1, 2) — вызывает __str__

# Если __str__ не определён, используется __repr__
```

---

## 19. Как работает import?

При `import module` Python:
1. Ищет модуль в `sys.modules` (кеш) — если есть, возвращает готовый объект
2. Ищет файл в `sys.path`
3. Компилирует в байт-код (`.pyc` в `__pycache__`)
4. Выполняет код модуля
5. Добавляет в `sys.modules`

```python
import sys

# Просмотр пути поиска
print(sys.path)

# Импорт уже закеширован
import os
import os  # не выполняется повторно — берётся из sys.modules

# Принудительная перезагрузка
import importlib
importlib.reload(os)

# Относительный импорт (внутри пакета)
from . import sibling_module
from ..parent import something
```

---

## 20. Что такое duck typing?

«Если это ходит как утка и крякает как утка — это утка». Python проверяет не тип объекта, а наличие нужных методов/атрибутов.

```python
class Dog:
    def speak(self): return 'Woof'

class Cat:
    def speak(self): return 'Meow'

class Duck:
    def speak(self): return 'Quack'

def make_speak(animal):
    return animal.speak()  # не важно, какого типа animal

for animal in [Dog(), Cat(), Duck()]:
    print(make_speak(animal))

# EAFP (Easier to Ask Forgiveness than Permission) — питонический подход
try:
    value = obj.method()
except AttributeError:
    value = default

# vs LBYL (Look Before You Leap) — менее питонический
if hasattr(obj, 'method'):
    value = obj.method()
```

---

## 21. Разница между threading и multiprocessing

| | threading | multiprocessing |
|---|---|---|
| GIL | Один на процесс | Каждый процесс свой |
| Память | Общая | Отдельная |
| Лучше для | I/O-bound | CPU-bound |
| Создание | Быстрее | Медленнее |
| Коммуникация | Общие объекты | Queue, Pipe |

```python
# threading — для I/O
from threading import Thread
import time

def download(url):
    time.sleep(1)  # имитация загрузки

threads = [Thread(target=download, args=(f'url{i}',)) for i in range(5)]
for t in threads: t.start()
for t in threads: t.join()  # 1 секунда вместо 5

# multiprocessing — для CPU
from multiprocessing import Pool

def compute(n):
    return sum(i**2 for i in range(n))

with Pool(4) as pool:
    results = pool.map(compute, [10**6]*4)
```

---

## 22. async/await и asyncio

asyncio — однопоточный конкурентный I/O через event loop. Корутины выполняются совместно (cooperative multitasking), уступая управление в точках `await`.

```python
import asyncio
import aiohttp

async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

async def main():
    urls = ['https://example.com'] * 5
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url) for url in urls]
        results = await asyncio.gather(*tasks)  # конкурентно
    return results

asyncio.run(main())

# asyncio vs threading:
# asyncio — однопоток, нет гонок данных, но только для async-совместимых библиотек
# threading — многопоток, нужны блокировки, работает с любыми библиотеками
```

---

## 23. Что такое __slots__?

`__slots__` ограничивает набор атрибутов экземпляра, убирая `__dict__`. Экономит память и ускоряет доступ к атрибутам.

```python
class WithDict:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class WithSlots:
    __slots__ = ('x', 'y')
    def __init__(self, x, y):
        self.x = x
        self.y = y

import sys
a = WithDict(1, 2)
b = WithSlots(1, 2)
print(sys.getsizeof(a.__dict__))  # 232 байт
# b не имеет __dict__ — экономия памяти

# Ограничение: нельзя добавить произвольный атрибут
b.z = 3  # AttributeError

# При наследовании: если родитель без __slots__ — экономии не будет
```

---

## 24. Генераторы с send() и двусторонняя коммуникация

```python
def accumulator():
    total = 0
    while True:
        value = yield total  # yield возвращает total, получает value через send()
        if value is None:
            break
        total += value

gen = accumulator()
next(gen)           # запускаем до первого yield
print(gen.send(10)) # 10
print(gen.send(20)) # 30
print(gen.send(5))  # 35
```

---

## 25. LEGB — правило области видимости

Python ищет имена в порядке: **L**ocal → **E**nclosing → **G**lobal → **B**uilt-in

```python
x = 'global'

def outer():
    x = 'enclosing'

    def inner():
        x = 'local'
        print(x)  # local

    inner()
    print(x)  # enclosing

outer()
print(x)  # global

# global и nonlocal для изменения внешних переменных
counter = 0

def increment():
    global counter
    counter += 1

def make_counter():
    count = 0
    def inc():
        nonlocal count
        count += 1
        return count
    return inc
```

---

## 26. Дескрипторы

Дескриптор — объект, реализующий `__get__`, `__set__`, `__delete__`. Именно на них построены `property`, `classmethod`, `staticmethod`.

```python
class Validator:
    def __set_name__(self, owner, name):
        self.name = name
        self.private = f'_{name}'

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.private, None)

    def __set__(self, obj, value):
        if not isinstance(value, (int, float)):
            raise TypeError(f'{self.name} должен быть числом')
        if value < 0:
            raise ValueError(f'{self.name} должен быть >= 0')
        setattr(obj, self.private, value)

class Product:
    price = Validator()
    quantity = Validator()

    def __init__(self, price, quantity):
        self.price = price
        self.quantity = quantity

p = Product(10.5, 3)
p.price = -1  # ValueError
```

---

## 27. __init__ vs __new__

- `__new__` — создаёт экземпляр (статический метод, вызывается первым)
- `__init__` — инициализирует уже созданный экземпляр

```python
class Singleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, value):
        self.value = value

a = Singleton(1)
b = Singleton(2)
print(a is b)    # True
print(a.value)   # 2 — __init__ вызван дважды на том же объекте

# __new__ нужен для иммутабельных типов
class PositiveInt(int):
    def __new__(cls, value):
        if value <= 0:
            raise ValueError('Должно быть положительным')
        return super().__new__(cls, value)
```

---

## 28. Абстрактные классы (ABC)

```python
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self) -> float:
        pass

    @abstractmethod
    def perimeter(self) -> float:
        pass

    def describe(self):
        return f'Площадь: {self.area():.2f}, периметр: {self.perimeter():.2f}'

class Circle(Shape):
    def __init__(self, radius):
        self.radius = radius

    def area(self):
        import math
        return math.pi * self.radius ** 2

    def perimeter(self):
        import math
        return 2 * math.pi * self.radius

# Shape() — TypeError: Can't instantiate abstract class
c = Circle(5)
print(c.describe())
```

---

## 29. functools: wraps, lru_cache, partial

```python
import functools

# lru_cache — мемоизация
@functools.lru_cache(maxsize=128)
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(50))               # мгновенно
print(fibonacci.cache_info())      # hits, misses, maxsize, currsize

# partial — частичное применение
def power(base, exp):
    return base ** exp

square = functools.partial(power, exp=2)
cube = functools.partial(power, exp=3)

print(square(5))  # 25
print(cube(3))    # 27

# reduce
from functools import reduce
product = reduce(lambda a, b: a * b, [1, 2, 3, 4, 5])  # 120
```

---

## 30. Коллекции из collections

```python
from collections import defaultdict, Counter, OrderedDict, namedtuple, deque

# defaultdict
graph = defaultdict(list)
graph['A'].append('B')  # не нужно проверять наличие ключа

# Counter
words = ['apple', 'banana', 'apple', 'cherry', 'banana', 'apple']
count = Counter(words)
print(count.most_common(2))  # [('apple', 3), ('banana', 2)]

# namedtuple
Point = namedtuple('Point', ['x', 'y'])
p = Point(1, 2)
print(p.x, p.y)  # иммутабельный, с именованными полями

# deque — двусторонняя очередь O(1) с обоих концов
dq = deque([1, 2, 3], maxlen=5)
dq.appendleft(0)
dq.rotate(1)
```

---

## 31. Type hints и typing

```python
from typing import Optional, Union, List, Dict, Tuple, Callable, TypeVar

def greet(name: str) -> str:
    return f'Hello, {name}'

def process(data: Optional[List[int]] = None) -> Dict[str, int]:
    if data is None:
        data = []
    return {'sum': sum(data), 'count': len(data)}

# TypeVar для обобщённых функций
T = TypeVar('T')

def first(lst: List[T]) -> Optional[T]:
    return lst[0] if lst else None

# Python 3.10+ — union через |
def func(x: int | str | None) -> int | None:
    ...

# Protocol вместо ABC (structural subtyping)
from typing import Protocol

class Drawable(Protocol):
    def draw(self) -> None: ...

def render(obj: Drawable) -> None:
    obj.draw()
```

---

## 32. dataclasses

```python
from dataclasses import dataclass, field, asdict
from typing import List

@dataclass
class Point:
    x: float
    y: float
    z: float = 0.0  # значение по умолчанию

    def distance_to_origin(self):
        return (self.x**2 + self.y**2 + self.z**2) ** 0.5

@dataclass(frozen=True)  # иммутабельный — можно хешировать
class Config:
    host: str
    port: int = 8000

@dataclass
class Team:
    name: str
    members: List[str] = field(default_factory=list)  # изменяемый default

p = Point(1.0, 2.0)
print(asdict(p))  # {'x': 1.0, 'y': 2.0, 'z': 0.0}
print(p)          # Point(x=1.0, y=2.0, z=0.0) — __repr__ бесплатно
```

---

## 33. Как работает хеширование?

Хеш — целое число, вычисляемое по значению объекта. Используется в `dict` и `set` для O(1) поиска.

```python
# Правило: если a == b, то hash(a) == hash(b)
# Обратное неверно (коллизии)

print(hash(42))      # 42
print(hash('hello')) # зависит от запуска (seed рандомный с Python 3.3)
print(hash((1, 2)))  # хешируем tuple

# Собственный __hash__
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))

# Если определить __eq__ без __hash__ — объект становится нехешируемым
# dict использует hash для определения корзины, затем == для разрешения коллизий
```

---

## 34. Итерационный протокол (__iter__ и __next__)

```python
class Range:
    def __init__(self, start, stop, step=1):
        self.current = start
        self.stop = stop
        self.step = step

    def __iter__(self):
        return self  # объект сам является итератором

    def __next__(self):
        if self.current >= self.stop:
            raise StopIteration
        value = self.current
        self.current += self.step
        return value

for x in Range(0, 10, 2):
    print(x)  # 0 2 4 6 8

# Разница итерабельного и итератора:
# Итерабельный — имеет __iter__, возвращает итератор (list, tuple, str)
# Итератор — имеет __iter__ и __next__, помнит позицию

lst = [1, 2, 3]      # итерабельный
it = iter(lst)       # итератор
print(next(it))      # 1
print(next(it))      # 2
```

---

## 35. Что такое weakref?

Слабая ссылка — ссылка на объект, которая не увеличивает счётчик ссылок. Объект может быть удалён GC, даже если на него есть слабые ссылки.

```python
import weakref

class BigObject:
    def __init__(self, data):
        self.data = data
    def __del__(self):
        print('Удалён')

obj = BigObject([1]*1000)
weak = weakref.ref(obj)

print(weak())   # <BigObject object>  — объект жив
del obj
print(weak())   # None  — объект удалён GC

# WeakValueDictionary — кеш без удержания объектов
cache = weakref.WeakValueDictionary()
o = BigObject([1])
cache['key'] = o
del o
# cache['key'] автоматически исчезнет
```

---

## 36. Enumerate, zip, map, filter

```python
# enumerate — индекс + значение
fruits = ['apple', 'banana', 'cherry']
for i, fruit in enumerate(fruits, start=1):
    print(f'{i}. {fruit}')

# zip — объединение итерабельных
names = ['Alice', 'Bob']
scores = [95, 87]
for name, score in zip(names, scores):
    print(f'{name}: {score}')

# zip_longest из itertools
from itertools import zip_longest
list(zip_longest([1,2,3], [4,5], fillvalue=0))  # [(1,4),(2,5),(3,0)]

# map — применяет функцию (ленивый)
squares = list(map(lambda x: x**2, range(5)))

# filter — фильтрует (ленивый)
evens = list(filter(lambda x: x % 2 == 0, range(10)))

# Предпочтительнее comprehensions:
squares = [x**2 for x in range(5)]
evens = [x for x in range(10) if x % 2 == 0]
```

---

## 37. Сортировка: sort() vs sorted()

```python
# sorted() — возвращает новый список, работает с любым итерабельным
nums = [3, 1, 4, 1, 5, 9]
sorted_nums = sorted(nums)       # новый список
print(nums)                      # [3, 1, 4, 1, 5, 9] — не изменён

# sort() — сортирует на месте, только для list
nums.sort()
print(nums)                      # [1, 1, 3, 4, 5, 9]

# key — функция для сравнения
words = ['banana', 'Apple', 'cherry']
sorted(words, key=str.lower)     # ['Apple', 'banana', 'cherry']

# Сортировка по нескольким полям
people = [('Alice', 30), ('Bob', 25), ('Charlie', 30)]
sorted(people, key=lambda x: (x[1], x[0]))  # по возрасту, затем по имени

# Стабильная сортировка — порядок равных элементов сохраняется
from operator import attrgetter, itemgetter
sorted(people, key=itemgetter(1))
```

---

## 38. Байты: bytes vs bytearray vs str

```python
# str — Unicode строка (Python 3)
s = 'Привет'
print(type(s))   # <class 'str'>

# bytes — неизменяемая последовательность байт
b = b'Hello'
b2 = 'Привет'.encode('utf-8')   # str -> bytes
print(b2)                        # b'\xd0\x9f\xd1\x80...'

# bytearray — изменяемый bytes
ba = bytearray(b'Hello')
ba[0] = 104  # 'h'
print(ba)    # bytearray(b'hello')

# Декодирование
print(b2.decode('utf-8'))  # 'Привет'

# Когда bytes важны: работа с сетью, файлами, бинарными данными
with open('image.png', 'rb') as f:
    data = f.read()  # bytes
```

---

## 39. Профилирование и оптимизация

```python
# timeit — измерение времени
import timeit
timeit.timeit('"-".join(str(n) for n in range(100))', number=10000)

# cProfile — профилирование функций
import cProfile
cProfile.run('my_function()')

# line_profiler (pip install line_profiler)
# @profile decorator + kernprof -l -v script.py

# memory_profiler (pip install memory_profiler)
from memory_profiler import profile

@profile
def my_func():
    a = [1] * 10**6

# Встроенные инструменты оптимизации:
# - list comprehensions быстрее for+append
# - local переменные быстрее global
# - join() быстрее конкатенации строк
# - set для поиска вместо list (O(1) vs O(n))
```

---

## 40. Паттерны проектирования в Python

```python
# Observer
class EventEmitter:
    def __init__(self):
        self._listeners = defaultdict(list)

    def on(self, event, callback):
        self._listeners[event].append(callback)

    def emit(self, event, *args):
        for cb in self._listeners[event]:
            cb(*args)

# Strategy
from abc import ABC, abstractmethod

class SortStrategy(ABC):
    @abstractmethod
    def sort(self, data): pass

class QuickSort(SortStrategy):
    def sort(self, data): return sorted(data)

class Sorter:
    def __init__(self, strategy: SortStrategy):
        self.strategy = strategy

    def sort(self, data):
        return self.strategy.sort(data)

# Factory
class AnimalFactory:
    _registry = {}

    @classmethod
    def register(cls, name):
        def decorator(animal_cls):
            cls._registry[name] = animal_cls
            return animal_cls
        return decorator

    @classmethod
    def create(cls, name):
        return cls._registry[name]()
```

---

## 41. Работа с файлами и os/pathlib

```python
from pathlib import Path

# pathlib — современный способ (Python 3.4+)
p = Path('/home/user/documents')
config = p / 'config.json'      # объединение путей

print(config.exists())
print(config.suffix)            # '.json'
print(config.stem)              # 'config'
print(config.parent)            # /home/user/documents

# Glob
py_files = list(Path('.').glob('**/*.py'))

# Чтение/запись
text = config.read_text(encoding='utf-8')
config.write_text('{}', encoding='utf-8')

# os для системных операций
import os
os.environ.get('HOME')
os.getcwd()
os.listdir('.')
```

---

## 42. Что такое __all__?

`__all__` — список имён, экспортируемых при `from module import *`. Также служит документацией публичного API.

```python
# mymodule.py
__all__ = ['PublicClass', 'public_function']

class PublicClass:
    pass

def public_function():
    pass

def _private_function():  # не экспортируется
    pass

# При from mymodule import * — импортируется только то, что в __all__
# При import mymodule — доступно всё
```

---

## 43. Exception chaining и трейсбек

```python
import traceback

# Цепочка исключений
try:
    int('abc')
except ValueError as original:
    raise RuntimeError('Conversion failed') from original
    # В трейсбеке будет: "The above exception was the cause..."

# Подавление контекста
raise RuntimeError('New error') from None  # скрывает оригинальное

# Программное создание трейсбека
try:
    1/0
except:
    tb = traceback.format_exc()  # строка с трейсбеком
    print(tb)

# ExceptionGroup (Python 3.11+)
try:
    raise ExceptionGroup('multiple', [ValueError('v'), TypeError('t')])
except* ValueError as eg:
    print('Caught ValueErrors')
```

---

## 44. Walrus operator := (Python 3.8+)

```python
# Присваивание внутри выражения
import re

# Без walrus:
match = re.search(r'\d+', text)
if match:
    print(match.group())

# С walrus:
if match := re.search(r'\d+', text):
    print(match.group())

# В while
while chunk := file.read(8192):
    process(chunk)

# В comprehension
results = [y for x in data if (y := process(x)) is not None]
```

---

## 45. Enum

```python
from enum import Enum, IntEnum, auto, Flag

class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3

print(Color.RED)          # Color.RED
print(Color.RED.value)    # 1
print(Color.RED.name)     # 'RED'
print(Color(2))           # Color.GREEN

# auto() — автоматические значения
class Direction(Enum):
    NORTH = auto()
    SOUTH = auto()
    EAST = auto()
    WEST = auto()

# Flag — битовые флаги
class Permission(Flag):
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()
    ALL = READ | WRITE | EXECUTE

perm = Permission.READ | Permission.WRITE
print(Permission.READ in perm)  # True
```

---

## 46. Протокол контекстного менеджера через contextlib

```python
from contextlib import contextmanager, asynccontextmanager, suppress

# suppress — подавление исключений
with suppress(FileNotFoundError):
    open('nonexistent.txt')

# contextmanager
@contextmanager
def timer():
    import time
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(f'Время: {elapsed:.3f}с')

with timer():
    sum(range(10**7))

# asynccontextmanager
@asynccontextmanager
async def managed_connection():
    conn = await create_connection()
    try:
        yield conn
    finally:
        await conn.close()
```

---

## 47. Что такое __call__?

`__call__` позволяет вызывать экземпляр класса как функцию.

```python
class Multiplier:
    def __init__(self, factor):
        self.factor = factor

    def __call__(self, x):
        return x * self.factor

double = Multiplier(2)
print(double(5))   # 10
print(callable(double))  # True

# Применение: stateful декораторы
class CountCalls:
    def __init__(self, func):
        self.func = func
        self.count = 0

    def __call__(self, *args, **kwargs):
        self.count += 1
        return self.func(*args, **kwargs)

@CountCalls
def say_hello():
    print('Hello')

say_hello()
say_hello()
print(say_hello.count)  # 2
```

---

## 48. Packing и unpacking

```python
# Распаковка
first, *rest = [1, 2, 3, 4, 5]
print(first)  # 1
print(rest)   # [2, 3, 4, 5]

*init, last = [1, 2, 3, 4, 5]
a, *b, c = [1, 2, 3, 4, 5]

# Обмен переменных
a, b = 1, 2
a, b = b, a

# Распаковка вложенных структур
(a, b), c = (1, 2), 3

# В функциях
def func(a, b, c):
    return a + b + c

args = (1, 2, 3)
func(*args)

# Объединение словарей (Python 3.9+)
d1 = {'a': 1}
d2 = {'b': 2}
merged = d1 | d2         # {'a': 1, 'b': 2}
merged = {**d1, **d2}   # то же самое
```

---

## 49. Тестирование: unittest и pytest

```python
import unittest
from unittest.mock import MagicMock, patch

class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = Calculator()

    def test_add(self):
        self.assertEqual(self.calc.add(2, 3), 5)

    def test_divide_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            self.calc.divide(1, 0)

    @patch('mymodule.requests.get')
    def test_api_call(self, mock_get):
        mock_get.return_value.json.return_value = {'status': 'ok'}
        result = fetch_data('https://api.example.com')
        self.assertEqual(result['status'], 'ok')
        mock_get.assert_called_once()

# pytest — более современный подход
def test_add():
    assert add(2, 3) == 5

import pytest

@pytest.fixture
def db():
    connection = create_test_db()
    yield connection
    connection.close()

@pytest.mark.parametrize('a,b,expected', [(1,2,3),(0,0,0),(-1,1,0)])
def test_add_param(a, b, expected):
    assert add(a, b) == expected
```

---

## 50. Что нового в современном Python (3.10–3.12)

```python
# Match statement (3.10) — структурное сопоставление с образцом
command = ('move', 10, 20)

match command:
    case ('move', x, y):
        print(f'Движение в ({x}, {y})')
    case ('quit',):
        print('Выход')
    case _:
        print('Неизвестная команда')

# match с типами и условиями
match point:
    case Point(x=0, y=0):
        print('Начало координат')
    case Point(x=x, y=0):
        print(f'На оси X: {x}')
    case Point(x=0, y=y):
        print(f'На оси Y: {y}')

# Exception groups (3.11)
try:
    raise ExceptionGroup('errors', [ValueError('v'), TypeError('t')])
except* ValueError:
    print('ValueError обработан')

# tomllib (3.11) — встроенный парсер TOML
import tomllib
with open('pyproject.toml', 'rb') as f:
    config = tomllib.load(f)

# TypeVarTuple и Unpack (3.11) — обобщения для tuple
# f-строки без ограничений (3.12) — можно вкладывать кавычки
name = 'world'
print(f"{'hello'} {name}")
```
