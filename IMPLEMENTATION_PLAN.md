# План реализации веб-приложения "Acoustic Beast"
### Веб-приложение для анализа и расчета уровня шума в производственных помещениях
**Стек: Python 3.11 + Django 4.2 + PostgreSQL + Bootstrap 5**

---

## 1. Описание проекта

Веб-приложение **Acoustic Beast** предназначено для расчёта и анализа уровня шума в производственных помещениях согласно ГОСТ ISO 9612-2016. Позволяет сотрудникам отдела охраны труда вводить данные замеров, выбирать стратегию расчёта и получать детализированный отчёт с рекомендациями.

---

## 2. Функциональные требования (из ВКР и Tilda-сайта)

### Страницы сайта (навигация)
| # | Страница | URL | Доступ |
|---|----------|-----|--------|
| 1 | Главная | `/` | Все |
| 2 | Документация | `/docs/` | Все |
| 3 | FAQ | `/faq/` | Все |
| 4 | Авторизация / Регистрация | `/login/`, `/register/` | Анонимы |
| 5 | Расчёт (форма ввода) | `/calculate/` | Авторизованные |
| 6 | Результат / Отчёт | `/result/<id>/` | Авторизованные |
| 7 | Скачать PDF | `/result/<id>/pdf/` | Авторизованные |
| 8 | История расчётов | `/history/` | Авторизованные |
| 9 | Панель администратора | `/admin/` | Администраторы |
| 10 | 404 страница | — | Все |

### Ключевые функции
- Три стратегии расчёта по ГОСТ ISO 9612-2016
- Ввод данных по точкам замера (динамическое добавление полей)
- Расчёт эквивалентного уровня шума по математическим формулам
- Сравнение с нормативами (СанПиН 2.2.4.3359-16)
- График уровней шума по точкам (matplotlib / Chart.js)
- Генерация отчёта с рекомендациями
- Экспорт отчёта в PDF (reportlab)
- История всех расчётов пользователя
- Роли пользователей: администратор / пользователь
- Страница документации с нормативными актами

---

## 3. Структура проекта Django

```
acoustic_beast/               ← корень проекта
├── manage.py
├── requirements.txt
├── .env                      ← секреты (не в git)
├── acoustic_beast/           ← Django-проект (settings, urls, wsgi)
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── noise/                    ← основное приложение
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   ├── urls.py
│   ├── admin.py
│   ├── calculators.py        ← математические формулы
│   ├── pdf_generator.py      ← генерация PDF
│   └── templatetags/
│       └── noise_extras.py
├── accounts/                 ← приложение авторизации
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   └── urls.py
├── templates/
│   ├── base.html             ← базовый шаблон (навбар, футер)
│   ├── index.html            ← главная страница
│   ├── docs.html             ← документация
│   ├── faq.html              ← FAQ
│   ├── noise/
│   │   ├── calculate.html    ← форма расчёта (мастер)
│   │   ├── result.html       ← отчёт с графиком
│   │   └── history.html      ← история расчётов
│   └── accounts/
│       ├── login.html
│       └── register.html
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── calculate.js      ← динамические поля точек замера
│   └── img/
│       └── hero-bg.jpg       ← фоновое фото шумомера
└── media/
    ├── reports/pdf/          ← сгенерированные PDF
    └── charts/               ← графики PNG
```

---

## 4. Модели базы данных (5 таблиц, ~17 полей)

### 4.1 Таблица `NoiseMeasurement` — запись о замере
```python
class NoiseMeasurement(models.Model):
    user         = ForeignKey(User)          # кто создал
    company      = CharField(max_length=255) # название компании
    location     = CharField(max_length=255) # место замера
    strategy     = CharField(choices=STRATEGY_CHOICES) # стратегия расчёта
    num_points   = IntegerField()            # кол-во точек
    created_at   = DateTimeField(auto_now_add=True)
    notes        = TextField(blank=True)     # доп. примечания
```

### 4.2 Таблица `MeasurementPoint` — отдельная точка замера
```python
class MeasurementPoint(models.Model):
    measurement  = ForeignKey(NoiseMeasurement, related_name='points')
    point_number = IntegerField()            # номер точки
    noise_db     = FloatField()              # уровень шума, дБ
    duration_min = FloatField(null=True)     # длительность (для стратегий 1, 2)
```

### 4.3 Таблица `NoiseReport` — результат расчёта
```python
class NoiseReport(models.Model):
    measurement       = OneToOneField(NoiseMeasurement)
    avg_noise         = FloatField()         # эквивалентный уровень, дБ
    std_deviation     = FloatField()         # стандартное отклонение
    max_noise         = FloatField()         # максимальное значение
    min_noise         = FloatField()         # минимальное значение
    norm_value        = FloatField()         # нормативное значение, дБ
    exceeds_norm      = BooleanField()       # превышение нормы
    recommendations   = TextField()          # текстовые рекомендации
    chart_path        = CharField()          # путь к PNG-графику
    pdf_path          = CharField()          # путь к PDF-файлу
    created_at        = DateTimeField(auto_now_add=True)
```

### 4.4 Таблица `CalculationStrategy` — справочник стратегий
```python
class CalculationStrategy(models.Model):
    code         = CharField(max_length=20, unique=True)  # 'operation'|'function'|'day'
    name         = CharField(max_length=255)  # человекочитаемое название
    description  = TextField()               # описание из ГОСТ
    formula_hint = TextField()               # подсказка по формуле
```

### 4.5 Таблица `RegulatoryDocument` — нормативные документы
```python
class RegulatoryDocument(models.Model):
    title        = CharField(max_length=512)  # название документа
    short_name   = CharField(max_length=128)  # "ГОСТ ISO 9612"
    description  = TextField()
    file_url     = URLField(blank=True)       # ссылка на Google Drive / PDF
    order        = IntegerField(default=0)    # порядок отображения
```

---

## 5. Математические формулы (calculators.py)

### Стратегия 1 — На основе рабочих операций
Каждая операция `m` имеет уровень `L_m` (дБ) и длительность `T_m` (мин).  
Базовая длительность `T0 = 480 мин` (8 часов).

```
L_EX,8h = 10 * log10( sum_m [ 10^(0.1 * L_m) * (T_m / T0) ] )
```

### Стратегия 2 — На основе трудовой функции
Измеренный эквивалентный уровень `L_p,A,eqTe` за эффективное время `Te`.

```
L_EX,8h = L_p,A,eqTe + 10 * log10(Te / T0)
```

### Стратегия 3 — На основе рабочего дня (полная смена)
Прямой расчёт по набору точечных замеров:

```
L_EX,8h = 10 * log10( (1/N) * sum_i [ 10^(0.1 * L_i) ] )
```

### Сравнение с нормативом
- Предельно допустимый уровень (ПДУ) шума = **80 дБ** (СанПиН 2.2.4.3359-16)
- Если `L_EX,8h > ПДУ` → `exceeds_norm = True` → формируются рекомендации

---

## 6. Визуальный дизайн (воспроизвести Tilda-сайт)

### Навбар (base.html)
- Слева: Главная | Документация | FAQ
- Центр: **Acoustic Beast** (логотип/название)
- Справа: Авторизация | Начать расчёт (кнопка)
- Тонкая нижняя граница

### Главная страница (index.html)
- Hero-секция: крупный заголовок «Приложение для расчёта и анализа уровня шума», подзаголовок, кнопка «Начать расчёт»
- Фоновое изображение — шумомер/измерительные приборы
- Секция «Процесс расчёта» — 3 карточки (кружок с цифрой + заголовок + описание):
  1. Выбор стратегии расчёта
  2. Ввод данных
  3. Отчёт

### Страница документации (docs.html)
- Тёмные карточки-аккордеоны с нормативными документами:
  - ГОСТ ISO 9612
  - СанПиН-2.2.4.3359-16
  - СП 51.13330.2011
  - Методические рекомендации

### Страница FAQ (faq.html)
- Аккордеон с типичными вопросами/ответами

### Страница расчёта (calculate.html) — 3-шаговый мастер
- Шаг 1: Выбор стратегии (3 radio-карточки)
- Шаг 2: Данные о компании (название, место, примечания)
- Шаг 3: Ввод точек замера (динамические поля через JS)
  - При стратегии 1/2: поля "уровень шума, дБ" + "длительность, мин"
  - При стратегии 3: только "уровень шума, дБ"

### Страница отчёта (result.html)
- Шапка с названием компании, датой, стратегией
- Таблица результатов: средний уровень, ПДУ, статус (норма/превышение)
- График уровней по точкам (линейный)
- Блок рекомендаций (зелёный = норма, красный = превышение)
- Кнопка «Скачать PDF»

### Цветовая схема
- Фон: `#ffffff` / `#f8f9fa`
- Тёмные акценты: `#1a1a1a` / `#2d2d2d`
- Акцентный цвет кнопок: `#4a90e2` или `#00d4ff` (из 404-страницы)
- Предупреждение о превышении нормы: `#dc3545`
- Норма: `#28a745`

---

## 7. Зависимости (requirements.txt)

```
Django==4.2.x
psycopg2-binary==2.9.x
python-dotenv==1.0.x
numpy==1.26.x
matplotlib==3.8.x
reportlab==4.0.x
Pillow==10.x
django-crispy-forms==2.1
crispy-bootstrap5==0.7
whitenoise==6.6.x
gunicorn==21.x
```

---

## 8. Этапы реализации (очерёдность)

### Этап 1 — Инициализация проекта (1 день)
- [ ] `django-admin startproject acoustic_beast`
- [ ] `python manage.py startapp noise`
- [ ] `python manage.py startapp accounts`
- [ ] Настройка `settings.py`: PostgreSQL, static/media, INSTALLED_APPS
- [ ] Создать `.env` с секретами (SECRET_KEY, DB_PASSWORD)
- [ ] `pip install -r requirements.txt`

### Этап 2 — Модели и БД (0.5 дня)
- [ ] Написать все 5 моделей в `noise/models.py`
- [ ] `python manage.py makemigrations && python manage.py migrate`
- [ ] Зарегистрировать модели в `admin.py`
- [ ] Заполнить справочник `CalculationStrategy` (3 записи)
- [ ] Заполнить `RegulatoryDocument` (4 документа)

### Этап 3 — Аутентификация (0.5 дня)
- [ ] Форма логина (`LoginForm`) с username/password
- [ ] Форма регистрации (`RegisterForm`)
- [ ] View логина — `LoginView`
- [ ] View регистрации — `RegisterView`
- [ ] Шаблоны `login.html`, `register.html`
- [ ] Декоратор `@login_required` на страницах расчёта/истории

### Этап 4 — Базовый шаблон и статические страницы (1 день)
- [ ] `base.html` — навбар, футер, подключение Bootstrap 5
- [ ] `index.html` — Hero + 3 карточки процесса
- [ ] `docs.html` — аккордеон с документами из БД
- [ ] `faq.html` — аккордеон с FAQ (можно захардкодить или из БД)
- [ ] `404.html` — тёмный фон + анимированная волна (как на Tilda)
- [ ] Подключить Bootstrap 5 через CDN или локально

### Этап 5 — Форма расчёта (1.5 дня)
- [ ] `NoiseMeasurementForm` (шаг 1+2)
- [ ] JS-скрипт для динамического добавления полей точек замера
- [ ] View `CalculateView` (GET — показать форму, POST — сохранить в БД)
- [ ] Шаблон `calculate.html` с 3-шаговым мастером
- [ ] Валидация: минимум 1 точка, уровень шума 0–200 дБ

### Этап 6 — Математический расчёт (1 день)
- [ ] Функции в `calculators.py`:
  - `calculate_strategy_1(points)` — по рабочим операциям
  - `calculate_strategy_2(points)` — по трудовой функции  
  - `calculate_strategy_3(points)` — по рабочему дню
  - `compare_with_norm(level)` → `(bool, float, list_of_recommendations)`
- [ ] Юнит-тесты для каждой функции
- [ ] Интеграция с View (вызов нужного калькулятора)

### Этап 7 — Генерация графика и отчёта (1 день)
- [ ] `generate_chart(points, measurement_id)` → PNG файл через matplotlib
  - Линейный график уровней по точкам
  - Горизонтальная красная линия ПДУ = 80 дБ
  - Сохранение в `media/charts/chart_{id}.png`
- [ ] Страница `result.html` с отображением графика и результатов
- [ ] `NoiseReport` создаётся при сохранении расчёта

### Этап 8 — PDF-отчёт (0.5 дня)
- [ ] `pdf_generator.py` с функцией `generate_pdf_report(report_id)` → PDF файл
  - Заголовок с названием компании, датой, стратегией
  - Таблица с результатами
  - Вставка графика PNG
  - Рекомендации
  - Сохранение в `media/reports/pdf/report_{id}.pdf`
- [ ] View `DownloadPDFView` — отдаёт файл или генерирует и отдаёт

### Этап 9 — История расчётов (0.5 дня)
- [ ] View `HistoryView` — список расчётов текущего пользователя
- [ ] Шаблон `history.html` — таблица с датой, компанией, результатом, ссылкой

### Этап 10 — Финальная полировка (1 день)
- [ ] Адаптивная вёрстка под мобильные (Bootstrap breakpoints)
- [ ] Сообщения об ошибках (django.contrib.messages)
- [ ] Кастомная 404/500 страница
- [ ] Проверка прав доступа (пользователь видит только свои расчёты)
- [ ] Обработка пограничных случаев: 0 точек, некорректный ввод

---

## 9. Матрица прав доступа

| Функция | Анонимный | Пользователь | Администратор |
|---------|-----------|--------------|---------------|
| Главная страница | ✓ | ✓ | ✓ |
| Документация | ✓ | ✓ | ✓ |
| FAQ | ✓ | ✓ | ✓ |
| Авторизация / Регистрация | ✓ | — | — |
| Расчёт шума | — | ✓ | ✓ |
| Просмотр своих отчётов | — | ✓ | ✓ |
| Скачать PDF | — | ✓ | ✓ |
| История расчётов | — | ✓ | ✓ |
| Все расчёты (всех юзеров) | — | — | ✓ |
| Управление пользователями | — | — | ✓ |
| Django Admin | — | — | ✓ |

---

## 10. URL-маршруты (urls.py)

```python
# noise/urls.py
urlpatterns = [
    path('',                    HomeView.as_view(),          name='home'),
    path('docs/',               DocsView.as_view(),          name='docs'),
    path('faq/',                FAQView.as_view(),           name='faq'),
    path('calculate/',          CalculateView.as_view(),     name='calculate'),
    path('result/<int:pk>/',    ResultView.as_view(),        name='result'),
    path('result/<int:pk>/pdf/',DownloadPDFView.as_view(),   name='download_pdf'),
    path('history/',            HistoryView.as_view(),       name='history'),
]

# accounts/urls.py
urlpatterns = [
    path('login/',              LoginView.as_view(),         name='login'),
    path('logout/',             LogoutView.as_view(),        name='logout'),
    path('register/',           RegisterView.as_view(),      name='register'),
]
```

---

## 11. Рекомендации по снижению шума (из ВКР)

Формируются автоматически при `exceeds_norm = True`:

1. Использование шумопоглощающих материалов на стенах и потолке
2. Установка шумоизоляционных экранов и перегородок вблизи источника
3. Перемещение шумного оборудования в отдельные помещения
4. Регулярное техническое обслуживание оборудования
5. Использование средств индивидуальной защиты органов слуха (СИЗ)
6. Введение регламентированных перерывов при работе в шумной зоне
7. Оценка вибрационного воздействия совместно с акустическим

---

## 12. Тестовый сценарий (из ВКР — ООО «ФАРМГРУПП СПб»)

**Объект**: Холодильные камеры медицинских препаратов Goldholod  
**Стратегия**: 3 (на основе рабочего дня)  
**Точки замера**: 5 точек  
**Данные**: [75, 78, 82, 85, 80] дБ  
**Ожидаемый результат**:  
- L_EX,8h ≈ 80.8 дБ → **превышение нормы** (ПДУ = 80 дБ)

> Примечание: В диссертации упоминается результат 47.3 дБ (это другое измерение — без превышения).

---

## 13. Файловая структура settings.py (ключевые настройки)

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME', default='noise_analysis_db'),
        'USER': env('DB_USER', default='postgres'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5432'),
    }
}

MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
```

---

## 14. Итоговый список страниц (аналог Tilda-сайта)

| Страница Tilda | Django-аналог | Статус |
|----------------|---------------|--------|
| Главная (hero + процесс) | `index.html` | Планируется |
| Документация (аккордеон) | `docs.html` | Планируется |
| FAQ | `faq.html` | Планируется |
| Авторизация (Tilda Members) | `accounts/login.html` | Планируется |
| Расчёт (форма) | `noise/calculate.html` | Планируется |
| Отчёт с PDF | `noise/result.html` | Планируется |
| 404 страница (волна) | `404.html` | Планируется |
| ГОСТ PDF (Google Drive embed) | Вкладка в `docs.html` | Планируется |

---

## 15. Примерный таймлайн

| Этап | Описание | Дней |
|------|----------|------|
| 1 | Инициализация проекта, структура | 1 |
| 2 | Модели и БД | 0.5 |
| 3 | Аутентификация | 0.5 |
| 4 | Базовый шаблон и статические страницы | 1 |
| 5 | Форма расчёта (мастер) | 1.5 |
| 6 | Математические калькуляторы | 1 |
| 7 | График и страница результата | 1 |
| 8 | PDF-генерация | 0.5 |
| 9 | История расчётов | 0.5 |
| 10 | Полировка, тесты, отзывчивость | 1 |
| **Итого** | | **~8.5 дней** |