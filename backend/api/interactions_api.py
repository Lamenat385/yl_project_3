"""
API для работы с взаимодействиями пользователей с постами
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from backend.database import db_session
from backend.database.models.user_post_interaction import UserPostInteraction
from backend.recommendation import engine

blueprint = Blueprint('interactions_api', __name__)


def get_or_create_interaction(user_id, post_id):
    """Получает или создает запись взаимодействия"""
    db_sess = db_session.create_session()
    try:
        interaction = db_sess.query(UserPostInteraction).filter_by(
            user_id=user_id, post_id=post_id
        ).first()

        if not interaction:
            interaction = UserPostInteraction(user_id=user_id, post_id=post_id)
            db_sess.add(interaction)
            db_sess.commit()

        return interaction
    except Exception:
        db_sess.rollback()
        raise
    finally:
        db_sess.close()


@blueprint.route('/api/interactions/toggle', methods=['POST'])
@login_required
def toggle_interaction():
    """Универсальный эндпоинт для переключения любого типа взаимодействия"""
    data = request.json

    if not data or 'post_id' not in data or 'action' not in data:
        return jsonify({'success': False, 'error': 'Неверные данные'}), 400

    post_id = data['post_id']
    action = data['action']  # 'like', 'favorite', 'read', 'not_interested'

    # Проверка допустимых действий
    valid_actions = ['like', 'favorite', 'read', 'not_interested']
    if action not in valid_actions:
        return jsonify({'success': False, 'error': 'Недопустимое действие'}), 400

    db_sess = db_session.create_session()
    try:
        # Получаем или создаем взаимодействие в рамках одной сессии
        interaction = db_sess.query(UserPostInteraction).filter_by(
            user_id=current_user.id, post_id=post_id
        ).first()

        if not interaction:
            interaction = UserPostInteraction(user_id=current_user.id, post_id=post_id)
            db_sess.add(interaction)
            db_sess.flush()  # Получаем ID, но не коммитим ещё

        # Маппинг действий на поля
        field_map = {
            'like': 'is_liked',
            'favorite': 'is_favorite',
            'read': 'is_read',
            'not_interested': 'is_not_interested'
        }

        field_name = field_map[action]

        # Переключаем значение
        current_value = getattr(interaction, field_name)
        new_state = not current_value
        setattr(interaction, field_name, new_state)
        db_sess.commit()

        # Записываем взаимодействие в буферы рекомендаций (только активация)
        if new_state and action in ('like', 'favorite', 'read'):
            try:
                engine.record_interaction(
                    user_id=current_user.id,
                    post_id=post_id,
                    action=action,
                )
            except Exception:
                pass  # не блокируем основной ответ из-за ошибки в рекомендациях

        return jsonify({
            'success': True,
            'action': action,
            'state': new_state
        })
    except Exception:
        db_sess.rollback()
        return jsonify({'success': False, 'error': 'Ошибка сервера'}), 500
    finally:
        db_sess.close()


@blueprint.route('/api/interactions/post/<int:post_id>/status', methods=['GET'])
@login_required
def get_post_interaction_status(post_id):
    """Получить статус всех взаимодействий для поста"""
    db_sess = db_session.create_session()
    try:
        interaction = db_sess.query(UserPostInteraction).filter_by(
            user_id=current_user.id, post_id=post_id
        ).first()

        if not interaction:
            return jsonify({
                'is_liked': False,
                'is_favorite': False,
                'is_read': False,
                'is_not_interested': False
            })

        return jsonify({
            'is_liked': interaction.is_liked,
            'is_favorite': interaction.is_favorite,
            'is_read': interaction.is_read,
            'is_not_interested': interaction.is_not_interested
        })
    finally:
        db_sess.close()


@blueprint.route('/api/interactions/user/<int:user_id>/liked', methods=['GET'])
@login_required
def get_user_liked_posts(user_id):
    """Получить все посты, которые понравились пользователю"""
    if current_user.id != user_id:
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    db_sess = db_session.create_session()
    try:
        interactions = db_sess.query(UserPostInteraction).filter_by(
            user_id=user_id, is_liked=True
        ).all()

        post_ids = [i.post_id for i in interactions]
        return jsonify({'post_ids': post_ids})
    finally:
        db_sess.close()


@blueprint.route('/api/interactions/user/<int:user_id>/favorites', methods=['GET'])
@login_required
def get_user_favorites(user_id):
    """Получить все избранные посты пользователя"""
    if current_user.id != user_id:
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    db_sess = db_session.create_session()
    try:
        interactions = db_sess.query(UserPostInteraction).filter_by(
            user_id=user_id, is_favorite=True
        ).all()

        post_ids = [i.post_id for i in interactions]
        return jsonify({'post_ids': post_ids})
    finally:
        db_sess.close()


@blueprint.route('/api/interactions/user/<int:user_id>/read', methods=['GET'])
@login_required
def get_user_read_posts(user_id):
    """Получить все прочитанные посты пользователя"""
    if current_user.id != user_id:
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    db_sess = db_session.create_session()
    try:
        interactions = db_sess.query(UserPostInteraction).filter_by(
            user_id=user_id, is_read=True
        ).all()

        post_ids = [i.post_id for i in interactions]
        return jsonify({'post_ids': post_ids})
    finally:
        db_sess.close()
