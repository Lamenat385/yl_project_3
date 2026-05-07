"""
API для импорта постов из zip-архивов
"""

import os
import uuid
import zipfile
from pathlib import Path
from flask import Blueprint, jsonify, request, send_file, session
from flask_login import login_required, current_user
from werkzeug.security import check_password_hash

from backend.database import db_session
from backend.database.models.posts_model import PostModel
from backend.database.models.users_model import UserModel
from backend.database.markdown_parser import parse_markdown, sanitize_filename, validate_image_extension, validate_file_extension
from backend.vector_db import vector_db

import io
import tempfile
import shutil

blueprint = Blueprint('posts_import_api', __name__)


def extract_post_from_zip(zip_path):
    """
    Извлекает данные поста из zip-архива.
    
    Ожидаемая структура zip:
    post.md          - основной файл с контентом в Markdown
    images/          - папка с изображениями (опционально)
    files/           - папка с файлами (опционально)
    
    В post.md можно ссылаться на файлы как:
    ![alt](images/photo.jpg)
    [file](files/document.pdf)
    """
    extracted_data = {
        'markdown': None,
        'images': [],
        'files': []
    }
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Ищем post.md в корне или в подпапках
        for name in zip_ref.namelist():
            if name.endswith('.md') and not name.startswith('__MACOSX'):
                with zip_ref.open(name) as f:
                    extracted_data['markdown'] = f.read().decode('utf-8')
                break
        
        # Извлекаем изображения
        images_dir = 'images/'
        for name in zip_ref.namelist():
            if name.startswith(images_dir) and not name.endswith('/'):
                ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
                if validate_image_extension(name):
                    with zip_ref.open(name) as f:
                        content = f.read()
                        filename = Path(name).name
                        extracted_data['images'].append({
                            'filename': filename,
                            'content': content
                        })
        
        # Извлекаем файлы
        files_dir = 'files/'
        for name in zip_ref.namelist():
            if name.startswith(files_dir) and not name.endswith('/'):
                ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
                if validate_file_extension(name):
                    with zip_ref.open(name) as f:
                        content = f.read()
                        filename = Path(name).name
                        extracted_data['files'].append({
                            'filename': filename,
                            'content': content
                        })
    
    return extracted_data


def process_markdown_references(markdown_text, images_dir, files_dir):
    """
    Обновляет пути к изображениям и файлам в markdown после загрузки.
    Заменяет относительные пути на абсолютные URL.
    """
    # В будущем можно добавить логику замены путей
    return markdown_text


@blueprint.route('/api/v1/posts/import', methods=['POST'])
def import_post_from_zip():
    """
    Импортирует пост из zip-архива.

    Тело запроса: multipart/form-data с полем 'zip_file'

    Ожидаемая структура zip:
    post.md          - основной файл с контентом в Markdown
    images/          - папка с изображениями (опционально)
    files/           - папка с файлами (опционально)

    Возвращает:
    {
        "success": true,
        "post_id": 123,
        "title": "Название поста",
        "message": "Пост успешно импортирован"
    }
    """
    # Проверяем аутентификацию вручную
    from backend.database import db_session
    from backend.database.models.users_model import UserModel
    from flask_login import login_user
    
    # Проверяем, аутентифицирован ли пользователь через стандартный способ
    if current_user.is_authenticated:
        pass  # Пользователь аутентифицирован, продолжаем выполнение
    else:
        # Если стандартная проверка не сработала, пробуем проверить сессию напрямую
        user_id = session.get('_user_id')
        if user_id:
            # Проверяем, существует ли пользователь в БД
            db_sess = db_session.create_session()
            try:
                user = db_sess.get(UserModel, user_id)
                if user:
                    # Пользователь существует, можно продолжить выполнение
                    # Установим current_user вручную, чтобы остальная логика работала
                    login_user(user)
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Требуется авторизация'
                    }), 401
            finally:
                db_sess.close()
        else:
            return jsonify({
                'success': False,
                'error': 'Требуется авторизация'
            }), 401
    
    if 'zip_file' not in request.files:
        return jsonify({
            'success': False,
            'error': 'Нет файла zip в запросе'
        }), 400
    
    zip_file = request.files['zip_file']
    if zip_file.filename == '':
        return jsonify({
            'success': False,
            'error': 'Пустое имя файла'
        }), 400
    
    if not zip_file.filename.endswith('.zip'):
        return jsonify({
            'success': False,
            'error': 'Файл должен иметь расширение .zip'
        }), 400
    
    # Создаем временную директорию для обработки
    temp_dir = None
    try:
        # Создаем временную папку
        temp_dir = Path(tempfile.mkdtemp())
        zip_path = temp_dir / 'upload.zip'
        zip_file.save(str(zip_path))
        
        # Извлекаем данные из zip
        extracted = extract_post_from_zip(str(zip_path))
        
        if not extracted['markdown']:
            return jsonify({
                'success': False,
                'error': 'В архиве не найден файл post.md'
            }), 400
        
        # Парсим markdown для получения заголовка
        # Ищем первый заголовок # Заголовок
        import re
        title_match = re.search(r'^#\s+(.+)$', extracted['markdown'], re.MULTILINE)
        title = title_match.group(1) if title_match else 'Без заголовка'
        
        # Обновляем пути в markdown (если есть изображения/файлы)
        markdown_content = extracted['markdown']
        
        # Сохраняем изображения
        attached_images = []
        for img in extracted['images']:
            safe_name = sanitize_filename(img['filename'])
            ext = safe_name.rsplit('.', 1)[-1].lower() if '.' in safe_name else ''
            unique_name = f"{uuid.uuid4()}.{ext}"
            
            img_path = Path(__file__).resolve().parent.parent.parent / 'data' / 'posts' / 'images' / unique_name
            img_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(img_path, 'wb') as f:
                f.write(img['content'])
            
            attached_images.append(unique_name)
        
        # Сохраняем файлы
        attached_files = []
        for file in extracted['files']:
            safe_name = sanitize_filename(file['filename'])
            ext = safe_name.rsplit('.', 1)[-1].lower() if '.' in safe_name else ''
            unique_name = f"{uuid.uuid4()}.{ext}"
            
            file_path = Path(__file__).resolve().parent.parent.parent / 'data' / 'posts' / 'files' / unique_name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(file['content'])
            
            attached_files.append(unique_name)
        
        # Создаем пост в БД
        db_sess = db_session.create_session()
        try:
            post = PostModel()
            post.title = title
            post.content = markdown_content
            post.content_html = parse_markdown(markdown_content)
            post.author = current_user.username
            post.user_id = current_user.id
            post.attached_images = ','.join(attached_images) if attached_images else None
            post.attached_files = ','.join(attached_files) if attached_files else None
            db_sess.add(post)
            db_sess.commit()
            
            # Синхронизируем с векторной базой
            vector_db.sync_post(post.id, post.title or "Без заголовка", post.content, post.author)
            
            return jsonify({
                'success': True,
                'post_id': post.id,
                'title': title,
                'message': f'Пост успешно импортирован. Изображений: {len(attached_images)}, Файлов: {len(attached_files)}'
            })
        except Exception as e:
            db_sess.rollback()
            return jsonify({
                'success': False,
                'error': f'Ошибка при сохранении поста: {str(e)}'
            }), 500
        finally:
            db_sess.close()
    
    except zipfile.BadZipFile:
        return jsonify({
            'success': False,
            'error': 'Неверный zip-архив'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка при обработке архива: {str(e)}'
        }), 500
    finally:
        # Очищаем временную папку
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir)


@blueprint.route('/api/v1/posts/export/<int:post_id>', methods=['GET'])
def export_post_to_zip(post_id):
    """
    Экспортирует пост в zip-архив с изображениями и файлами.

    Возвращает zip-архив со структурой:
    post_id/
    ├── post.md
    ├── images/
    │   └── image1.jpg
    └── files/
        └── document.pdf
    """
    # Проверяем аутентификацию вручную
    from backend.database import db_session
    from backend.database.models.users_model import UserModel
    from flask_login import login_user
    
    # Проверяем, аутентифицирован ли пользователь через стандартный способ
    if current_user.is_authenticated:
        pass  # Пользователь аутентифицирован, продолжаем выполнение
    else:
        # Если стандартная проверка не сработала, пробуем проверить сессию напрямую
        user_id = session.get('_user_id')
        if user_id:
            # Проверяем, существует ли пользователь в БД
            db_sess = db_session.create_session()
            try:
                user = db_sess.get(UserModel, user_id)
                if user:
                    # Пользователь существует, можно продолжить выполнение
                    # Установим current_user вручную, чтобы остальная логика работала
                    login_user(user)
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Требуется авторизация'
                    }), 401
            finally:
                db_sess.close()
        else:
            return jsonify({
                'success': False,
                'error': 'Требуется авторизация'
            }), 401
    db_sess = db_session.create_session()
    try:
        post = db_sess.get(PostModel, post_id)
        if not post:
            return jsonify({
                'success': False,
                'error': 'Пост не найден'
            }), 404
        
        # Проверяем, что пост принадлежит пользователю
        if post.user_id != current_user.id and not current_user.username == 'admin':
            return jsonify({
                'success': False,
                'error': 'У вас нет прав для экспорта этого поста'
            }), 403
        
        # Создаем zip в памяти
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Добавляем post.md
            zip_file.writestr(f'post_{post.id}/post.md', post.content)
            
            # Добавляем изображения
            if post.attached_images:
                images = post.attached_images.split(',')
                for img_name in images:
                    img_path = Path(__file__).resolve().parent.parent.parent / 'data' / 'posts' / 'images' / img_name
                    if img_path.exists():
                        with open(img_path, 'rb') as f:
                            zip_file.writestr(f'post_{post.id}/images/{img_name}', f.read())
            
            # Добавляем файлы
            if post.attached_files:
                files = post.attached_files.split(',')
                for file_name in files:
                    file_path = Path(__file__).resolve().parent.parent.parent / 'data' / 'posts' / 'files' / file_name
                    if file_path.exists():
                        with open(file_path, 'rb') as f:
                            zip_file.writestr(f'post_{post.id}/files/{file_name}', f.read())
        
        memory_file.seek(0)
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'post_{post.id}.zip'
        )
    finally:
        db_sess.close()
