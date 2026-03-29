from .init_db import db, app, Post
from .markdown_parser import parse_markdown
from datetime import datetime


def create_post(author: str, content: str, path: str = None, user_id: int = None) -> int:
    """
    Создаёт новый пост в БД.

    Returns:
        int: ID созданного поста или 0 при ошибке
    """
    try:
        with app.app_context():
            if not author or not content:
                return 0

            new_post = Post(
                author=author,
                content=content,
                content_html=parse_markdown(content),
                path=path,
                user_id=user_id,
                created_at=datetime.utcnow()
            )

            db.session.add(new_post)
            db.session.commit()
            return new_post.id

    except Exception as e:
        db.session.rollback()
        print(f"❌ Ошибка создания поста: {e}")
        return 0