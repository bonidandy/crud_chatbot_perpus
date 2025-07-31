import os
from flask import Flask, render_template, request, url_for, flash, session, redirect
from flask_mysqldb import MySQL
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from dotenv import load_dotenv

# Memuat variabel lingkungan dari .env
load_dotenv()

app = Flask(__name__)
app.secret_key = 'many random bytes'

# Konfigurasi database menggunakan variabel lingkungan dari Railway
app.config['MYSQL_HOST'] = os.getenv('DB_HOST')
app.config['MYSQL_USER'] = os.getenv('DB_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('DB_PASSWORD') 
app.config['MYSQL_DB'] = os.getenv('DB_NAME')

mysql = MySQL(app)

# Decorator untuk memastikan pengguna login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Silakan login terlebih dahulu!')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Route Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'admin_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM admin WHERE email=%s", (email,))
        admin = cur.fetchone()
        if admin and check_password_hash(admin[2], password):  # Memeriksa hash password
            session['admin_id'] = admin[0]
            flash('Login berhasil!')
            return redirect(url_for('dashboard'))
        else:
            flash('Email atau password salah!')
    return render_template('login.html')

# Route Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Logout berhasil!')
    return redirect(url_for('login'))

# Route Dashboard (hanya untuk pengguna yang sudah login)
@app.route('/')
@login_required
def dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM intents")
    intents = cur.fetchall()
    cur.close()
    return render_template('index.html', intents=intents)

# Route untuk Insert data intent
@app.route('/insert', methods=['POST'])
@login_required
def insert():
    tag = request.form['tag']
    patterns = request.form['patterns']
    responses = request.form['responses']
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO intents (tag, patterns, responses) VALUES (%s, %s, %s)", (tag, patterns, responses))
    mysql.connection.commit()
    flash("Data berhasil ditambahkan!")
    return redirect(url_for('dashboard'))

# Route untuk Delete data intent
@app.route('/delete/<string:id_data>', methods=['GET'])
@login_required
def delete(id_data):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM intents WHERE id=%s", (id_data,))
    mysql.connection.commit()
    flash("Data berhasil dihapus!")
    return redirect(url_for('dashboard'))

# Route untuk Update data intent
@app.route('/update', methods=['POST'])
@login_required
def update():
    id_data = request.form['id']
    tag = request.form['tag']
    patterns = request.form['patterns']
    responses = request.form['responses']
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE intents SET tag=%s, patterns=%s, responses=%s
        WHERE id=%s
    """, (tag, patterns, responses, id_data))
    mysql.connection.commit()
    flash("Data berhasil diperbarui!")
    return redirect(url_for('dashboard'))

# Route untuk CRUD Buku
@app.route('/books')
@login_required
def books():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM books")
    books = cur.fetchall()
    cur.close()
    return render_template('books.html', books=books)

# Route untuk menambah buku
@app.route('/books/add', methods=['POST'])
@login_required
def add_book():
    title = request.form['title']
    subject = request.form['subject']
    location = request.form['location']
    availability = request.form['availability']
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO books (title, subject, location, availability, timestamp) VALUES (%s, %s, %s, %s, %s)",
                (title, subject, location, availability, timestamp))
    mysql.connection.commit()
    flash("Buku berhasil ditambahkan!")
    return redirect(url_for('books'))

# Route untuk menghapus buku
@app.route('/books/delete/<int:id>', methods=['GET'])
@login_required
def delete_book(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM books WHERE id=%s", (id,))
    mysql.connection.commit()
    flash("Buku berhasil dihapus!")
    return redirect(url_for('books'))

# Route untuk memperbarui buku
@app.route('/books/update', methods=['POST'])
@login_required
def update_book():
    id = request.form['id']
    title = request.form['title']
    subject = request.form['subject']
    location = request.form['location']
    availability = request.form['availability']
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE books SET title=%s, subject=%s, location=%s, availability=%s
        WHERE id=%s
    """, (title, subject, location, availability, id))
    mysql.connection.commit()
    flash("Buku berhasil diperbarui!")
    return redirect(url_for('books'))

# Inisialisasi aplikasi
if __name__ == "__main__":
    app.run(debug=True)
