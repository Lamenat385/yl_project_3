# API GoldForum - Документация

Документация нового API для форума GoldForum, добавленного в версии 2.0.

## 📋 Содержание

- [Аутентификация](#аутентификация)
- [1. Импорт поста из ZIP-архива](#1-импорт-поста-из-zip-архива)
- [2. Экспорт поста в ZIP-архив](#2-экспорт-поста-в-zip-архив)
- [3. Получение метаданных поста](#3-получение-метаданных-поста)
- [4. Экспорт избранного пользователя](#4-экспорт-избранного-пользователя)
- [Примеры использования](#примеры-использования)

---

## 🔐 Аутентификация

Для всех защищенных endpoint'ов требуется аутентификация. Используйте сессию Flask-Login.

### Вход в систему

```
POST /login
Content-Type: application/x-www-form-urlencoded

username=<username>&password=<password>&remember_me=false
```

Успешный ответ: `302 Found` (редирект)

---

## 1. Импорт поста из ZIP-архива

Загружает пост вместе с изображениями и файлами из ZIP-архива.

### Endpoint

```
POST /api/v1/posts/import
Authorization: Session (Flask-Login)
Content-Type: multipart/form-data
```

### Тело запроса

Форма с полем `zip_file` (ZIP-архив)

### Структура ZIP-архива

```
post.zip
├── post.md              # Основной файл с контентом в Markdown
├── images/              # Папка с изображениями (опционально)
│   ├── image1.jpg
│   └── image2.png
└── files/               # Папка с файлами (опционально)
    ├── document.pdf
    └── readme.txt
```

### Пример структуры post.md

```markdown
# Заголовок поста

Текст поста в формате Markdown.

![Изображение](images/image1.jpg)

[Файл для скачивания](files/document.pdf)
```

### Успешный ответ (200 OK)

```json
{
  "success": true,
  "post_id": 123,
  "title": "Заголовок поста",
  "message": "Пост успешно импортирован. Изображений: 2, Файлов: 1"
}
```

### Ошибки

| Код | Описание |
|-----|----------|
| 400 | Нет файла zip в запросе / Пустое имя файла / Неверное расширение / В архиве не найден файл post.md |
| 401 | Пользователь не авторизован |
| 500 | Ошибка при сохранении поста |

### Пример запроса (curl)

```bash
curl -X POST http://localhost:5000/api/v1/posts/import \
  -H "Cookie: session=your_session_cookie" \
  -F "zip_file=@post.zip"
```

---

## 2. Экспорт поста в ZIP-архив

Экспортирует пост вместе с изображениями и файлами в ZIP-архив.

### Endpoint

```
GET /api/v1/posts/export/<post_id>
Authorization: Session (Flask-Login)
```

### Параметры пути

| Параметр | Описание |
|----------|----------|
| post_id  | ID поста для экспорта |

### Успешный ответ (200 OK)

Файл: `post_<post_id>.zip`

### Структура ZIP-архива

```
post_123.zip
└── post_123/
    ├── post.md          # Markdown контент
    ├── images/          # Изображения
    │   ├── image1.jpg
    │   └── image2.png
    └── files/           # Файлы
        ├── document.pdf
        └── readme.txt
```

### Ошибки

| Код | Описание |
|-----|----------|
| 403 | У вас нет прав для экспорта этого поста |
| 404 | Пост не найден |
| 401 | Пользователь не авторизован |

### Пример запроса (curl)

```bash
curl -X GET http://localhost:5000/api/v1/posts/export/123 \
  -H "Cookie: session=your_session_cookie" \
  -o post_123.zip
```

---

## 3. Получение метаданных поста

Возвращает метаданные поста по его ID.

### Endpoint

```
GET /api/v1/posts/<post_id>/metadata
```

### Параметры пути

| Параметр | Описание |
|----------|----------|
| post_id  | ID поста |

### Успешный ответ (200 OK)

```json
{
  "success": true,
  "id": 123,
  "title": "Заголовок поста",
  "author": "username",
  "author_id": 1,
  "created_at": "2025-05-06T10:30:00",
  "updated_at": "2025-05-06T10:30:00",
  "content_length": 1234,
  "has_images": true,
  "has_files": true,
  "attached_images": ["image1.jpg", "image2.png"],
  "attached_files": ["document.pdf"]
}
```

### Поля ответа

| Поле | Описание |
|------|----------|
| id | ID поста |
| title | Заголовок поста |
| author | Имя автора |
| author_id | ID автора |
| created_at | Дата создания (ISO 8601) |
| updated_at | Дата последнего обновления (ISO 8601) |
| content_length | Длина контента в символах |
| has_images | Есть ли изображения |
| has_files | Есть ли файлы |
| attached_images | Список имен изображений |
| attached_files | Список имен файлов |

### Ошибки

| Код | Описание |
|-----|----------|
| 404 | Пост не найден |

### Пример запроса (curl)

```bash
curl -X GET http://localhost:5000/api/v1/posts/123/metadata
```

---

## 4. Экспорт избранного пользователя

Экспортирует все избранные посты пользователя в ZIP-архив. Требует пароль пользователя.

### Endpoint

```
POST /api/v1/users/<username>/favorites/export
Content-Type: application/json
```

### Тело запроса

```json
{
  "password": "user_password"
}
```

### Параметры пути

| Параметр | Описание |
|----------|----------|
| username | Имя пользователя |

### Успешный ответ (200 OK)

Файл: `<username>_favorites.zip`

### Структура ZIP-архива

```
admin_favorites.zip
├── metadata.json        # Общие метаданные
└── posts/
    ├── post_1/
    │   ├── post.md
    │   ├── images/
    │   └── files/
    ├── post_2/
    │   └── ...
    └── ...
```

### metadata.json

```json
{
  "username": "admin",
  "user_id": 1,
  "export_date": "2025-05-06 15:30:00",
  "posts_count": 5,
  "posts": [
    {
      "id": 1,
      "title": "Пост 1",
      "created_at": "2025-05-01T10:00:00",
      "has_images": true,
      "has_files": false
    },
    ...
  ]
}
```

### Ошибки

| Код | Описание |
|-----|----------|
| 400 | Нет JSON в теле запроса / Требуется поле "password" |
| 401 | Неверный пароль |
| 403 | Пользователь не найден / У пользователя нет избранных постов |

### Пример запроса (curl)

```bash
curl -X POST http://localhost:5000/api/v1/users/admin/favorites/export \
  -H "Content-Type: application/json" \
  -d '{"password": "admin"}' \
  -o admin_favorites.zip
```

---

## 📚 Примеры использования

### Python (requests)

```python
import requests
import zipfile
import io
import json

BASE_URL = "http://localhost:5000"

# Вход
session = requests.Session()
session.post(f"{BASE_URL}/login", data={
    "username": "admin",
    "password": "admin",
    "remember_me": False
})

# 1. Импорт поста из zip
with open("post.zip", "rb") as f:
    response = session.post(
        f"{BASE_URL}/api/v1/posts/import",
        files={"zip_file": ("post.zip", f, "application/zip")}
    )
    print(response.json())

# 2. Получение метаданных
response = session.get(f"{BASE_URL}/api/v1/posts/123/metadata")
print(json.dumps(response.json(), indent=2))

# 3. Экспорт поста
response = session.get(f"{BASE_URL}/api/v1/posts/export/123")
with open("exported_post.zip", "wb") as f:
    f.write(response.content)

# 4. Экспорт избранного
response = session.post(
    f"{BASE_URL}/api/v1/users/admin/favorites/export",
    json={"password": "admin"}
)
with open("favorites.zip", "wb") as f:
    f.write(response.content)
```

### JavaScript (fetch)

```javascript
const BASE_URL = "http://localhost:5000";

// Вход (нужно обработать cookies)
const loginResponse = await fetch(`${BASE_URL}/login`, {
  method: "POST",
  body: new URLSearchParams({
    username: "admin",
    password: "admin",
    remember_me: "false"
  })
});

// 1. Импорт поста
const formData = new FormData();
formData.append("zip_file", fileInput.files[0]);

const importResponse = await fetch(`${BASE_URL}/api/v1/posts/import`, {
  method: "POST",
  body: formData,
  credentials: "include"
});
console.log(await importResponse.json());

// 2. Получение метаданных
const metadataResponse = await fetch(`${BASE_URL}/api/v1/posts/123/metadata`, {
  credentials: "include"
});
console.log(await metadataResponse.json());

// 3. Экспорт поста
const exportResponse = await fetch(`${BASE_URL}/api/v1/posts/export/123`, {
  credentials: "include"
});
const blob = await exportResponse.blob();
const url = window.URL.createObjectURL(blob);
const a = document.createElement("a");
a.href = url;
a.download = "post_123.zip";
a.click();
```

---

## 📁 Структура ZIP-архивов

### Для импорта (input)

```
your_post.zip
├── post.md              # Обязательный файл
├── images/              # Опционально
│   ├── photo1.jpg
│   └── logo.png
└── files/               # Опционально
    ├── document.pdf
    └── data.csv
```

### Для экспорта (output)

```
post_123.zip
└── post_123/
    ├── post.md
    ├── images/
    │   ├── image1.jpg
    │   └── image2.png
    └── files/
        └── document.pdf
```

---

## 🔧 Тестирование

Запустите тестовый скрипт для проверки работы API:

```bash
python test_api.py
```

Тест создаст файлы:
- `exported_post_*.zip` - экспортированный пост
- `admin_favorites.zip` - избранное пользователя

---

## 📝 Примечания

1. Все файлы проверяются на безопасность (расширения, MIME-type)
2. Изображения: png, jpg, jpeg, gif, webp, svg, bmp
3. Файлы: pdf, doc, docx, txt, zip, rar, 7z, mp3, mp4, avi, mkv (исключены: exe, bat, sh, cmd, ps1, vbs, msi)
4. ZIP-архивы не должны превышать 16MB (ограничение Flask)
5. Метаданные поста обновляются в векторной базе при импорте

---

## 🐛 Известные ограничения

- Максимальный размер ZIP-архива: 16MB
- Имена файлов в ZIP должны быть уникальны
- Поддержка вложенных папок ограничена (images/, files/)

---

**Версия API:** 1.0  
**Дата создания:** 2025-05-06  
**Автор:** GoldForum Team
