# GoldForum

Платформа для ведения блогов с векторным поиском, ML-рекомендациями и REST API. Построена на Flask + SQLAlchemy + ChromaDB.

---

## Возможности

### Веб-интерфейс
- Регистрация и авторизация пользователей
- Создание, просмотр и удаление постов
- Markdown-контент с рендерингом в HTML
- Загрузка изображений и файлов к постам
- Комментарии к постам
- Лайки, избранное, отметки «прочитано»
- Профиль пользователя с вкладками (посты / лайки / избранное / прочитано)
- Полнотекстовый векторный поиск по постам и авторам

### REST API (v1)
| Группа | Метод | Маршрут | Описание |
|--------|-------|---------|----------|
| **Авторизация** | `POST` | `/api/v1/auth/login` | Вход (username + password) |
| | `POST` | `/api/v1/auth/logout` | Выход |
| | `GET` | `/api/v1/auth/status` | Статус сессии |
| **Посты** | `GET` | `/api/posts` | Список последних 20 постов |
| | `GET` | `/api/posts/<id>` | Один пост |
| | `POST` | `/api/posts` | Создать пост (требует авторизацию) |
| | `DELETE` | `/api/posts/<id>` | Удалить свой пост |
| | `GET` | `/api/v1/posts/<id>/metadata` | Метаданные поста |
| | `GET` | `/api/v1/posts/<id>/export` | Экспорт поста в ZIP |
| | `POST` | `/api/v1/posts/import` | Импорт поста из ZIP |
| | `POST` | `/api/v1/posts/export/bulk` | Массовый экспорт в ZIP |
| **Лента** | `GET` | `/api/feed` | Батч рекомендаций (infinite scroll) |
| | `POST` | `/api/feed/record` | Запись взаимодействия |
| **Взаимодействия** | `POST` | `/api/interactions/toggle` | Переключить like/favorite/read |
| | `GET` | `/api/interactions/post/<id>/status` | Статусы взаимодействий |
| | `GET` | `/api/interactions/user/<id>/favorites` | ID избранных постов |
| | `GET` | `/api/interactions/user/<id>/liked` | ID понравившихся постов |
| | `GET` | `/api/interactions/user/<id>/read` | ID прочитанных постов |
| **Комментарии** | `GET` | `/api/v1/posts/<id>/comments` | Список комментариев |
| | `POST` | `/api/v1/posts/<id>/comments` | Добавить комментарий |
| | `DELETE` | `/api/v1/comments/<id>` | Удалить свой комментарий |
| | `POST` | `/api/v1/posts/<id>/like` | Лайк/анлайк поста |
| **Экспорт** | `POST` | `/api/v1/users/<name>/favorites/export` | Экспорт избранного (по паролю) |
| **Загрузка** | `POST` | `/api/upload/image` | Загрузка изображения |
| | `POST` | `/api/upload/file` | Загрузка файла |

### REST API (v2 — Flask-RESTful)
| Метод | Маршрут | Описание |
|-------|---------|----------|
| `GET` | `/api/v2/posts` | Список постов |
| `GET` | `/api/v2/posts/<id>` | Один пост |
| `POST` | `/api/v2/posts` | Создать пост |

### Рекомендательная система
- Два FIFO-буфера взаимодействий (Alpha / Beta) для каждого пользователя
- Весовые очки: read=1, like=3, favorite=5
- Вектор профиля вычисляется взвешенным усреднением эмбеддингов
- Вероятностный выбор: Alpha 50% / Beta 30% / Random 20%
- Порог косинусного расстояния (TBM) для фильтрации кандидатов
- Fallback — случайный пост с весом √(likes_count)
- Настройки в `backend/recommendation/config.json`

### Векторный поиск
- Эмбеддинги через `paraphrase-multilingual-MiniLM-L12-v2` (SentenceTransformers)
- Хранение векторов в ChromaDB (PersistentClient)
- Косинусное расстояние для ранжирования результатов

---

## Установка и запуск

### Требования
- Python 3.10+
- 4+ ГБ RAM (для ML-модели эмбеддингов)

### 1. Клонирование
```bash
git clone <repo-url>
cd PythonProject17
```

### 2. Виртуальное окружение
```bash
python -m venv .venv
.venv\Scripts\activate     # Windows
source .venv/bin/activate  # Linux/Mac
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Первый запуск
```bash
python app.py
```

При первом запуске автоматически:
- Создаётся база SQLite `data/sql_db/forum.db`
- Создаётся пользователь `admin` / `admin`
- Инициализируется векторная база ChromaDB в `data/vector_db/`
- Загружается ML-модель эмбеддингов (~470 МБ, кешируется)

Сервер будет доступен по адресу **http://127.0.0.1:5000**.

---

## Структура проекта

```
PythonProject17/
├── app.py                          # Точка входа, конфигурация Flask, маршруты
├── requirements.txt                # Зависимости Python
├── API_DOCUMENTATION.md            # Документация API с примерами
├── readme.md                       # Этот файл
│
├── backend/
│   ├── errors.py                   # Обработчики HTTP-ошибок (400–505)
│   ├── api/
│   │   ├── auth_api.py             # API авторизации
│   │   ├── posts_api.py            # CRUD постов
│   │   ├── comments_api.py         # Комментарии и лайки
│   │   ├── interactions_api.py     # like/favorite/read/not_interested
│   │   ├── feed_api.py             # Лента рекомендаций
│   │   ├── posts_export_api.py     # Экспорт постов в ZIP
│   │   ├── posts_import_api.py     # Импорт/экспорт постов через ZIP
│   │   └── posts_metadata_api.py   # Метаданные + экспорт избранного
│   ├── database/
│   │   ├── db_session.py           # Фабрика сессий SQLAlchemy (SQLite)
│   │   ├── default_data.py         # Создание дефолтного пользователя
│   │   ├── markdown_parser.py      # Парсер Markdown → HTML + работа с файлами
│   │   └── models/
│   │       ├── users_model.py      # Модель пользователя
│   │       ├── posts_model.py      # Модель поста
│   │       ├── comments_model.py   # Модель комментария
│   │       └── user_post_interaction.py  # Взаимодействия пользователь↔пост
│   ├── recommendation/
│   │   ├── __init__.py             # Движок рекомендаций (RecommendationEngine)
│   │   └── config.json             # Параметры алгоритма
│   ├── vector_db/
│   │   └── vector_db.py            # Обёртка над ChromaDB + SentenceTransformers
│   ├── resources/
│   │   └── posts_resources.py      # Flask-RESTful ресурсы (API v2)
│   └── forms/
│       ├── users_form.py           # Формы логина/регистрации
│       └── post_form.py            # Форма создания поста
│
├── data/
│   ├── sql_db/                     # SQLite база данных
│   ├── vector_db/                  # ChromaDB (векторные индексы)
│   └── posts/
│       ├── images/                 # Загруженные изображения
│       └── files/                  # Загруженные файлы
│
├── static/
│   ├── css/                        # Стили
│   ├── images/                     # Статические изображения
│   ├── json/                       # JSON-ресурсы
│   └── uploads/                    # Публичные загрузки
│
└── templates/
    ├── base.html                   # Базовый шаблон
    ├── index.html                  # Главная (лента постов)
    ├── post_detail.html            # Страница поста
    ├── create_post.html            # Создание поста
    ├── login.html                  # Вход
    ├── register.html               # Регистрация
    ├── profile.html                # Профиль пользователя
    ├── search.html                 # Результаты поиска
    └── error.html                  # Страница ошибки
```

---

## Ключевые зависимости

| Пакет | Назначение |
|-------|-----------|
| `flask` | Веб-фреймворк |
| `flask-login` | Сессии и аутентификация |
| `flask-wtf` | Формы (логин, регистрация, пост) |
| `flask-restful` | REST API v2 |
| `sqlalchemy` | ORM для SQLite |
| `sqlalchemy-serializer` | Сериализация моделей в JSON |
| `chromadb` | Векторная база данных |
| `sentence-transformers` | ML-модель эмбеддингов |
| `markdown` | Парсинг Markdown → HTML |
| `werkzeug` | Утилиты WSGI (пароли, secure_filename) |

---

## Конфигурация рекомендаций

Файл `backend/recommendation/config.json`:

```json
{
    "DR": 1,         // Очки за «прочитано»
    "DL": 3,         // Очки за «лайк»
    "DS": 5,         // Очки за «избранное»
    "alpha_N": 25,   // Размер буфера Alpha (FIFO)
    "beta_N": 10,    // Размер буфера Beta (FIFO)
    "alphaPerc": 0.5, // Вероятность выбора Alpha
    "betaPerc": 0.3,  // Вероятность выбора Beta
    "randPerc": 0.2,  // Вероятность случайного поста
    "TBM": 0.3        // Порог косинусного расстояния
}
```

Сумма `alphaPerc + betaPerc + randPerc` должна быть строго равна `1.0`.

---

## Примечания

- **Эмбеддинги:** при первом запуске модель `paraphrase-multilingual-MiniLM-L12-v2` (~470 МБ) загружается из Hugging Face Hub и кешируется в `~/.cache/`.
- **База данных:** SQLite хранится в `data/sql_db/forum.db`. Для сброса — удалить файл и перезапустить сервер.
- **ChromaDB:** векторные индексы в `data/vector_db/`. При старте сервер синхронизирует их с существующими постами.
- **Загрузки:** максимальный размер запроса — 16 МБ. Изображения: png, jpg, jpeg, gif, webp.
- **Production:** замените `SECRET_KEY` в `app.py` на случайную строку и отключите `debug=True`.
