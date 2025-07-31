import os
from flask import Flask, render_template, request, url_for, flash, session, redirect
import mysql.connector
from mysql.connector import Error
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from dotenv import load_dotenv

# Memuat variabel lingkungan dari .env (untuk pengembangan lokal)
load_dotenv()

app = Flask(__name__)
app.secret_key = 'many random bytes'

# Konfigurasi database menggunakan variabel lingkungan dari Railway
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'mysql.railway.internal'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME', 'railway'),
    'autocommit': True,
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'connect_timeout': 60,
    'buffered': True
}

# Fungsi untuk mendapatkan koneksi database
def get_db_connection():
    try:
        # Filter None values dari config
        config = {k: v for k, v in DB_CONFIG.items() if v is not None}
        connection = mysql.connector.connect(**config)
        if connection.is_connected():
            return connection
        else:
            print("Failed to establish database connection")
            return None
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

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
        
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("SELECT * FROM admin WHERE email=%s", (email,))
                admin = cursor.fetchone()
                
                if admin and check_password_hash(admin[2], password):  # Memeriksa hash password
                    session['admin_id'] = admin[0]
                    flash('Login berhasil!')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Email atau password salah!')
                    
            except Error as e:
                flash(f'Database error: {e}')
            finally:
                cursor.close()
                connection.close()
        else:
            flash('Koneksi database gagal!')
            
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
    connection = get_db_connection()
    intents = []
    
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM intents")
            intents = cursor.fetchall()
        except Error as e:
            flash(f'Database error: {e}')
        finally:
            cursor.close()
            connection.close()
    else:
        flash('Koneksi database gagal!')
        
    return render_template('index.html', intents=intents)

# Route untuk Insert data intent
@app.route('/insert', methods=['POST'])
@login_required
def insert():
    tag = request.form['tag']
    patterns = request.form['patterns']
    responses = request.form['responses']
    
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("INSERT INTO intents (tag, patterns, responses) VALUES (%s, %s, %s)", 
                         (tag, patterns, responses))
            flash("Data berhasil ditambahkan!")
        except Error as e:
            flash(f'Database error: {e}')
        finally:
            cursor.close()
            connection.close()
    else:
        flash('Koneksi database gagal!')
        
    return redirect(url_for('dashboard'))

# Route untuk Delete data intent
@app.route('/delete/<string:id_data>', methods=['GET'])
@login_required
def delete(id_data):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM intents WHERE id=%s", (id_data,))
            flash("Data berhasil dihapus!")
        except Error as e:
            flash(f'Database error: {e}')
        finally:
            cursor.close()
            connection.close()
    else:
        flash('Koneksi database gagal!')
        
    return redirect(url_for('dashboard'))

# Route untuk Update data intent
@app.route('/update', methods=['POST'])
@login_required
def update():
    id_data = request.form['id']
    tag = request.form['tag']
    patterns = request.form['patterns']
    responses = request.form['responses']
    
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE intents SET tag=%s, patterns=%s, responses=%s
                WHERE id=%s
            """, (tag, patterns, responses, id_data))
            flash("Data berhasil diperbarui!")
        except Error as e:
            flash(f'Database error: {e}')
        finally:
            cursor.close()
            connection.close()
    else:
        flash('Koneksi database gagal!')
        
    return redirect(url_for('dashboard'))

# Route untuk CRUD Buku
@app.route('/books')
@login_required
def books():
    connection = get_db_connection()
    books = []
    
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM books")
            books = cursor.fetchall()
        except Error as e:
            flash(f'Database error: {e}')
        finally:
            cursor.close()
            connection.close()
    else:
        flash('Koneksi database gagal!')
        
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
    
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("INSERT INTO books (title, subject, location, availability, timestamp) VALUES (%s, %s, %s, %s, %s)",
                         (title, subject, location, availability, timestamp))
            flash("Buku berhasil ditambahkan!")
        except Error as e:
            flash(f'Database error: {e}')
        finally:
            cursor.close()
            connection.close()
    else:
        flash('Koneksi database gagal!')
        
    return redirect(url_for('books'))

# Route untuk menghapus buku
@app.route('/books/delete/<int:id>', methods=['GET'])
@login_required
def delete_book(id):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM books WHERE id=%s", (id,))
            flash("Buku berhasil dihapus!")
        except Error as e:
            flash(f'Database error: {e}')
        finally:
            cursor.close()
            connection.close()
    else:
        flash('Koneksi database gagal!')
        
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
    
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE books SET title=%s, subject=%s, location=%s, availability=%s
                WHERE id=%s
            """, (title, subject, location, availability, id))
            flash("Buku berhasil diperbarui!")
        except Error as e:
            flash(f'Database error: {e}')
        finally:
            cursor.close()
            connection.close()
    else:
        flash('Koneksi database gagal!')
        
    return redirect(url_for('books'))

# Inisialisasi aplikasi
if __name__ == "__main__":
    app.run(debug=True)