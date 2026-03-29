import os
import sys
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import uuid

# ==================== ПУТИ И ИМПОРТЫ ====================

# Добавляем корень проекта в PATH для корректных импортов
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

print("🔍 Инициализация приложения...")
print(f"📁 Корень проекта: {PROJECT_ROOT}")

# Импортируем БД
try:
    from backend.database.init_db import db, User, Post, init_database
    from backend.database.markdown_parser import parse_markdown

    print("✅ БД импортирована успешно")
except Exception as e:
    print(f"❌ Ошибка импорта БД: {e}")
    sys.exit(1)

# ==================== КОНФИГУРАЦИЯ ====================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{PROJECT_ROOT}/data/sql_db/forum.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Инициализация расширений
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Войдите для доступа'

print("✅ Конфигурация завершена")

# ==================== ПУТИ К ФАЙЛАМ ====================

UPLOAD_DIR = PROJECT_ROOT / 'data' / 'posts'
IMAGES_DIR = UPLOAD_DIR / 'images'
FILES_DIR = UPLOAD_DIR / 'files'

# Создаём директории
for dir_path in [UPLOAD_DIR, IMAGES_DIR, FILES_DIR, PROJECT_ROOT / 'data' / 'sql_db']:
    dir_path.mkdir(parents=True, exist_ok=True)

print("✅ Директории созданы")


# ==================== ЗАГРУЗКА ПОЛЬЗОВАТЕЛЯ ====================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==================== МАРШРУТЫ ====================

@app.route('/')
def index():
    posts = Post.query.order_by(Post.created_at.desc()).limit(20).all()
    return render_template('index.html', posts=posts)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Валидация
        if not username or not password:
            flash('Имя пользователя и пароль обязательны', 'danger')
            return redirect(url_for('register'))

        if len(username) < 3:
            flash('Имя пользователя должно быть не менее 3 символов', 'danger')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('Пароль должен быть не менее 6 символов', 'danger')
            return redirect(url_for('register'))

        # Проверка на существование
        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято', 'danger')
            return redirect(url_for('register'))

        # Создание пользователя
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Регистрация успешна! Теперь войдите.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')  # Было email
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()  # Ищем по username

        if user and user.check_password(password):
            login_user(user)
            flash('Вы вошли!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))

        flash('Неверное имя пользователя или пароль', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли', 'info')
    return redirect(url_for('index'))


@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')

        if not title or not content:
            flash('Заголовок и текст обязательны', 'danger')
            return redirect(url_for('new_post'))

        post = Post(
            author=current_user.username,
            content=content,
            content_html=parse_markdown(content),
            user_id=current_user.id
        )
        db.session.add(post)
        db.session.commit()

        flash('Пост опубликован!', 'success')
        return redirect(url_for('post_detail', post_id=post.id))

    return render_template('create_post.html')


@app.route('/post/<int:post_id>')
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post_detail.html', post=post)


@app.route('/profile/<int:user_id>')
def profile(user_id):
    user = User.query.get_or_404(user_id)
    posts = Post.query.filter_by(user_id=user.id).order_by(Post.created_at.desc()).all()
    return render_template('profile.html', user=user, posts=posts)


# ==================== API ЗАГРУЗКИ ====================

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
        'url': f'/data/posts/images/{unique_name}'
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
        'url': f'/data/posts/files/{unique_name}'
    })


# ==================== СЕРВИС ФАЙЛОВ ====================

@app.route('/data/posts/images/<filename>')
def serve_image(filename):
    return send_from_directory(IMAGES_DIR, filename)


@app.route('/data/posts/files/<filename>')
def serve_file(filename):
    return send_from_directory(FILES_DIR, filename, as_attachment=True)


# ==================== ИНИЦИАЛИЗАЦИЯ БД ====================

with app.app_context():
    try:
        db.create_all()
        print("✅ Таблицы БД созданы/проверены")
    except Exception as e:
        print(f"❌ Ошибка БД: {e}")

# ==================== ЗАПУСК СЕРВЕРА ====================

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("🚀 ЗАПУСК СЕРВЕРА")
    print("=" * 50)
    print("📍 URL: http://127.0.0.1:5000")
    print("🔧 Debug: ON")
    print("=" * 50 + "\n")

    app.run(debug=True, host='127.0.0.1', port=5000)