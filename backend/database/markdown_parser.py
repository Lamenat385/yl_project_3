import re
import os
from pathlib import Path
from typing import Optional

# Проверка наличия библиотеки markdown
try:
    import markdown

    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    print("⚠️ Библиотека 'markdown' не установлена. Выполните: pip install markdown")

# Корень проекта
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Пути к медиафайлам
IMAGES_DIR = PROJECT_ROOT / 'data' / 'posts' / 'images'
FILES_DIR = PROJECT_ROOT / 'data' / 'posts' / 'files'

# Создаём директории если их нет
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
FILES_DIR.mkdir(parents=True, exist_ok=True)


def parse_markdown(text: str) -> str:
    """
    Парсит Markdown текст в HTML.

    Args:
        text: Текст в формате Markdown

    Returns:
        str: HTML код
    """
    if not text:
        return ''

    # Если библиотека не установлена, возвращаем текст с базовой обработкой
    if not MARKDOWN_AVAILABLE:
        return simple_markdown_fallback(text)

    # Настройки расширений Markdown
    extensions = [
        'tables',  # Таблицы
        'fenced_code',  # Блоки кода ```
        'codehilite',  # Подсветка синтаксиса
        'nl2br',  # Переносы строк <br>
    ]

    try:
        md = markdown.Markdown(extensions=extensions, output_format='html5')
        html = md.convert(text)
        html = sanitize_html(html)
        return html
    except Exception as e:
        print(f"❌ Ошибка парсинга Markdown: {e}")
        return simple_markdown_fallback(text)


def simple_markdown_fallback(text: str) -> str:
    """
    Базовая обработка Markdown без библиотеки.
    Используется как запасной вариант.
    """
    if not text:
        return ''

    html = text

    # Экранирование HTML
    html = html.replace('&', '&amp;')
    html = html.replace('<', '&lt;')
    html = html.replace('>', '&gt;')

    # Заголовки
    html = re.sub(r'^###### (.+)$', r'<h6>\1</h6>', html, flags=re.MULTILINE)
    html = re.sub(r'^##### (.+)$', r'<h5>\1</h5>', html, flags=re.MULTILINE)
    html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # Жирный текст
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'__(.+?)__', r'<strong>\1</strong>', html)

    # Курсив
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    html = re.sub(r'_(.+?)_', r'<em>\1</em>', html)

    # Картинки ![alt](url)
    html = re.sub(r'!\[(.+?)\]\((.+?)\)',
                  r'<img src="\2" alt="\1" class="img-fluid rounded my-2" style="max-width: 100%; border: 2px solid #D4AF37;">',
                  html)

    # Ссылки [text](url)
    html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" class="text-gold">\1</a>', html)

    # Код inline
    html = re.sub(r'`(.+?)`', r'<code class="bg-dark text-warning p-1">\1</code>', html)

    # Блоки кода
    html = re.sub(r'```(\w*)\n(.+?)```', r'<pre class="bg-dark border border-warning p-3"><code>\2</code></pre>', html,
                  flags=re.DOTALL)

    # Переносы строк
    html = html.replace('\n', '<br>')

    return html


def sanitize_html(html: str) -> str:
    """
    Базовая санитизация HTML (защита от XSS).
    Удаляет опасные теги.
    """
    if not html:
        return ''

    # Удаляем скрипты и опасные теги
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>',
        r'javascript:',
        r'on\w+\s*=',
    ]

    for pattern in dangerous_patterns:
        html = re.sub(pattern, '', html, flags=re.IGNORECASE | re.DOTALL)

    return html


def sanitize_filename(filename: str) -> str:
    """
    Очистка имени файла от опасных символов.

    Args:
        filename: Исходное имя файла

    Returns:
        str: Безопасное имя файла
    """
    if not filename:
        return ''

    # Разрешённые символы: буквы, цифры, тире, подчёркивание, точка
    sanitized = re.sub(r'[^a-zA-Z0-9_\-.]', '_', filename)

    # Защита от path traversal
    sanitized = os.path.basename(sanitized)

    # Ограничение длины
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:250] + ext

    return sanitized


def validate_image_extension(filename: str) -> bool:
    """Проверка расширения картинки"""
    allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'}
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in allowed


def validate_file_extension(filename: str) -> bool:
    """Проверка расширения файла"""
    allowed = {'pdf', 'doc', 'docx', 'txt', 'zip', 'rar', '7z', 'mp3', 'mp4', 'avi', 'mkv'}
    blocked = {'exe', 'bat', 'sh', 'cmd', 'ps1', 'vbs', 'msi'}

    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    if ext in blocked:
        return False
    return ext in allowed or ext == ''


def image_exists(filename: str) -> bool:
    """Проверка существования картинки"""
    safe_name = sanitize_filename(filename)
    return (IMAGES_DIR / safe_name).exists()


def file_exists(filename: str) -> bool:
    """Проверка существования файла"""
    safe_name = sanitize_filename(filename)
    return (FILES_DIR / safe_name).exists()


def get_image_url(filename: str) -> Optional[str]:
    """Возвращает URL картинки если она существует"""
    safe_name = sanitize_filename(filename)
    if image_exists(safe_name):
        return f'/data/posts/images/{safe_name}'
    return None


def get_file_url(filename: str) -> Optional[str]:
    """Возвращает URL файла если он существует"""
    safe_name = sanitize_filename(filename)
    if file_exists(safe_name):
        return f'/data/posts/files/{safe_name}'
    return None


def save_uploaded_image(file, filename: str) -> Optional[str]:
    """
    Сохраняет загруженную картинку.

    Args:
        file: FileStorage объект
        filename: Имя файла

    Returns:
        str: Уникальное имя файла или None при ошибке
    """
    try:
        if not validate_image_extension(filename):
            return None

        safe_name = sanitize_filename(filename)
        file_path = IMAGES_DIR / safe_name

        file.save(str(file_path))
        return safe_name

    except Exception as e:
        print(f"❌ Ошибка сохранения картинки: {e}")
        return None


def save_uploaded_file(file, filename: str) -> Optional[str]:
    """
    Сохраняет загруженный файл.

    Args:
        file: FileStorage объект
        filename: Имя файла

    Returns:
        str: Уникальное имя файла или None при ошибке
    """
    try:
        if not validate_file_extension(filename):
            return None

        safe_name = sanitize_filename(filename)
        file_path = FILES_DIR / safe_name

        file.save(str(file_path))
        return safe_name

    except Exception as e:
        print(f"❌ Ошибка сохранения файла: {e}")
        return None


def delete_image(filename: str) -> bool:
    """Удаление картинки"""
    try:
        safe_name = sanitize_filename(filename)
        file_path = IMAGES_DIR / safe_name

        if file_path.exists():
            file_path.unlink()
            return True
        return False
    except Exception as e:
        print(f"❌ Ошибка удаления картинки: {e}")
        return False


def delete_file(filename: str) -> bool:
    """Удаление файла"""
    try:
        safe_name = sanitize_filename(filename)
        file_path = FILES_DIR / safe_name

        if file_path.exists():
            file_path.unlink()
            return True
        return False
    except Exception as e:
        print(f"❌ Ошибка удаления файла: {e}")
        return False


def get_file_size(filepath: str) -> int:
    """Получение размера файла в байтах"""
    try:
        path = Path(filepath)
        if path.exists():
            return path.stat().st_size
        return 0
    except Exception:
        return 0


def format_file_size(size_bytes: int) -> str:
    """Форматирование размера файла (KB, MB, GB)"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"