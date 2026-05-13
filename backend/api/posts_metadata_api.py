"""
API для получения метаданных постов и управления избранным
"""

import datetime
from flask import Blueprint, jsonify, request, send_file
from flask_login import login_required, current_user

from backend.database import db_session
from backend.database.models.posts_model import PostModel
from backend.database.models.users_model import UserModel
from backend.database.models.user_post_interaction import UserPostInteraction

import io
import json
import zipfile
from pathlib import Path

blueprint = Blueprint('posts_metadata_api', __name__)


@blueprint.route('/api/v1/posts/<int:post_id>/metadata', methods=['GET'])
def get_post_metadata(post_id):
    """
    Получение метаданных поста по id.
    
    Возвращает:
    {
        "id": 123,
        "title": "Название поста",
        "author": "username",
        "author_id": 1,
        "created_at": "2025-05-06 10:30:00",
        "updated_at": "2025-05-06 10:30:00",
        "content_length": 1234,
        "has_images": true,
        "has_files": true,
        "attached_images": ["image1.jpg", "image2.jpg"],
        "attached_files": ["document.pdf"]
    }
    """
    db_sess = db_session.create_session()
    try:
        post = db_sess.get(PostModel, post_id)
        if not post:
            return jsonify({
                'success': False,
                'error': 'Пост не найден'
            }), 404
        
        metadata = {
            'success': True,
            'id': post.id,
            'title': post.title,
            'author': post.author,
            'author_id': post.user_id,
            'created_at': post.created_at.isoformat() if post.created_at else None,
            'updated_at': post.updated_at.isoformat() if post.updated_at else None,
            'content_length': len(post.content) if post.content else 0,
            'has_images': bool(post.attached_images),
            'has_files': bool(post.attached_files),
            'attached_images': post.attached_images.split(',') if post.attached_images else [],
            'attached_files': post.attached_files.split(',') if post.attached_files else []
        }
        
        return jsonify(metadata)
    finally:
        db_sess.close()


@blueprint.route('/api/v1/users/<username>/favorites/export', methods=['POST'])
def export_user_favorites(username):
    """
    Экспорт всех избранных постов пользователя в zip-архив.
    
    Тело запроса (JSON):
    {
        "password": "user_password"
    }
    
    Возвращает: zip-архив с постами в формате:
    username_favorites.zip
    └── posts/
        ├── post_1/
        │   ├── post.md
        │   ├── images/
        │   └── files/
        ├── post_2/
        │   └── ...
        └── ...
    
    Статусы:
    200 - Успешный экспорт
    401 - Неверный пароль
    403 - Пользователь не найден или посты не найдены
    """
    if not request.is_json:
        return jsonify({
            'success': False,
            'error': 'Требуется JSON в теле запроса'
        }), 400
    
    data = request.get_json()
    if not data or 'password' not in data:
        return jsonify({
            'success': False,
            'error': 'Требуется поле "password" в JSON'
        }), 400
    
    password = data['password']
    
    db_sess = db_session.create_session()
    try:
        # Ищем пользователя по username
        user = db_sess.query(UserModel).filter(UserModel.username == username).first()
        if not user:
            return jsonify({
                'success': False,
                'error': 'Пользователь не найден'
            }), 403
        
        # Проверяем пароль
        if not user.check_password(password):
            return jsonify({
                'success': False,
                'error': 'Неверный пароль'
            }), 401
        
        # Получаем избранные посты
        favorite_interactions = db_sess.query(UserPostInteraction).filter_by(
            user_id=user.id, is_favorite=True
        ).all()
        
        if not favorite_interactions:
            return jsonify({
                'success': False,
                'error': 'У пользователя нет избранных постов'
            }), 403
        
        favorite_post_ids = [i.post_id for i in favorite_interactions]
        posts = db_sess.query(PostModel).filter(PostModel.id.in_(favorite_post_ids)).all()
        
        if not posts:
            return jsonify({
                'success': False,
                'error': 'Избранные посты не найдены'
            }), 403
        
        # Создаем zip-архив в памяти
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Добавляем файл с метаданными
            metadata = {
                'username': username,
                'user_id': user.id,
                'export_date': str(datetime.datetime.now()),
                'posts_count': len(posts),
                'posts': []
            }
            
            for post in posts:
                post_folder = f'posts/post_{post.id}/'
                
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
                
                # Добавляем метаданные поста
                metadata['posts'].append({
                    'id': post.id,
                    'title': post.title,
                    'created_at': post.created_at.isoformat() if post.created_at else None,
                    'has_images': bool(post.attached_images),
                    'has_files': bool(post.attached_files)
                })
            
            # Добавляем общий metadata.json
            zip_file.writestr('metadata.json', json.dumps(metadata, indent=2, ensure_ascii=False))
        
        memory_file.seek(0)
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{username}_favorites.zip'
        )
    finally:
        db_sess.close()
