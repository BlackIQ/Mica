import datetime
import os
import re
import subprocess
import requests
import hashlib
from flask import (
    Flask,
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
    session
)
from flask_mysqldb import MySQL
import mysql.connector
import MySQLdb.cursors
from werkzeug.utils import secure_filename
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import config

# Flask App Settings
UPLOAD_FOLDER = config.UPLOAD_FOLDER
ALLOWED_EXTENSIONS = config.ALLOWED_EXTENSIONS
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_PATH'] = 100
limiter = Limiter(app, key_func=get_remote_address)
app.config.update(SECRET_KEY=config.SECRET_KEY)
app.config['MYSQL_HOST'] = config.MYSQL_HOST
app.config['MYSQL_USER'] = config.MYSQL_USERNAME
app.config['MYSQL_PASSWORD'] = config.MYSQL_PASSWORD
app.config['MYSQL_DB'] = config.MYSQL_DB_NAME


# login
class Users:
    mysql = MySQL(app)


@app.route('/login', methods=['Get', 'Post'])
@limiter.limit("10 per minute")
def login():
    print(request.form)
    print(1)
    if 'loggedin' in session:
        flash('already logged in', 'success')
        return redirect('/dashboard')
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        print(2)
        username = request.form.get('username')
        passw = request.form.get('password')
        print(3)
        password = hashlib.sha256(passw.encode()).hexdigest()
        cursor = Users.mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM USERS WHERE username = %s AND passhash = %s', (username, password))
        account = cursor.fetchone()
        print(4)
        if account:
            print(5)
            session['loggedin'] = True
            session['id'] = account['ID']
            session['username'] = account['USERNAME']
            flash('Logged in successfully!', 'success')
            print(6)
            return redirect('/')
        else:
            print(7)
            flash('Incorrect username/password!', 'warning')
            print(8)
            return render_template('login.html')
    return render_template('login.html')


@app.route('/register', methods=['Get', 'Post'])
def register():
    if request.method == 'POST':
        if request.form.get('invitecode') != config.INVITE_CODE:
            flash(
                "Sorry, You can't register without an invition code right now. If you want to get notified about public access day, return to mainpage and submit your email for out newsletter.",
                'info')
        username = request.form.get('username')
        password = request.form.get('password')
        confirmpassword = request.form.get('confirmpassword')
        email = request.form.get('email')
        phone = request.form.get('phone')
        if not username or not password or not email:
            flash('Please fill out the form!', 'danger')
            return redirect('/admin/new_user')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Invalid email address!', 'danger')
            return redirect('/admin/new_user')
        elif not re.match(r'[A-Za-z0-9]+', username):
            flash('Username must contain only characters and numbers!', 'danger')
            return redirect('/admin/new_user')
        elif password != confirmpassword:
            flash("The Passwords doesn't match", 'danger')
            return redirect('/admin/new_user')
        cur = Users.mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute(f"SELECT * FROM USERS WHERE username = '{username}'")
        userex = cur.fetchone()
        if userex:
            flash('Username already exists!', 'warning')
            return redirect('/admin/new_user')
        else:
            createuser(username, password, email, phone)
            flash('Registration was succesfull', 'success')
            return redirect('/')

    elif request.method == 'POST':
        flash('Please fill out the form!', 'danger')
        return redirect('/admin/new_user')
    if request.referrer == 'http://localhost:5000/admin/new_user' or request.referrer == None:
        referrer = 'http://localhost:5000/admin'
    else:
        referrer = request.referrer
    return render_template('register.html', data={'referrer': referrer})


def createuser(username, password, email, phone):
    db = get_database_connection()
    cur = db.cursor()
    cur.execute("SELECT count(*) FROM USERS")
    uid = int(cur.fetchone()[0]) + 1
    passhash = hashlib.sha256(password.encode()).hexdigest()
    date = datetime.datetime.now()
    cur.execute(f"INSERT INTO USERS VALUES ({uid},'{username}','{passhash}','{email}','{phone}','{date}');")
    db.commit()
    db.close()


# DataBase
def get_database_connection():
    """connects to the MySQL database and returns the connection"""
    return mysql.connector.connect(host=config.MYSQL_HOST,
                                   user=config.MYSQL_USERNAME,
                                   passwd=config.MYSQL_PASSWORD,
                                   db=config.MYSQL_DB_NAME,
                                   charset='utf8')


# Upload Voices
@app.route('/uploadfile')
def upload_file():
    return render_template('upload.html')


@app.route('/upload', methods=['Post'])
def upload():
    # check if the post request has the file part
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(request.url)
    file = request.files['file']
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        date = datetime.datetime.now()
        username = session['username']

        fileid = createfilename()
        filename = fileid + filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        db = get_database_connection()
        cur = db.cursor()
        cur.execute(f"INSERT INTO VOICES VALUES ({fileid} , '{username}' , '{date}' );")
        flash('File uploaded', 'info')
        return redirect('/')


def allowed_file(filename):
    """ checks the extension of the passed filename to be in the allowed extensions"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def createfilename():
    """return new file id"""
    db = get_database_connection()
    cur = db.cursor()
    cur.execute('SELECT count(*) FROM VOICES;')
    newfilename = cur.fetchone()[0]
    return str(newfilename)


@app.route('/')
def home():
    return render_template('home.html')