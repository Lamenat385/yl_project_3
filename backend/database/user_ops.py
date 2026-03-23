from .init_db import db, User
from werkzeug.security import generate_password_hash


def register_user(username: str, password: str) -> bool:
    """
    Регистрирует нового пользователя в БД.

    Args:
        username: Имя пользователя (должно быть уникальным)
        password: Пароль (будет захеширован)

    Returns:
        bool: True если регистрация успешна, False если username занят или ошибка
    """
    try:
        # Проверка на существование пользователя
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"⚠️ Пользователь '{username}' уже существует")
            return False

        # Создание нового пользователя
        new_user = User(
            username=username,
            passwd_hash=generate_password_hash(password),
            tg_id=None  # NULL в БД
        )

        db.session.add(new_user)
        db.session.commit()
        print(f"✅ Пользователь '{username}' успешно зарегистрирован")
        return True

    except Exception as e:
        db.session.rollback()
        print(f"❌ Ошибка при регистрации: {e}")
        return False