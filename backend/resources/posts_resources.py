from flask import jsonify
from flask_restful import reqparse, abort, Resource
from flask_login import current_user, login_required

from backend.database import db_session
from backend.database.models.posts_model import PostModel
from backend.database.markdown_parser import parse_markdown


def abort_if_post_not_found(post_id):
    session = db_session.create_session()
    try:
        post = session.query(PostModel).get(post_id)
        if not post:
            abort(404, message=f"Post {post_id} not found")
    finally:
        session.close()


class PostResource(Resource):
    def get(self, post_id):
        abort_if_post_not_found(post_id)
        session = db_session.create_session()
        try:
            post = session.get(PostModel, post_id)
            return jsonify({'post': post.to_dict(
                only=('title', 'content', 'content_html', 'author', 'user_id', 'created_at'))})
        finally:
            session.close()

    def delete(self, post_id):
        abort_if_post_not_found(post_id)
        session = db_session.create_session()
        try:
            post = session.query(PostModel).filter(
                PostModel.id == post_id,
                PostModel.user_id == current_user.id
            ).first()
            if not post:
                abort(403, message="You can only delete your own posts")
            session.delete(post)
            session.commit()
            return jsonify({'success': 'OK'})
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


class PostListResource(Resource):
    def get(self):
        session = db_session.create_session()
        try:
            posts = session.query(PostModel).order_by(PostModel.created_at.desc()).limit(20).all()
            return jsonify({'posts': [item.to_dict(
                only=('title', 'content', 'author', 'created_at')) for item in posts]})
        finally:
            session.close()

    @login_required
    def post(self):
        args = parser.parse_args()
        session = db_session.create_session()
        try:
            post = PostModel(
                title=args['title'],
                content=args['content'],
                content_html=parse_markdown(args['content']),
                author=current_user.username,
                user_id=current_user.id
            )
            session.add(post)
            session.commit()
            return jsonify({'id': post.id})
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


parser = reqparse.RequestParser()
parser.add_argument('title', required=True)
parser.add_argument('content', required=True)
