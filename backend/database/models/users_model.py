import datetime
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from ..db_session import SqlAlchemyBase
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class UserModel(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    username = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False, index=True)
    passwd_hash = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    tg_id = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=True, index=True)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)

    posts = orm.relationship("PostModel", back_populates='user', cascade='all, delete-orphan')

    def set_password(self, password):
        self.passwd_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.passwd_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'
