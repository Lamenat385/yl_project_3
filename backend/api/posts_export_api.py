"""
API для экспорта постов в zip-архивы
"""

from flask import Blueprint, jsonify, request, send_file
from flask_login import login_required, current_user

from backend.database import db_session
from backend.database.models.posts_model import PostModel
from backend.database.models.user_post_interaction import UserPostInteraction

import io
import zipfile
from pathlib import Path

blueprint = Blueprint('posts_export_api', __name__)


@blueprint.route('/api/v1/posts/<int:post_id>/export', methods=['GET'])
@login_required
def export_post(post_id):
    """
    Экспорт поста в zip-архив.

    Возвращает: zip-архив со структурой:
    post_{post_id}.zip
    └── post_{post_id}/
        ├── post.md
        ├── images/
        │   └── image1.jpg
        └── files/
            └── document.pdf

    Статусы:
    200 - Успешный экспорт
    403 - Пост не принадлежит пользователю
    404 - Пост не найден
    """
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


@blueprint.route('/api/v1/posts/export/bulk', methods=['POST'])
@login_required
def export_posts_bulk():
    """
    Экспорт нескольких постов в один zip-архив.

    Тело запроса (JSON):
    {
        "post_ids": [1, 2, 3]
    }

    Возвращает: zip-архив с постами в формате:
    posts_export_{timestamp}.zip
    └── post_{post_id}/
        ├── post.md
        ├── images/
        └── files/

    Статусы:
    200 - Успешный экспорт
    400 - Неверный запрос
    """
    if not request.is_json:
        return jsonify({
            'success': False,
            'error': 'Требуется JSON в теле запроса'
        }), 400

    data = request.get_json()
    if not data or 'post_ids' not in data or not isinstance(data['post_ids'], list):
        return jsonify({
            'success': False,
            'error': 'Требуется поле "post_ids" с массивом ID постов'
        }), 400

    post_ids = data['post_ids']

    db_sess = db_session.create_session()
    try:
        posts = db_sess.query(PostModel).filter(PostModel.id.in_(post_ids)).all()

        if not posts:
            return jsonify({
                'success': False,
                'error': 'Посты не найдены'
            }), 404

        # Проверяем права доступа
        for post in posts:
            if post.user_id != current_user.id and not current_user.username == 'admin':
                return jsonify({
                    'success': False,
                    'error': f'У вас нет прав для экспорта поста {post.id}'
                }), 403

        # Создаем zip в памяти
        import datetime
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for post in posts:
                post_folder = f'post_{post.id}/'

                # Добавляем post.md
                zip_file.writestr(post_folder + 'post.md', post.content)

                # Добавляем изображения
                if post.attached_images:
                    images = post.attached_images.split(',')
                    for img_name in images:
                        img_path = Path(__file__).resolve().parent.parent.parent / 'data' / 'posts' / 'images' / img_name
                        if img_path.exists():
                            with open(img_path, 'rb') as f:
                                zip_file.writestr(post_folder + f'images/{img_name}', f.read())

                # Добавляем файлы
                if post.attached_files:
                    files = post.attached_files.split(',')
                    for file_name in files:
                        file_path = Path(__file__).resolve().parent.parent.parent / 'data' / 'posts' / 'files' / file_name
                        if file_path.exists():
                            with open(file_path, 'rb') as f:
                                zip_file.writestr(post_folder + f'files/{file_name}', f.read())

        memory_file.seek(0)

        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'posts_export_{timestamp}.zip'
        )
    finally:
        db_sess.close()
