"""
API для авторизации пользователей
"""

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash

from backend.database import db_session
from backend.database.models.users_model import UserModel
from flask_login import login_user

blueprint = Blueprint('auth_api', __name__)


@blueprint.route('/api/v1/auth/login', methods=['POST'])
def login():
    """
    Вход в систему по username и password.

    Тело запроса (JSON):
    {
        "username": "username",
        "password": "password"
    }

    Возвращает:
    {
        "success": true,
        "user_id": 1,
        "username": "username",
        "message": "Успешный вход"
    }

    Статусы:
    200 - Успешный вход
    400 - Неверный запрос (отсутствуют username или password)
    401 - Неверный пароль
    """
    if not request.is_json:
        return jsonify({
            'success': False,
            'error': 'Требуется JSON в теле запроса'
        }), 400

    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({
            'success': False,
            'error': 'Требуются поля "username" и "password"'
        }), 400

    username = data['username']
    password = data['password']

    db_sess = db_session.create_session()
    try:
        user = db_sess.query(UserModel).filter(UserModel.username == username).first()
        if not user:
            return jsonify({
                'success': False,
                'error': 'Пользователь не найден'
            }), 401

        if not user.check_password(password):
            return jsonify({
                'success': False,
                'error': 'Неверный пароль'
            }), 401

        # Вход в систему
        login_user(user)

        return jsonify({
            'success': True,
            'user_id': user.id,
            'username': user.username,
            'message': 'Успешный вход'
        })
    finally:
        db_sess.close()


@blueprint.route('/api/v1/auth/logout', methods=['POST'])
def logout():
    """
    Выход из системы.

    Возвращает:
    {
        "success": true,
        "message": "Успешный выход"
    }
    """
    from flask_login import logout_user
    logout_user()

    return jsonify({
        'success': True,
        'message': 'Успешный выход'
    })


@blueprint.route('/api/v1/auth/status', methods=['GET'])
def auth_status():
    """
    Проверка статуса авторизации.

    Возвращает:
    {
        "is_authenticated": true,
        "user_id": 1,
        "username": "username"
    }
    """
    from flask_login import current_user

    if current_user.is_authenticated:
        return jsonify({
            'is_authenticated': True,
            'user_id': current_user.id,
            'username': current_user.username
        })
    else:
        return jsonify({
            'is_authenticated': False
        })
