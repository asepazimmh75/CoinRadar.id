from dotenv import load_dotenv

load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
from datetime import datetime


MONGODB_URI = os.environ["MONGODB_URI"]
DB_NAME = os.environ["DB_NAME"]

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

app = Flask(__name__)

app.secret_key = bytes.fromhex(os.environ['SECRET_KEY'])

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('About.html')

@app.route('/contact')
def contact():
    return render_template('Contact.html')

@app.route('/adminpage')
def dashboard():
    return render_template('AdminPage.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Cek apakah user ada dalam database
        user = db.users.find_one({'username': username})

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        avatar = request.form.get('avatar')  # Menyimpan avatar jika ada

        # Validasi input
        if not username or not email or not password:
            flash("Please fill in all fields.", 'danger')
            return redirect(url_for('signup'))

        # Hash password sebelum disimpan
        hashed_password = generate_password_hash(password)

        # Simpan data pengguna ke MongoDB
        db.users.insert_one({
            'username': username,
            'email': email,
            'password': hashed_password,
            'avatar': avatar
        })
        
        flash('Signup successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/publish', methods=['GET', 'POST'])
def publish_article():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        
        # Mengelola file thumbnail (jika ada)
        if 'thumbnail' in request.files:
            thumbnail_file = request.files['thumbnail']
            if thumbnail_file and allowed_file(thumbnail_file.filename):
                filename = secure_filename(thumbnail_file.filename)
                thumbnail_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                thumbnail_path = f'uploads/{filename}'
            else:
                thumbnail_path = None
        else:
            thumbnail_path = None

        # Buat tanggal publikasi secara otomatis
        published_at = datetime.now()

        # Simpan data artikel ke MongoDB
        db.articles.insert_one({
            'title': title,
            'description': description,
            'category': category,
            'thumbnail': thumbnail_path,
            'published_at': published_at  # Tanggal otomatis
        })

        flash('Article published successfully!', 'success')
        return redirect(url_for('publish_article'))

    return render_template('publish.html')

def allowed_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/singlepage')
def singlepage():
    return render_template('singlepage.html')

@app.route('/articles', methods=['GET'])
def get_articles():
    articles = list(db.articles.find({}, {'_id': 0}))  # Ambil semua artikel dari MongoDB, tanpa menyertakan `_id`.
    return {'articles': articles}, 200

@app.route('/update_article/<string:title>', methods=['GET', 'POST'])
def update_article(title):
    if request.method == 'POST':
        # Ambil data dari form
        new_title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        
        # Perbarui data di MongoDB
        db.articles.update_one(
            {'title': title},  # Cari berdasarkan judul lama
            {'$set': {
                'title': new_title,
                'description': description,
                'category': category,
                'updated_at': datetime.now()
            }}
        )
        flash('Article updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    # Ambil artikel untuk di-update berdasarkan judul
    article = db.articles.find_one({'title': title})
    return render_template('update.html', article=article)


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)