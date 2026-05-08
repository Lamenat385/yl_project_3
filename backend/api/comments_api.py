"""
API для работы с комментариями к постам
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from backend.database import db_session
from backend.database.models.comments_model import CommentModel
from backend.database.models.posts_model import PostModel
from backend.database.models.user_post_interaction import UserPostInteraction
from backend.database.markdown_parser import parse_markdown

blueprint = Blueprint('comments_api', __name__)


@blueprint.route('/api/v1/posts/<int:post_id>/comments', methods=['GET'])
def get_comments(post_id):
    """
    Получить все комментарии к посту.
    
    Возвращает:
    {
        "comments": [
            {
                "id": 1,
                "user_id": 1,
                "username": "username",
                "content": "Текст комментария",
                "content_html": "<p>Текст комментария</p>",
                "likes_count": 5,
                "created_at": "2025-05-08 10:30:00"
            }
        ]
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
        
        comments = db_sess.query(CommentModel).filter_by(post_id=post_id).order_by(CommentModel.created_at.desc()).all()
        
        comments_list = []
        for comment in comments:
            comments_list.append({
                'id': comment.id,
                'user_id': comment.user_id,
                'username': comment.user.username if comment.user else 'Аноним',
                'content': comment.content,
                'content_html': comment.content_html or parse_markdown(comment.content),
                'likes_count': comment.likes_count,
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return jsonify({
            'success': True,
            'comments': comments_list
        })
    finally:
        db_sess.close()


@blueprint.route('/api/v1/posts/<int:post_id>/comments', methods=['POST'])
@login_required
def add_comment(post_id):
    """
    Добавить комментарий к посту.
    
    Тело запроса (JSON):
    {
        "content": "Текст комментария"
    }
    
    Возвращает:
    {
        "success": true,
        "comment": {
            "id": 1,
            "user_id": 1,
            "username": "username",
            "content": "Текст комментария",
            "content_html": "<p>Текст комментария</p>",
            "likes_count": 0,
            "created_at": "2025-05-08 10:30:00"
        }
    }
    """
    if not request.is_json:
        return jsonify({
            'success': False,
            'error': 'Требуется JSON в теле запроса'
        }), 400
    
    data = request.get_json()
    if not data or 'content' not in data or not data['content'].strip():
        return jsonify({
            'success': False,
            'error': 'Требуется поле "content" с текстом комментария'
        }), 400
    
    db_sess = db_session.create_session()
    try:
        post = db_sess.get(PostModel, post_id)
        if not post:
            return jsonify({
                'success': False,
                'error': 'Пост не найден'
            }), 404
        
        comment = CommentModel(
            post_id=post_id,
            user_id=current_user.id,
            content=data['content'].strip(),
            content_html=parse_markdown(data['content'].strip())
        )
        
        db_sess.add(comment)
        db_sess.commit()
        
        return jsonify({
            'success': True,
            'comment': {
                'id': comment.id,
                'user_id': comment.user_id,
                'username': current_user.username,
                'content': comment.content,
                'content_html': comment.content_html,
                'likes_count': comment.likes_count,
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        }), 201
    except Exception as e:
        db_sess.rollback()
        return jsonify({
            'success': False,
            'error': f'Ошибка при добавлении комментария: {str(e)}'
        }), 500
    finally:
        db_sess.close()


@blueprint.route('/api/v1/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """
    Удалить комментарий.
    
    Возвращает:
    {
        "success": true
    }
    """
    db_sess = db_session.create_session()
    try:
        comment = db_sess.get(CommentModel, comment_id)
        if not comment:
            return jsonify({
                'success': False,
                'error': 'Комментарий не найден'
            }), 404
        
        # Проверяем, что пользователь является автором комментария
        if comment.user_id != current_user.id:
            return jsonify({
                'success': False,
                'error': 'У вас нет прав для удаления этого комментария'
            }), 403
        
        db_sess.delete(comment)
        db_sess.commit()
        
        return jsonify({
            'success': True
        })
    except Exception as e:
        db_sess.rollback()
        return jsonify({
            'success': False,
            'error': f'Ошибка при удалении комментария: {str(e)}'
        }), 500
    finally:
        db_sess.close()


@blueprint.route('/api/v1/comments/<int:comment_id>/like', methods=['POST'])
@login_required
def like_comment(comment_id):
    """
    Поставить лайк комментарию.
    
    Возвращает:
    {
        "success": true,
        "likes_count": 5
    }
    """
    db_sess = db_session.create_session()
    try:
        comment = db_sess.get(CommentModel, comment_id)
        if not comment:
            return jsonify({
                'success': False,
                'error': 'Комментарий не найден'
            }), 404
        
        # Проверяем, ставил ли пользователь лайк ранее
        interaction = db_sess.query(UserPostInteraction).filter_by(
            user_id=current_user.id,
            post_id=comment.post_id,
            is_liked=True
        ).first()
        
        if not interaction:
            interaction = UserPostInteraction(
                user_id=current_user.id,
                post_id=comment.post_id,
                is_liked=True
            )
            db_sess.add(interaction)
            comment.likes_count += 1
        else:
            # Убираем лайк
            interaction.is_liked = False
            comment.likes_count -= 1
        
        db_sess.commit()
        
        return jsonify({
            'success': True,
            'likes_count': comment.likes_count
        })
    except Exception as e:
        db_sess.rollback()
        return jsonify({
            'success': False,
            'error': f'Ошибка при лайке комментария: {str(e)}'
        }), 500
    finally:
        db_sess.close()


@blueprint.route('/api/v1/posts/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    """
    Поставить лайк посту.
    
    Возвращает:
    {
        "success": true,
        "likes_count": 5
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
        
        # Проверяем, ставил ли пользователь лайк ранее
        interaction = db_sess.query(UserPostInteraction).filter_by(
            user_id=current_user.id,
            post_id=post_id,
            is_liked=True
        ).first()
        
        if not interaction:
            interaction = UserPostInteraction(
                user_id=current_user.id,
                post_id=post_id,
                is_liked=True
            )
            db_sess.add(interaction)
            post.likes_count += 1
        else:
            # Убираем лайк
            interaction.is_liked = False
            post.likes_count -= 1
        
        db_sess.commit()
        
        return jsonify({
            'success': True,
            'likes_count': post.likes_count
        })
    except Exception as e:
        db_sess.rollback()
        return jsonify({
            'success': False,
            'error': f'Ошибка при лайке поста: {str(e)}'
        }), 500
    finally:
        db_sess.close()
