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
        print(f"Attempting to connect with config: {config}")  # Debug log
        connection = mysql.connector.connect(**config)
        if connection.is_connected():
            print("Database connection successful!")
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

# Route Login dengan debug dan support untuk plain text password
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
                
                print(f"Login attempt - Email: {email}")  # Debug
                print(f"Admin found: {admin}")  # Debug
                
                if admin:
                    # Cek apakah password di database sudah di-hash atau plain text
                    stored_password = admin[2]  # Asumsi password di kolom ke-3
                    print(f"Stored password: {stored_password}")  # Debug
                    print(f"Input password: {password}")  # Debug
                    
                    # Coba cek hash dulu, jika gagal coba plain text
                    password_valid = False
                    if stored_password.startswith('pbkdf2:') or stored_password.startswith('scrypt:') or stored_password.startswith('$'):
                        # Password sudah di-hash
                        try:
                            password_valid = check_password_hash(stored_password, password)
                            print(f"Hash check result: {password_valid}")  # Debug
                        except Exception as e:
                            print(f"Hash check error: {e}")  # Debug
                            password_valid = False
                    else:
                        # Password masih plain text
                        password_valid = (stored_password == password)
                        print(f"Plain text check result: {password_valid}")  # Debug
                    
                    if password_valid:
                        session['admin_id'] = admin[0]
                        flash('Login berhasil!')
                        return redirect(url_for('dashboard'))
                    else:
                        flash('Email atau password salah!')
                else:
                    flash('Email tidak ditemukan!')
                    
            except Error as e:
                print(f"Database error during login: {e}")  # Debug
                flash(f'Database error: {e}')
            finally:
                cursor.close()
                connection.close()
        else:
            flash('Koneksi database gagal!')
            
    return render_template('login.html')

# Route untuk update password admin yang sudah ada menjadi hash
@app.route('/hash-admin-password')
def hash_admin_password():
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            # Hash password yang sudah ada
            new_hashed_password = generate_password_hash('admin1234')
            cursor.execute("UPDATE admin SET password = %s WHERE email = %s", 
                         (new_hashed_password, 'admin@perpus.com'))
            cursor.close()
            connection.close()
            return f"Password admin berhasil di-hash!<br>New hash: {new_hashed_password}<br><a href='/login'>Login sekarang</a>"
        except Error as e:
            return f'Database error: {e}'
    else:
        return 'Koneksi database gagal!'

# Route untuk membuat admin baru
@app.route('/create-admin', methods=['GET', 'POST'])
def create_admin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("INSERT INTO admin (email, password) VALUES (%s, %s)", 
                             (email, hashed_password))
                cursor.close()
                connection.close()
                flash("Admin berhasil dibuat!")
                return redirect(url_for('login'))
            except Error as e:
                flash(f'Database error: {e}')
        else:
            flash('Koneksi database gagal!')
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Create Admin</title></head>
    <body>
        <h2>Create New Admin</h2>
        <form method="post">
            <p><input type="email" name="email" placeholder="Email" required></p>
            <p><input type="password" name="password" placeholder="Password" required></p>
            <p><button type="submit">Create Admin</button></p>
        </form>
        <a href="/login">Back to Login</a>
    </body>
    </html>
    '''

# Route untuk debug - lihat semua admin
@app.route('/debug-admin')
def debug_admin():
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT id, email, password FROM admin")
            admins = cursor.fetchall()
            cursor.close()
            connection.close()
            
            result = "<h2>Debug Admin Data</h2>"
            for admin in admins:
                result += f"<p>ID: {admin[0]}, Email: {admin[1]}, Password: {admin[2]}</p>"
            result += "<br><a href='/hash-admin-password'>Hash Current Password</a>"
            result += "<br><a href='/login'>Login</a>"
            return result
        except Error as e:
            return f'Database error: {e}'
    else:
        return 'Koneksi database gagal!'

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
    # Test koneksi database saat startup
    print("Testing database connection...")
    test_conn = get_db_connection()
    if test_conn:
        print("Database connection test: SUCCESS")
        test_conn.close()
    else:
        print("Database connection test: FAILED")
    
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))