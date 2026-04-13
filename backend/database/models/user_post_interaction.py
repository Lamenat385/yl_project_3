import datetime
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from ..db_session import SqlAlchemyBase


class UserPostInteraction(SqlAlchemyBase, SerializerMixin):
    """Модель для хранения взаимодействий пользователя с постами"""
    
    __tablename__ = 'user_post_interactions'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    
    # ID пользователя
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"), nullable=False, index=True)
    
    # ID поста
    post_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("posts.id"), nullable=False, index=True)
    
    # Флаги взаимодействий
    is_liked = sqlalchemy.Column(sqlalchemy.Boolean, default=False, nullable=False)
    is_favorite = sqlalchemy.Column(sqlalchemy.Boolean, default=False, nullable=False)
    is_read = sqlalchemy.Column(sqlalchemy.Boolean, default=False, nullable=False)
    is_not_interested = sqlalchemy.Column(sqlalchemy.Boolean, default=False, nullable=False)
    
    # Дата создания и обновления
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)
    updated_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    
    # Связи
    user = orm.relationship('UserModel', foreign_keys=[user_id])
    post = orm.relationship('PostModel', foreign_keys=[post_id])
    
    # Уникальная комбинация user_id + post_id
    __table_args__ = (
        sqlalchemy.UniqueConstraint('user_id', 'post_id', name='uq_user_post'),
    )

    def __repr__(self):
        return f'<UserPostInteraction user={self.user_id} post={self.post_id}>'
