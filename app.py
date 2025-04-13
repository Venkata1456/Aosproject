# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
import os
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
import psutil
import shutil
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from datetime import datetime


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Subbupa1&',
    'database': 'nas_management'
}

UPLOAD_FOLDER = 'C:/NAS_Server_Files'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Helper function to connect to MySQL
def get_db_connection():
    return pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session['role'] = user['role']
            if user['role'] == 'admin':
                return redirect('/admin_dashboard')
            else:
                return redirect('/user_dashboard')
        else:
            return "Invalid credentials"
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    # Clear the session data
    session.clear()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        role = 'user'

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, password, role))
        conn.commit()
        conn.close()

        return redirect('/login')
        flash("User created successfully. Please login to continue.")
    
    return render_template('register.html')

@app.route('/user_dashboard')
def user_dashboard():
    # Check if user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    
    # Establish a database connection
    connection = get_db_connection()
    with connection.cursor() as cursor:
        # Fetch user's access permissions
        cursor.execute("SELECT read_access, write_access FROM users WHERE username = %s", (username,))
        user_permissions = cursor.fetchone()
        
    connection.close()

    disk_usage = psutil.disk_usage('/').percent
    cpu_usage = psutil.cpu_percent(interval=1)
    # Get RAM Usage
    ram = psutil.virtual_memory()
    ram_usage = ram.percent  # Percentage of RAM used
    
    # Check permissions
    if not user_permissions['read_access']:
        flash("You do not have permission to view files.")
        return render_template('user_dashboard.html', read_access=False, write_access=False, username=session['username'], disk_usage=disk_usage, cpu_usage=cpu_usage, ram_usage=ram_usage)
    
    # Render the dashboard with permissions
    return render_template(
        'user_dashboard.html',
        read_access=user_permissions['read_access'],
        write_access=user_permissions['write_access'],
        username=session['username'], disk_usage=disk_usage, cpu_usage=cpu_usage, ram_usage=ram_usage
    )

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'username' in session and session['role'] == 'admin':
        # Establish a database connection
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Query to select only non-admin users
            cursor.execute("SELECT username, read_access, write_access FROM users WHERE role != 'admin'")

            users = cursor.fetchall()
        connection.close()
        
        disk_usage = psutil.disk_usage('/').percent
        cpu_usage = psutil.cpu_percent(interval=1)
        # Get RAM Usage
        ram = psutil.virtual_memory()
        ram_usage = ram.percent  # Percentage of RAM used

        # Get list of backup folders
        backup_folders = [d for d in os.listdir(BASE_FOLDER_PATH) if d.startswith('backup_') and os.path.isdir(os.path.join(BASE_FOLDER_PATH, d))]
    
        return render_template('admin_dashboard.html', username=session['username'], disk_usage=disk_usage, cpu_usage=cpu_usage, ram_usage=ram_usage, users=users, backups=backup_folders)
    else:
        return redirect('/login')

BASE_FOLDER_PATH = 'C:/NAS_Server_Files'  # Change to the folder path for storage

@app.route('/upload_file', methods=['POST'])
def upload_file():
    # Check if the user is logged in
    if 'username' not in session:
        flash("Please log in to upload files.")
        return redirect(url_for('login'))

    # Ensure a file was uploaded
    if 'file' not in request.files:
        flash("No file selected for uploading.")
        return redirect(url_for('user_dashboard'))

    file = request.files['file']

    # If the user uploaded a file with a valid filename
    if file.filename == '':
        flash("No file selected.")
        return redirect(url_for('user_dashboard'))
            
    # Ensure the base folder path exists
    os.makedirs(BASE_FOLDER_PATH, exist_ok=True)
    
    # Save the file to the BASE_FOLDER_PATH
    file_path = os.path.join(BASE_FOLDER_PATH, file.filename)
    file.save(file_path)

    flash(f"File '{file.filename}' uploaded successfully.")
    return redirect(url_for('user_dashboard'))

# Additional routes for file upload, listing, folder management, etc.


# Endpoint to create a folder
@app.route('/create_folder', methods=['POST'])
def create_folder():
    folder_name = request.json.get('folderName')
    folder_path = os.path.join(BASE_FOLDER_PATH, folder_name)
    try:
        os.makedirs(folder_path, exist_ok=True)
        return jsonify(message="Folder created successfully")
    except Exception as e:
        return jsonify(message="Error creating folder: " + str(e)), 500

# Endpoint to rename a folder
@app.route('/rename_folder', methods=['POST'])
def rename_folder():
    old_folder_name = request.json.get('oldFolderName')
    new_folder_name = request.json.get('newFolderName')
    old_folder_path = os.path.join(BASE_FOLDER_PATH, old_folder_name)
    new_folder_path = os.path.join(BASE_FOLDER_PATH, new_folder_name)
    try:
        os.rename(old_folder_path, new_folder_path)
        return jsonify(message="Folder renamed successfully")
    except Exception as e:
        return jsonify(message="Error renaming folder: " + str(e)), 500

# Endpoint to delete a folder
@app.route('/delete_folder', methods=['POST'])
def delete_folder():
    folder_name = request.json.get('folderName')
    folder_path = os.path.join(BASE_FOLDER_PATH, folder_name)
    try:
        os.rmdir(folder_path)
        return jsonify(message="Folder deleted successfully")
    except Exception as e:
        return jsonify(message="Error deleting folder: " + str(e)), 500

# Endpoint to list all folders
@app.route('/list_folders', methods=['GET'])
def list_folders():
    try:
        folders = [f for f in os.listdir(BASE_FOLDER_PATH) if os.path.isdir(os.path.join(BASE_FOLDER_PATH, f))]
        return jsonify(folders=folders)
    except Exception as e:
        return jsonify(message="Error listing folders: " + str(e)), 500

@app.route('/list_files', methods=['GET'])
def list_files():
    try:
        files = os.listdir(BASE_FOLDER_PATH)
        return jsonify({'files': files}), 200
    except Exception as e:
        print(f"Error listing files: {e}")
        return jsonify({'error': 'Could not list files.'}), 500

@app.route('/download_file', methods=['GET'])
def download_file():
    filename = request.args.get('filename')
    if filename:
        try:
            # Serve the file from the specified directory
            return send_from_directory(BASE_FOLDER_PATH, filename, as_attachment=True)
        except FileNotFoundError:
            return jsonify({'error': 'File not found'}), 404
    else:
        return jsonify({'error': 'Filename not specified'}), 400

# Route to delete a file
@app.route('/delete_file', methods=['DELETE'])
def delete_file():
    filename = request.args.get('filename')
    if filename:
        file_path = os.path.join(BASE_FOLDER_PATH, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return jsonify({'message': f'{filename} deleted successfully.'}), 200
            except Exception as e:
                return jsonify({'error': f'Error deleting {filename}: {str(e)}'}), 500
        else:
            return jsonify({'error': 'File not found'}), 404
    else:
        return jsonify({'error': 'Filename not specified'}), 400

@app.route('/update_access', methods=['POST'])
def update_access():
    username = request.form['username']
    read_access = request.form.get('read_access') == 'true'
    write_access = request.form.get('write_access') == 'true'
    
    # Update user's permissions in the database
    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE users 
        SET read_access = %s, write_access = %s 
        WHERE username = %s
    """, (read_access, write_access, username))
    mysql.connection.commit()
    cursor.close()

    return jsonify({"success": True, "message": "Access updated successfully"})

@app.route('/delete_user', methods=['POST'])
def delete_user():
    # Check if the admin is logged in
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    # Get the username to delete from the form
    username_to_delete = request.form['username']

    # Connect to the database and delete the user
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM users WHERE username = %s", (username_to_delete,))
        connection.commit()
    connection.close()

    flash(f"User '{username_to_delete}' has been deleted.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/apply_changes', methods=['POST'])
def apply_changes():
    # Check if the admin is logged in
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    # Get the values from the form
    username = request.form['username']
    read_access = request.form['read_access'] == 'true'
    write_access = request.form['write_access'] == 'true'

    # Update the user's permissions in the database
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE users
            SET read_access = %s, write_access = %s
            WHERE username = %s
        """, (read_access, write_access, username))
        connection.commit()
    connection.close()

    # Send a success message back to the front-end
    return jsonify({'message': f"Permissions for '{username}' have been updated."})

# Route for creating a backup
@app.route('/backup_files')
@login_required
def backup_files():
    if not current_user.is_admin:
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for('admin_dashboard'))
    
    # Create a new backup folder with timestamp
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    backup_folder = os.path.join(BASE_FOLDER_PATH, f"backup_{timestamp}")

    try:
        # Create backup directory
        os.makedirs(backup_folder)

        # Copy all files and folders from NAS_Server_Files to the new backup folder
        for item in os.listdir(BASE_FOLDER_PATH):
            s = os.path.join(BASE_FOLDER_PATH, item)
            d = os.path.join(backup_folder, item)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)

        flash(f"Backup created successfully in folder: {backup_folder}", "success")
    except Exception as e:
        flash(f"Error during backup: {str(e)}", "danger")
    
    return redirect(url_for('admin_dashboard'))


# Route for restoring backup
@app.route('/restore_backup/<backup_folder>', methods=['GET'])
@login_required
def restore_backup(backup_folder):
    if not current_user.is_admin:
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for('admin_dashboard'))

    backup_folder_path = os.path.join(BASE_FOLDER_PATH, backup_folder)
    
    if not os.path.exists(backup_folder_path):
        flash("Backup folder does not exist.", "danger")
        return redirect(url_for('admin_dashboard'))

    # Send all files in the backup folder as a zip file
    try:
        # Create a zip file of the backup folder
        shutil.make_archive(backup_folder_path, 'zip', backup_folder_path)
        zip_file = f"{backup_folder_path}.zip"
        
        return send_from_directory(directory=os.path.dirname(zip_file), path=os.path.basename(zip_file), as_attachment=True)
    
    except Exception as e:
        flash(f"Error during restore: {str(e)}", "danger")
        return redirect(url_for('admin_dashboard'))



if __name__ == '__main__':
    app.run(debug=True)
