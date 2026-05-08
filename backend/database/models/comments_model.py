import datetime
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from ..db_session import SqlAlchemyBase


class CommentModel(SqlAlchemyBase, SerializerMixin):
    """Модель для хранения комментариев к постам"""

    __tablename__ = 'comments'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)

    # ID поста, к которому оставлен комментарий
    post_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("posts.id"), nullable=False, index=True)

    # ID пользователя, оставившего комментарий
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"), nullable=False, index=True)

    # Текст комментария
    content = sqlalchemy.Column(sqlalchemy.Text, nullable=False)

    # HTML-версия комментария (после парсинга Markdown)
    content_html = sqlalchemy.Column(sqlalchemy.Text, nullable=True)

    # Количество лайков на комментарии
    likes_count = sqlalchemy.Column(sqlalchemy.Integer, default=0, nullable=False)

    # Дата создания и обновления
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now, index=True)
    updated_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    # Связи
    user = orm.relationship('UserModel', foreign_keys=[user_id])
    post = orm.relationship('PostModel', foreign_keys=[post_id], back_populates='comments')

    def __repr__(self):
        return f'<Comment {self.id} by {self.user_id} on post {self.post_id}>'
