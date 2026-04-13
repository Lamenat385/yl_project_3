import flask
from flask import jsonify, make_response, request
from flask_login import current_user, login_required

from backend.database import db_session
from backend.database.models.posts_model import PostModel
from backend.database.models.users_model import UserModel

blueprint = flask.Blueprint(
    'posts_api',
    __name__,
    template_folder='templates'
)


@blueprint.route('/api/posts')
def get_posts():
    db_sess = db_session.create_session()
    try:
        posts = db_sess.query(PostModel).order_by(PostModel.created_at.desc()).limit(20).all()
        return jsonify(
            {
                'posts':
                    [item.to_dict(only=('title', 'content', 'author', 'created_at'))
                     for item in posts]
            }
        )
    finally:
        db_sess.close()


@blueprint.route('/api/posts/<int:post_id>', methods=['GET'])
def get_one_post(post_id):
    db_sess = db_session.create_session()
    try:
        post = db_sess.get(PostModel, post_id)
        if not post:
            return make_response(jsonify({'error': 'Not found'}), 404)
        return jsonify(
            {
                'post': post.to_dict(only=(
                    'title', 'content', 'content_html', 'author', 'user_id', 'created_at'))
            }
        )
    finally:
        db_sess.close()


@blueprint.route('/api/posts', methods=['POST'])
@login_required
def create_post():
    if not request.json:
        return make_response(jsonify({'error': 'Empty request'}), 400)
    elif not all(key in request.json for key in ['title', 'content']):
        return make_response(jsonify({'error': 'Bad request'}), 400)

    from backend.database.markdown_parser import parse_markdown

    db_sess = db_session.create_session()
    try:
        post = PostModel(
            title=request.json['title'],
            content=request.json['content'],
            content_html=parse_markdown(request.json['content']),
            author=current_user.username,
            user_id=current_user.id
        )
        db_sess.add(post)
        db_sess.commit()
        return jsonify({'id': post.id})
    except Exception:
        db_sess.rollback()
        raise
    finally:
        db_sess.close()


@blueprint.route('/api/posts/<int:post_id>', methods=['DELETE'])
@login_required
def delete_post(post_id):
    db_sess = db_session.create_session()
    try:
        post = db_sess.query(PostModel).filter(
            PostModel.id == post_id,
            PostModel.user_id == current_user.id
        ).first()
        if not post:
            return make_response(jsonify({'error': 'Not found'}), 404)
        db_sess.delete(post)
        db_sess.commit()
        return jsonify({'success': 'OK'})
    except Exception:
        db_sess.rollback()
        raise
    finally:
        db_sess.close()
