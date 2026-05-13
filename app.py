import datetime
import os
import uuid
from pathlib import Path

from flask import Flask, request, render_template, redirect, abort, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_restful import Api
from werkzeug.utils import secure_filename

from backend.forms.users_form import LoginForm, RegisterForm
from backend.forms.post_form import PostForm

# БД
from backend.database import db_session
from backend.database.models.posts_model import PostModel
from backend.database.models.users_model import UserModel
from backend.database.models.user_post_interaction import UserPostInteraction
from backend.database import default_data
from backend.database.markdown_parser import parse_markdown

# Векторная база данных
from backend.vector_db import vector_db

# API
from backend.errors import *
from backend.api import posts_api
from backend.api import interactions_api
from backend.api import posts_import_api
from backend.api import posts_metadata_api
from backend.api import auth_api
from backend.api import posts_export_api
from backend.api import comments_api
from backend.resources import posts_resources

# ==================== КОНФИГУРАЦИЯ ====================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=30)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

login_manager = LoginManager()
login_manager.init_app(app)

# Настройка обработчика unauthorized для возврата JSON для API
@login_manager.unauthorized_handler
def unauthorized_callback():
    # Проверяем, является ли запрос API-запросом
    if request.path.startswith('/api/'):
        # Возвращаем JSON-ответ для API-запросов
        # Проверим тип контента, чтобы различать JSON и multipart/form-data запросы
        content_type = request.headers.get('Content-Type', '')
        if 'application/json' in content_type or request.method == 'POST' and 'multipart/form-data' in content_type:
            return jsonify({
                'success': False,
                'error': 'Требуется авторизация'
            }), 401
        else:
            return jsonify({
                'success': False,
                'error': 'Требуется авторизация'
            }), 401
    # Для обычных запросов возвращаем стандартный обработчик
    return redirect('/login')

api = Api(app)

# Пути к файлам
PROJECT_ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = PROJECT_ROOT / 'data' / 'posts'
IMAGES_DIR = UPLOAD_DIR / 'images'
FILES_DIR = UPLOAD_DIR / 'files'

for dir_path in [UPLOAD_DIR, IMAGES_DIR, FILES_DIR, PROJECT_ROOT / 'data' / 'sql_db']:
    dir_path.mkdir(parents=True, exist_ok=True)


# ==================== ЗАГРУЗКА ПОЛЬЗОВАТЕЛЯ ====================

@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    try:
        return db_sess.get(UserModel, user_id)
    finally:
        db_sess.close()


# ==================== МАРШРУТЫ ====================

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        try:
            user = db_sess.query(UserModel).filter(
                UserModel.username == form.username.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                return redirect("/")
            return render_template('login.html',
                                   message="Неправильное имя пользователя или пароль",
                                   form=form)
        finally:
            db_sess.close()
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect("/")

    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")

        if len(form.username.data) < 3:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Имя пользователя должно быть не менее 3 символов")

        if len(form.password.data) < 6:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароль должен быть не менее 6 символов")

        db_sess = db_session.create_session()
        try:
            if db_sess.query(UserModel).filter(UserModel.username == form.username.data).first():
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message="Такой пользователь уже есть")

            user = UserModel(
                username=form.username.data,
            )
            user.set_password(form.password.data)
            db_sess.add(user)
            db_sess.commit()
            return redirect('/login')
        except Exception:
            db_sess.rollback()
            raise
        finally:
            db_sess.close()
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/')
@app.route('/index')
def index():
    db_sess = db_session.create_session()
    try:
        posts = db_sess.query(PostModel).order_by(PostModel.created_at.desc()).limit(50).all()

        # Получаем статусы взаимодействий для авторизованного пользователя
        interactions = {}
        if current_user.is_authenticated:
            user_interactions = db_sess.query(UserPostInteraction).filter_by(
                user_id=current_user.id
            ).all()
            interactions = {i.post_id: i for i in user_interactions}

        return render_template("index.html", posts=posts, interactions=interactions)
    finally:
        db_sess.close()


@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        if not form.title.data or not form.content.data:
            return render_template('create_post.html', title='Создание поста',
                                   form=form,
                                   message="Заголовок и текст обязательны")

        db_sess = db_session.create_session()
        try:
            post = PostModel()
            post.title = form.title.data
            post.content = form.content.data
            post.content_html = parse_markdown(form.content.data)
            post.author = current_user.username
            post.user_id = current_user.id
            db_sess.add(post)
            db_sess.commit()

            # Добавляем пост в векторную базу
            vector_db.sync_post(post.id, post.title, post.content, post.author)

            return redirect(url_for('post_detail', post_id=post.id))
        except Exception:
            db_sess.rollback()
            raise
        finally:
            db_sess.close()
    return render_template('create_post.html', title='Создание поста', form=form)


@app.route('/post/<int:post_id>')
def post_detail(post_id):
    db_sess = db_session.create_session()
    try:
        post = db_sess.get(PostModel, post_id)
        if not post:
            abort(404)
        return render_template('post_detail.html', post=post)
    finally:
        db_sess.close()


@app.route('/profile/<int:user_id>')
def profile(user_id):
    db_sess = db_session.create_session()
    try:
        user = db_sess.get(UserModel, user_id)
        if not user:
            abort(404)

        posts = db_sess.query(PostModel).filter_by(user_id=user.id).order_by(PostModel.created_at.desc()).all()

        # Вкладки видны только владельцу профиля
        is_owner = current_user.is_authenticated and current_user.id == user_id

        liked_posts = []
        favorite_posts = []
        read_posts = []

        if is_owner:
            # Получаем посты, которые понравились
            liked_interactions = db_sess.query(UserPostInteraction).filter_by(
                user_id=user.id, is_liked=True
            ).all()
            liked_post_ids = [i.post_id for i in liked_interactions]
            liked_posts = db_sess.query(PostModel).filter(PostModel.id.in_(liked_post_ids)).order_by(PostModel.created_at.desc()).all()

            # Получаем избранные посты
            favorite_interactions = db_sess.query(UserPostInteraction).filter_by(
                user_id=user.id, is_favorite=True
            ).all()
            favorite_post_ids = [i.post_id for i in favorite_interactions]
            favorite_posts = db_sess.query(PostModel).filter(PostModel.id.in_(favorite_post_ids)).order_by(PostModel.created_at.desc()).all()

            # Получаем прочитанные посты
            read_interactions = db_sess.query(UserPostInteraction).filter_by(
                user_id=user.id, is_read=True
            ).all()
            read_post_ids = [i.post_id for i in read_interactions]
            read_posts = db_sess.query(PostModel).filter(PostModel.id.in_(read_post_ids)).order_by(PostModel.created_at.desc()).all()

        return render_template(
            'profile.html',
            user=user,
            posts=posts,
            is_owner=is_owner,
            liked_posts=liked_posts,
            favorite_posts=favorite_posts,
            read_posts=read_posts
        )
    finally:
        db_sess.close()


@app.route('/search')
def search():
    """Страница поиска постов и авторов"""
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'posts')  # 'posts' или 'authors'

    results = None
    authors_results = []

    if query:
        if search_type == 'posts':
            # Векторный поиск постов
            vector_results = vector_db.search_posts(query, n_results=20)

            # Получаем полную информацию о постах из БД
            db_sess = db_session.create_session()
            try:
                results = []
                for vec_post in vector_results:
                    post = db_sess.get(PostModel, vec_post['id'])
                    if post:
                        results.append({
                            'id': post.id,
                            'title': vec_post['title'],
                            'author': post.author,
                            'author_id': post.user_id,
                            'content': post.content,
                            'content_preview': vec_post.get('content_preview', post.content[:200]),
                            'created_at': post.created_at,
                            'distance': vec_post['distance']
                        })
            finally:
                db_sess.close()

        elif search_type == 'authors':
            # Классический поиск авторов по имени (нестрогий)
            db_sess = db_session.create_session()
            try:
                # Используем LIKE для нестрогого поиска
                authors = db_sess.query(UserModel).filter(
                    UserModel.username.ilike(f'%{query}%')
                ).all()

                authors_results = []
                for author in authors:
                    posts_count = db_sess.query(PostModel).filter_by(user_id=author.id).count()
                    authors_results.append({
                        'id': author.id,
                        'username': author.username,
                        'created_at': author.created_at,
                        'posts_count': posts_count
                    })
            finally:
                db_sess.close()

    return render_template(
        'search.html',
        query=query,
        search_type=search_type,
        results=results,
        authors_results=authors_results
    )


# ==================== API ЗАГРУЗКИ ФАЙЛОВ ====================

@app.route('/api/upload/image', methods=['POST'])
@login_required
def api_upload_image():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Нет файла'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Пустое имя'}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    if ext not in allowed:
        return jsonify({'success': False, 'error': 'Недопустимый формат'}), 400

    unique_name = f"{uuid.uuid4()}.{ext}"
    file_path = IMAGES_DIR / unique_name
    file.save(str(file_path))

    return jsonify({
        'success': True,
        'url': f'/static/uploads/images/{unique_name}'
    })


@app.route('/api/upload/file', methods=['POST'])
@login_required
def api_upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Нет файла'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Пустое имя'}), 400

    unique_name = f"{uuid.uuid4()}.{file.filename.rsplit('.', 1)[-1].lower()}" if '.' in file.filename else uuid.uuid4().hex
    file_path = FILES_DIR / unique_name
    file.save(str(file_path))

    return jsonify({
        'success': True,
        'url': f'/static/uploads/files/{unique_name}'
    })


# ==================== СЕРВИС ФАЙЛОВ ====================

@app.route('/static/uploads/images/<filename>')
def serve_image(filename):
    return send_from_directory(IMAGES_DIR, filename)


@app.route('/static/uploads/files/<filename>')
def serve_file(filename):
    return send_from_directory(FILES_DIR, filename, as_attachment=True)


# ==================== ИНИЦИАЛИЗАЦИЯ ====================

def sync_vector_database():
    """Синхронизирует векторную базу с существующими постами"""
    db_sess = db_session.create_session()
    try:
        all_posts = db_sess.query(PostModel).all()

        synced_count = 0
        for post in all_posts:
            vector_db.sync_post(post.id, post.title or "Без заголовка", post.content, post.author)
            synced_count += 1

        print(f"[SUCCESS] Векторная база синхронизирована: {synced_count} постов")
    finally:
        db_sess.close()


def main():
    # Регистрация обработчиков ошибок
    app.register_error_handler(400, bad_request)
    app.register_error_handler(401, unauthorized)
    app.register_error_handler(403, forbidden)
    app.register_error_handler(404, not_found)
    app.register_error_handler(405, method_not_allowed)
    app.register_error_handler(406, not_acceptable)
    app.register_error_handler(408, request_timeout)
    app.register_error_handler(409, conflict)
    app.register_error_handler(410, gone)
    app.register_error_handler(411, length_required)
    app.register_error_handler(412, precondition_failed)
    app.register_error_handler(413, payload_too_large)
    app.register_error_handler(414, uri_too_long)
    app.register_error_handler(415, unsupported_media_type)
    app.register_error_handler(416, range_not_satisfiable)
    app.register_error_handler(417, expectation_failed)
    app.register_error_handler(418, im_a_teapot)
    app.register_error_handler(421, misdirected_request)
    app.register_error_handler(422, unprocessable_entity)
    app.register_error_handler(423, locked)
    app.register_error_handler(424, failed_dependency)
    app.register_error_handler(428, precondition_required)
    app.register_error_handler(429, too_many_requests)
    app.register_error_handler(431, headers_too_large)
    app.register_error_handler(451, legal_unavailable)
    app.register_error_handler(500, internal_error)
    app.register_error_handler(501, not_implemented)
    app.register_error_handler(502, bad_gateway)
    app.register_error_handler(503, service_unavailable)
    app.register_error_handler(504, gateway_timeout)
    app.register_error_handler(505, http_version_not_supported)

    db_session.global_init("data/sql_db/forum.db")
    default_data.default_data()
    
    # Синхронизируем векторную базу
    sync_vector_database()

    app.register_blueprint(posts_api.blueprint)
    app.register_blueprint(interactions_api.blueprint)
    app.register_blueprint(posts_import_api.blueprint)
    app.register_blueprint(posts_metadata_api.blueprint)
    app.register_blueprint(auth_api.blueprint)
    app.register_blueprint(posts_export_api.blueprint)
    app.register_blueprint(comments_api.blueprint)

    # Flask-RESTful ресурсы
    api.add_resource(posts_resources.PostListResource, '/api/v2/posts')
    api.add_resource(posts_resources.PostResource, '/api/v2/posts/<int:post_id>')


main()

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("[SERVER] STARTING SERVER")
    print("=" * 50)
    print("URL: http://127.0.0.1:5000")
    print("Debug: ON")
    print("=" * 50 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
