import sys
from pathlib import Path

# Добавляем корень проекта в sys.path для правильных импортов
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from datetime import datetime

# 1. Конфигурация приложения
app = Flask(__name__)

# Путь к БД: data/sql_db/forum.db от корня проекта
db_dir = project_root / 'data' / 'sql_db'
db_dir.mkdir(parents=True, exist_ok=True)  # Создаём директорию если нет

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_dir}/forum.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# 2. ORM Модель
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    passwd_hash = db.Column(db.String(256), nullable=False)
    tg_id = db.Column(db.String(100), unique=True, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        """Хеширование пароля"""
        self.passwd_hash = generate_password_hash(password)

    def check_password(self, password):
        """Проверка пароля"""
        from werkzeug.security import check_password_hash
        return check_password_hash(self.passwd_hash, password)


class Post(db.Model):
    __tablename__ = 'posts'

    # Уникальный ид поста (PRIMARY KEY)
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Автор (ссылка на таблицу users)
    author = db.Column(db.String(80), nullable=False, index=True)

    # Дата + время создания
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Путь (строка неопределённой длины, пока не используется)
    path = db.Column(db.Text, nullable=True)

    # Текст поста
    content = db.Column(db.Text, nullable=False)

    # Связь с пользователем (опционально, для удобства)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)

    def __repr__(self):
        return f'<Post {self.id} by {self.author}>'

    def to_dict(self):
        """Сериализация в словарь"""
        return {
            'id': self.id,
            'author': self.author,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'path': self.path,
            'content': self.content
        }

# 3. Инициализация БД
def init_database():
    """Создание всех таблиц в БД"""
    with app.app_context():
        db.create_all()
        print(f"✅ База данных: {db_dir}/forum.db")
        print("✅ Таблицы 'users' и 'posts' созданы!")

        # Вывод структуры таблиц
        inspector = db.inspect(db.engine)
        for table_name in ['users', 'posts']:
            print(f"\n📋 Таблица '{table_name}':")
            columns = inspector.get_columns(table_name)
            for col in columns:
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                print(f"   - {col['name']}: {col['type']} ({nullable})")


if __name__ == '__main__':
    init_database()