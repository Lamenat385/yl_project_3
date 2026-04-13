import datetime
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from ..db_session import SqlAlchemyBase


class PostModel(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'posts'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    author = sqlalchemy.Column(sqlalchemy.String, nullable=False, index=True)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    content = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    content_html = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now, index=True)
    updated_at = sqlalchemy.Column(sqlalchemy.DateTime, onupdate=datetime.datetime.now)
    path = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    attached_images = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    attached_files = sqlalchemy.Column(sqlalchemy.Text, nullable=True)

    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"), nullable=True, index=True)
    user = orm.relationship('UserModel')

    def render_content(self) -> str:
        """Рендерит Markdown в HTML"""
        if self.content_html:
            return self.content_html
        from backend.database.markdown_parser import parse_markdown
        return parse_markdown(self.content)

    def set_content(self, content: str):
        """Устанавливает контент и генерирует HTML"""
        from backend.database.markdown_parser import parse_markdown
        self.content = content
        from backend.database.markdown_parser import parse_markdown
        self.content_html = parse_markdown(content)

    def __repr__(self):
        return f'<Post {self.id} by {self.author}>'
