from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
import os
import pymysql
import psutil
import shutil
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Config
BASE_DIR = 'C:/NAS_Server_Files'
SECRET_KEY = 'my_secret'
DB_DETAILS = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Subbupa1&',
    'database': 'nas_management'
}

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['UPLOAD_DIR'] = BASE_DIR


# DB Connector
def db():
    return pymysql.connect(**DB_DETAILS, cursorclass=pymysql.cursors.DictCursor)


@app.route('/')
def index():
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login_view():
    if request.method == 'POST':
        uname = request.form['username']
        passwd = request.form['password']

        conn = db()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username=%s", (uname,))
            user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], passwd):
            session['user'] = uname
            session['role'] = user['role']
            return redirect('/admin' if user['role'] == 'admin' else '/dashboard')
        flash("Invalid credentials")
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        uname = request.form['username']
        passwd = generate_password_hash(request.form['password'])

        conn = db()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, 'user')", (uname, passwd))
            conn.commit()
        conn.close()
        flash("Registration complete.")
        return redirect('/login')
    return render_template('register.html')


@app.route('/logout')
def log_out():
    session.clear()
    return redirect('/login')


@app.route('/dashboard')
def user_home():
    if 'user' not in session:
        return redirect('/login')

    conn = db()
    with conn.cursor() as cur:
        cur.execute("SELECT read_access, write_access FROM users WHERE username=%s", (session['user'],))
        perms = cur.fetchone()
    conn.close()

    stats = {
        'disk': psutil.disk_usage('/').percent,
        'cpu': psutil.cpu_percent(1),
        'ram': psutil.virtual_memory().percent
    }

    if not perms['read_access']:
        flash("Read access not granted.")
        return render_template('user_dashboard.html', **stats, read_access=False, write_access=False, username=session['user'])

    return render_template('user_dashboard.html', **stats, read_access=perms['read_access'], write_access=perms['write_access'], username=session['user'])


@app.route('/admin')
def admin_home():
    if session.get('role') != 'admin':
        return redirect('/login')

    conn = db()
    with conn.cursor() as cur:
        cur.execute("SELECT username, read_access, write_access FROM users WHERE role != 'admin'")
        users = cur.fetchall()
    conn.close()

    backups = [f for f in os.listdir(BASE_DIR) if f.startswith('backup_') and os.path.isdir(os.path.join(BASE_DIR, f))]
    stats = {
        'disk': psutil.disk_usage('/').percent,
        'cpu': psutil.cpu_percent(1),
        'ram': psutil.virtual_memory().percent
    }

    return render_template('admin_dashboard.html', users=users, backups=backups, username=session['user'], **stats)


@app.route('/upload', methods=['POST'])
def upload():
    if 'user' not in session or 'file' not in request.files:
        return redirect('/dashboard')

    f = request.files['file']
    if f.filename == '':
        flash("No file selected.")
        return redirect('/dashboard')

    os.makedirs(BASE_DIR, exist_ok=True)
    f.save(os.path.join(BASE_DIR, f.filename))
    flash("Upload complete.")
    return redirect('/dashboard')


@app.route('/folders', methods=['GET', 'POST', 'PUT', 'DELETE'])
def folders():
    if request.method == 'POST':
        name = request.json.get('folderName')
        os.makedirs(os.path.join(BASE_DIR, name), exist_ok=True)
        return jsonify(msg='Created')
    
    if request.method == 'PUT':
        data = request.json
        os.rename(os.path.join(BASE_DIR, data['oldFolderName']), os.path.join(BASE_DIR, data['newFolderName']))
        return jsonify(msg='Renamed')
    
    if request.method == 'DELETE':
        name = request.json.get('folderName')
        shutil.rmtree(os.path.join(BASE_DIR, name), ignore_errors=True)
        return jsonify(msg='Deleted')

    folders = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))]
    return jsonify(folders=folders)


@app.route('/files', methods=['GET', 'DELETE'])
def file_ops():
    filename = request.args.get('filename')
    if request.method == 'DELETE' and filename:
        os.remove(os.path.join(BASE_DIR, filename))
        return jsonify(msg='File deleted')
    if request.method == 'GET':
        return jsonify(files=os.listdir(BASE_DIR))


@app.route('/download')
def download():
    fname = request.args.get('filename')
    return send_from_directory(BASE_DIR, fname, as_attachment=True)


@app.route('/backup')
def backup():
    if session.get('role') != 'admin':
        return redirect('/admin')

    now = datetime.now().strftime('%Y%m%d%H%M%S')
    dest = os.path.join(BASE_DIR, f"backup_{now}")
    os.makedirs(dest, exist_ok=True)

    for item in os.listdir(BASE_DIR):
        src = os.path.join(BASE_DIR, item)
        dst = os.path.join(dest, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    flash("Backup successful.")
    return redirect('/admin')


@app.route('/restore/<bname>')
def restore(bname):
    if session.get('role') != 'admin':
        return redirect('/admin')
    
    zip_path = shutil.make_archive(os.path.join(BASE_DIR, bname), 'zip', os.path.join(BASE_DIR, bname))
    return send_from_directory(BASE_DIR, os.path.basename(zip_path), as_attachment=True)


@app.route('/permissions', methods=['POST'])
def update_permissions():
    uname = request.form['username']
    read = request.form.get('read_access') == 'true'
    write = request.form.get('write_access') == 'true'

    conn = db()
    with conn.cursor() as cur:
        cur.execute("UPDATE users SET read_access=%s, write_access=%s WHERE username=%s", (read, write, uname))
        conn.commit()
    conn.close()

    return jsonify(msg="Permissions updated")


@app.route('/remove_user', methods=['POST'])
def remove_user():
    uname = request.form['username']
    conn = db()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM users WHERE username=%s", (uname,))
        conn.commit()
    conn.close()
    flash(f"{uname} removed.")
    return redirect('/admin')


if __name__ == "__main__":
    app.run(debug=True)
