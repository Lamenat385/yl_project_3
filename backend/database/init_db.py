import sys
from pathlib import Path

from flask_login import UserMixin

# Добавляем корень проекта в sys.path для правильных импортов
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
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
class User(UserMixin, db.Model):  # ← Добавляем UserMixin
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    passwd_hash = db.Column(db.String(256), nullable=False)
    tg_id = db.Column(db.String(100), unique=True, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи
    posts = db.relationship('Post', backref='author_user', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.passwd_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.passwd_hash, password)


class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    author = db.Column(db.String(80), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    path = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=False)  # Исходный Markdown
    content_html = db.Column(db.Text, nullable=True)  # Рендеренный HTML
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)

    # Медиа (список файлов/картинок в посте)
    attached_images = db.Column(db.Text, nullable=True)  # JSON строка
    attached_files = db.Column(db.Text, nullable=True)  # JSON строка

    def __repr__(self):
        return f'<Post {self.id} by {self.author}>'

    def render_content(self) -> str:
        """Рендерит Markdown в HTML"""
        if self.content_html:
            return self.content_html
        # Если content_html нет, рендерим на лету
        from .markdown_parser import parse_markdown
        return parse_markdown(self.content)

    def set_content(self, content: str):
        """Устанавливает контент и генерирует HTML"""
        from .markdown_parser import parse_markdown
        self.content = content
        self.content_html = parse_markdown(content)

    def to_dict(self):
        return {
            'id': self.id,
            'author': self.author,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'path': self.path,
            'content': self.content,
            'content_html': self.render_content()
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