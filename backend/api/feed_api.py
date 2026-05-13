"""
API для бесконечной ленты рекомендаций (Infinite Scroll Feed).
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from backend.recommendation import engine

blueprint = Blueprint('feed_api', __name__)


@blueprint.route('/api/feed', methods=['GET'])
@login_required
def get_feed():
    """
    Возвращает батч постов для бесконечной ленты.

    Query params:
        batch_size  (int)  — кол-во постов в батче (1..50, по умолчанию 10)
        exclude_ids (str)  — CSV-строка с ID уже показанных постов

    Returns:
        JSON: { "success": true, "posts": [...], "has_more": bool }
    """
    batch_size = request.args.get('batch_size', 10, type=int)
    batch_size = max(1, min(batch_size, 50))

    exclude_ids_str = request.args.get('exclude_ids', '')
    exclude_ids = set()
    if exclude_ids_str:
        try:
            exclude_ids = {int(x.strip()) for x in exclude_ids_str.split(',') if x.strip()}
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid exclude_ids format'}), 400

    posts = engine.generate_feed_batch(
        user_id=current_user.id,
        batch_size=batch_size,
        initial_exclude_ids=exclude_ids,
    )

    return jsonify({
        'success': True,
        'posts': posts,
        'has_more': len(posts) == batch_size,
    })


@blueprint.route('/api/feed/record', methods=['POST'])
@login_required
def record_interaction():
    """
    Записывает взаимодействие пользователя с постом в буферы рекомендаций.

    Body (JSON):
        post_id (int)  — ID поста
        action  (str)  — 'read', 'like' или 'favorite'
    """
    data = request.get_json(silent=True) or {}
    post_id = data.get('post_id')
    action = data.get('action')

    if not post_id or not action:
        return jsonify({'success': False, 'error': 'Missing post_id or action'}), 400

    if action not in ('read', 'like', 'favorite'):
        return jsonify({
            'success': False,
            'error': f"Invalid action '{action}'. Must be: read, like, favorite"
        }), 400

    engine.record_interaction(
        user_id=current_user.id,
        post_id=int(post_id),
        action=action,
    )

    return jsonify({'success': True})
