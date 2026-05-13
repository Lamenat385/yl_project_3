# GoldForum API Documentation

## Общая информация

GoldForum API предоставляет REST-интерфейс для работы с постами, комментариями, избранным и пользователями.

**Базовый URL:** `http://localhost:5000`

**Формат данных:** JSON (для POST/PUT запросов) или multipart/form-data (для загрузки файлов)

---

## 1. Авторизация

### POST /api/v1/auth/login

Вход в систему по username и password.

**Тело запроса (JSON):**
```json
{
    "username": "sari",
    "password": "12345678"
}
```

**Пример на Python:**
```python
import requests

response = requests.post(
    "http://localhost:5000/api/v1/auth/login",
    json={"username": "sari", "password": "12345678"}
)
print(response.json())
```

**Ответ (успех):**
```json
{
    "success": true,
    "user_id": 1,
    "username": "sari",
    "message": "Успешный вход"
}
```

**Статусы:**
- `200` - Успешный вход
- `400` - Неверный запрос (отсутствуют username или password)
- `401` - Неверный пароль или пользователь не найден

---

### POST /api/v1/auth/logout

Выход из системы.

**Пример на Python:**
```python
import requests

# Сначала войдите, чтобы получить сессию
session = requests.Session()
session.post(
    "http://localhost:5000/api/v1/auth/login",
    json={"username": "sari", "password": "12345678"}
)

# Затем выйдите
response = session.post("http://localhost:5000/api/v1/auth/logout")
print(response.json())
```

---

### GET /api/v1/auth/status

Проверка статуса авторизации.

**Пример на Python:**
```python
import requests

session = requests.Session()
session.post(
    "http://localhost:5000/api/v1/auth/login",
    json={"username": "sari", "password": "12345678"}
)

response = session.get("http://localhost:5000/api/v1/auth/status")
print(response.json())
# {"is_authenticated": True, "user_id": 1, "username": "sari"}
```

---

## 2. Посты

### GET /api/v1/posts/<int:post_id>/metadata

Получение метаданных поста по ID.

**Пример на Python:**
```python
import requests

session = requests.Session()
session.post(
    "http://localhost:5000/api/v1/auth/login",
    json={"username": "sari", "password": "12345678"}
)

response = session.get("http://localhost:5000/api/v1/posts/1/metadata")
print(response.json())
```

**Ответ:**
```json
{
    "id": 1,
    "title": "Название поста",
    "author": "sari",
    "author_id": 1,
    "created_at": "2025-05-06T10:30:00",
    "updated_at": "2025-05-06T10:30:00",
    "content_length": 1234,
    "has_images": true,
    "has_files": true,
    "attached_images": ["image1.jpg", "image2.jpg"],
    "attached_files": ["document.pdf"]
}
```

---

### POST /api/v1/posts/import

Импорт поста из zip-архива (multipart/form-data).

**Тело запроса:**
- `zip_file` - zip-архив с постом

**Структура zip-архива:**
```
post.md          - основной файл с контентом в Markdown
images/          - папка с изображениями (опционально)
files/           - папка с файлами (опционально)
```

**Пример на Python:**
```python
import requests

session = requests.Session()
session.post(
    "http://localhost:5000/api/v1/auth/login",
    json={"username": "sari", "password": "12345678"}
)

with open('post.zip', 'rb') as f:
    files = {'zip_file': ('post.zip', f, 'application/zip')}
    response = session.post(
        "http://localhost:5000/api/v1/posts/import",
        files=files
    )
    print(response.json())
```

**Ответ:**
```json
{
    "success": true,
    "post_id": 123,
    "title": "Название поста",
    "message": "Пост успешно импортирован. Изображений: 2, Файлов: 1"
}
```

---

### GET /api/v1/posts/<int:post_id>/export

Экспорт поста в zip-архив.

**Пример на Python:**
```python
import requests

session = requests.Session()
session.post(
    "http://localhost:5000/api/v1/auth/login",
    json={"username": "sari", "password": "12345678"}
)

response = session.get("http://localhost:5000/api/v1/posts/1/export")
with open('post_1.zip', 'wb') as f:
    f.write(response.content)
print("Пост успешно экспортирован!")
```

**Структура zip-архива:**
```
post_{post_id}.zip
└── post_{post_id}/
    ├── post.md
    ├── images/
    │   └── image1.jpg
    └── files/
        └── document.pdf
```

---

### POST /api/v1/posts/export/bulk

Экспорт нескольких постов в один zip-архив.

**Тело запроса (JSON):**
```json
{
    "post_ids": [1, 2, 3]
}
```

**Пример на Python:**
```python
import requests

session = requests.Session()
session.post(
    "http://localhost:5000/api/v1/auth/login",
    json={"username": "sari", "password": "12345678"}
)

response = session.post(
    "http://localhost:5000/api/v1/posts/export/bulk",
    json={"post_ids": [1, 2, 3]}
)
with open('posts_export.zip', 'wb') as f:
    f.write(response.content)
print("Посты успешно экспортированы!")
```

---

## 3. Комментарии

### GET /api/v1/posts/<int:post_id>/comments

Получение всех комментариев к посту.

**Пример на Python:**
```python
import requests

session = requests.Session()
session.post(
    "http://localhost:5000/api/v1/auth/login",
    json={"username": "sari", "password": "12345678"}
)

response = session.get("http://localhost:5000/api/v1/posts/1/comments")
print(response.json())
```

**Ответ:**
```json
{
    "success": true,
    "comments": [
        {
            "id": 1,
            "user_id": 1,
            "username": "sari",
            "content": "Текст комментария",
            "content_html": "<p>Текст комментария</p>",
            "likes_count": 5,
            "created_at": "2025-05-08 10:30:00"
        }
    ]
}
```

---

### POST /api/v1/posts/<int:post_id>/comments

Добавление комментария к посту.

**Тело запроса (JSON):**
```json
{
    "content": "Текст комментария"
}
```

**Пример на Python:**
```python
import requests

session = requests.Session()
session.post(
    "http://localhost:5000/api/v1/auth/login",
    json={"username": "sari", "password": "12345678"}
)

response = session.post(
    "http://localhost:5000/api/v1/posts/1/comments",
    json={"content": "Отличный пост!"}
)
print(response.json())
```

**Ответ:**
```json
{
    "success": true,
    "comment": {
        "id": 1,
        "user_id": 1,
        "username": "sari",
        "content": "Отличный пост!",
        "content_html": "<p>Отличный пост!</p>",
        "likes_count": 0,
        "created_at": "2025-05-08 11:00:00"
    }
}
```

---

### DELETE /api/v1/comments/<int:comment_id>

Удаление комментария (только автор может удалить свой комментарий).

**Пример на Python:**
```python
import requests

session = requests.Session()
session.post(
    "http://localhost:5000/api/v1/auth/login",
    json={"username": "sari", "password": "12345678"}
)

response = session.delete("http://localhost:5000/api/v1/comments/1")
print(response.json())
```

---

### POST /api/v1/posts/<int:post_id>/like

Поставить/убрать лайк посту.

**Пример на Python:**
```python
import requests

session = requests.Session()
session.post(
    "http://localhost:5000/api/v1/auth/login",
    json={"username": "sari", "password": "12345678"}
)

# Поставить лайк
response = session.post("http://localhost:5000/api/v1/posts/1/like")
print(response.json())
# {"success": true, "likes_count": 5}
```

---

### POST /api/v1/comments/<int:comment_id>/like

Поставить/убрать лайк комментарию.

**Пример на Python:**
```python
import requests

session = requests.Session()
session.post(
    "http://localhost:5000/api/v1/auth/login",
    json={"username": "sari", "password": "12345678"}
)

# Поставить лайк
response = session.post("http://localhost:5000/api/v1/comments/1/like")
print(response.json())
# {"success": true, "likes_count": 1}

# Убрать лайк
response = session.post("http://localhost:5000/api/v1/comments/1/like")
print(response.json())
# {"success": true, "likes_count": 0}
```

---

## 4. Взаимодействия с постами

### POST /api/interactions/toggle

Переключение любого типа взаимодействия (лайк, избранное, прочитано).

**Тело запроса (JSON):**
```json
{
    "post_id": 1,
    "action": "like"
}
```

**Доступные действия:** `like`, `favorite`, `read`, `not_interested`

**Пример на Python:**
```python
import requests

session = requests.Session()
session.post(
    "http://localhost:5000/api/v1/auth/login",
    json={"username": "sari", "password": "12345678"}
)

# Поставить лайк
response = session.post(
    "http://localhost:5000/api/interactions/toggle",
    json={"post_id": 1, "action": "like"}
)
print(response.json())

# Добавить в избранное
response = session.post(
    "http://localhost:5000/api/interactions/toggle",
    json={"post_id": 1, "action": "favorite"}
)
print(response.json())
```

---

### GET /api/interactions/post/<int:post_id>/status

Получение статуса всех взаимодействий для поста.

**Пример на Python:**
```python
import requests

session = requests.Session()
session.post(
    "http://localhost:5000/api/v1/auth/login",
    json={"username": "sari", "password": "12345678"}
)

response = session.get("http://localhost:5000/api/interactions/post/1/status")
print(response.json())
# {"is_liked": true, "is_favorite": false, "is_read": true, "is_not_interested": false}
```

---

## 5. Экспорт избранного пользователя

### POST /api/v1/users/<username>/favorites/export

Экспорт всех избранных постов пользователя в zip-архив.

**Тело запроса (JSON):**
```json
{
    "password": "user_password"
}
```

**Пример на Python:**
```python
import requests

session = requests.Session()
session.post(
    "http://localhost:5000/api/v1/auth/login",
    json={"username": "sari", "password": "12345678"}
)

# Экспорт избранного пользователя
response = session.post(
    "http://localhost:5000/api/v1/users/sari/favorites/export",
    json={"password": "12345678"}
)
with open('sari_favorites.zip', 'wb') as f:
    f.write(response.content)
print("Избранное успешно экспортировано!")
```

**Структура zip-архива:**
```
username_favorites.zip
└── posts/
    ├── post_1/
    │   ├── post.md
    │   ├── images/
    │   └── files/
    ├── post_2/
    │   └── ...
    └── metadata.json
```

---

## Пример полного сценария использования

```python
import requests
import json

# Инициализация сессии
session = requests.Session()
BASE_URL = "http://localhost:5000"

# 1. Вход в систему
response = session.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={"username": "sari", "password": "12345678"}
)
print("Login:", response.json())

# 2. Создание поста
response = session.post(
    f"{BASE_URL}/api/posts",
    json={
        "title": "Мой новый пост",
        "content": "# Привет, мир!\nЭто мой первый пост."
    }
)
post_id = response.json().get('id')
print("Created post:", post_id)

# 3. Добавление комментария
response = session.post(
    f"{BASE_URL}/api/v1/posts/{post_id}/comments",
    json={"content": "Отличный пост!"}
print("Comment:", response.json())

# 4. Поставить лайк
response = session.post(f"{BASE_URL}/api/v1/posts/{post_id}/like")
print("Like:", response.json())

# 5. Экспорт поста
response = session.get(f"{BASE_URL}/api/v1/posts/{post_id}/export")
with open(f'post_{post_id}.zip', 'wb') as f:
    f.write(response.content)
print("Post exported!")

# 6. Выход
response = session.post(f"{BASE_URL}/api/v1/auth/logout")
print("Logout:", response.json())
```

---

## Обработка ошибок

Все API-эндпоинты возвращают JSON-ответы с ошибками в следующем формате:

```json
{
    "success": false,
    "error": "Описание ошибки"
}
```

**Коды ошибок:**
- `400` - Неверный запрос (отсутствуют обязательные поля)
- `401` - Не авторизован (неверный пароль или пользователь не найден)
- `403` - Доступ запрещен (нет прав на действие)
- `404` - Ресурс не найден
- `500` - Внутренняя ошибка сервера
