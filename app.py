from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response, current_app
import sqlite3
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from typing import Optional
from sqlite3 import Connection
from functools import wraps
from datetime import timedelta


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
SECRET_KEY = 'a4c78f3ea9cc4f74bfb15efad9b012ee2342abcdefff1234'
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = timedelta(minutes=10)


def init_db() -> None:
    """
    初始化資料庫，若不存在則建立 announcements 與 images 資料表。
    """
    if not os.path.exists('database.db'):
        try:
            conn = sqlite3.connect('database.db')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS announcements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    image TEXT,
                    timestamp TEXT NOT NULL
                );
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    announcement_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    is_cover INTEGER DEFAULT 0,
                    FOREIGN KEY (announcement_id) REFERENCES announcements (id)
                );
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS members (
                    iid INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    account TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL
                );
            ''')
            conn.execute('''
                INSERT OR IGNORE INTO members (username, account, password)
                VALUES (?, ?, ?)
            ''', ('admin', 'admin', 'admin'))

            conn.commit()
        except sqlite3.Error as e:
            print(f"資料庫錯誤: {e}")
        finally:
            conn.close()


def get_db_connection() -> Connection:
    """
    建立並回傳資料庫連線。
    """
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('請先登入')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    """
    首頁，顯示最新三則公告。
    """
    try:
        conn = get_db_connection()
        announcements = conn.execute(
            'SELECT * FROM announcements ORDER BY id DESC LIMIT 3'
        ).fetchall()
    finally:
        conn.close()
    return render_template('index.html', announcements=announcements)


@app.route('/member')
def member():
    """
    奉祀神祇頁
    """
    return render_template('member.html')


@app.route('/history')
def history():
    """
    神明故事頁
    """
    return render_template('history.html')


@app.route('/event')
def event():
    """
    廟宇沿革頁
    """
    return render_template('event.html')


@app.route('/light')
def light():
    """
    安奉斗燈頁
    """
    return render_template('light.html')


@app.route('/solve')
def solve():
    """
    收驚問事頁
    """
    return render_template('solve.html')


@app.route('/announcements')
def announcement_list():
    """
    公告列表頁面。
    """
    try:
        conn = get_db_connection()
        announcements = conn.execute(
            'SELECT * FROM announcements ORDER BY id DESC'
        ).fetchall()
    finally:
        conn.close()
    return render_template('announcements.html', announcements=announcements)


@app.route('/announcements/<int:announcement_id>')
def announcement_detail(announcement_id: int):
    """
    公告詳情頁。
    """
    try:
        conn = get_db_connection()
        announcement = conn.execute(
            'SELECT * FROM announcements WHERE id = ?',
            (announcement_id,)
        ).fetchone()
        images = conn.execute(
            'SELECT * FROM images WHERE announcement_id = ?',
            (announcement_id,)
        ).fetchall()
    finally:
        conn.close()
    return render_template('announcement_detail.html', announcement=announcement, images=images)


@app.route('/admin_announcements')
@login_required
def admin_announcements():
    """
    管理頁面，顯示所有公告。
    """
    try:
        conn = get_db_connection()
        announcements = conn.execute(
            'SELECT * FROM announcements ORDER BY id DESC'
        ).fetchall()
    finally:
        conn.close()
    return render_template('admin_announcements.html', announcements=announcements)


@app.route('/admin_announcements/create_announcements', methods=['GET', 'POST'])
@login_required
def create_announcements():
    """
    新增公告。
    """
    if request.method == 'POST':
        title: str = request.form['title']
        content: str = request.form['content']
        image = request.files.get('image')
        images = request.files.getlist('images')
        timestamp: str = datetime.now().strftime('%Y-%m-%d')

        image_filename: Optional[str] = None
        if image and image.filename:
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            image_filename = filename

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO announcements (title, content, image, timestamp) VALUES (?, ?, ?, ?)',
                (title, content, image_filename, timestamp)
            )
            announcement_id = cursor.lastrowid

            for img in images:
                if img and img.filename:
                    img_name = secure_filename(img.filename)
                    img_path = os.path.join(app.config['UPLOAD_FOLDER'], img_name)
                    img.save(img_path)
                    cursor.execute(
                        'INSERT INTO images (announcement_id, filename) VALUES (?, ?)',
                        (announcement_id, img_name)
                    )
            conn.commit()
        except sqlite3.Error as e:
            print(f"資料庫錯誤: {e}")
        finally:
            conn.close()

        return redirect(url_for('admin_announcements'))

    return render_template('create_announcements.html')


@app.route('/admin_announcements/delete/<int:announcement_id>')
@login_required
def delete(announcement_id: int):
    """
    刪除公告。
    """
    try:
        conn = get_db_connection()
        conn.execute(
            'DELETE FROM announcements WHERE id = ?',
            (announcement_id,)
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"刪除失敗: {e}")
    finally:
        conn.close()
    return redirect(url_for('admin_announcements'))


@app.route('/admin_announcements/delete-image/<int:image_id>/<int:announcement_id>')
@login_required
def delete_image(image_id: int, announcement_id: int):
    """
    刪除公告的一張附加圖片。
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        image = cursor.execute('SELECT filename FROM images WHERE id = ?', (image_id,)).fetchone()
        if image:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], image['filename'])
            if os.path.exists(file_path):
                os.remove(file_path)
            cursor.execute('DELETE FROM images WHERE id = ?', (image_id,))
            conn.commit()
    except sqlite3.Error as e:
        print(f"圖片刪除失敗: {e}")
    finally:
        conn.close()
    return redirect(url_for('edit', announcement_id=announcement_id))


@app.route('/admin_announcements/edit/<int:announcement_id>', methods=['GET', 'POST'])
@login_required
def edit(announcement_id: int):
    """
    編輯公告。
    """
    conn = get_db_connection()
    announcement = conn.execute(
        'SELECT * FROM announcements WHERE id = ?',
        (announcement_id,)
    ).fetchone()

    # 讀取目前所有附加圖片
    other_images = conn.execute(
        'SELECT * FROM images WHERE announcement_id = ?',
        (announcement_id,)
    ).fetchall()

    if request.method == 'POST':
        title: str = request.form['title']
        content: str = request.form['content']
        image = request.files.get('image')
        new_images = request.files.getlist('images')

        image_filename: str = announcement['image']
        if image and image.filename:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename

        try:
            conn.execute(
                'UPDATE announcements SET title = ?, content = ?, image = ? WHERE id = ?',
                (title, content, image_filename, announcement_id)
            )

            # 新增新上傳的多張圖片
            for img in new_images:
                if img and img.filename:
                    img_name = secure_filename(img.filename)
                    img_path = os.path.join(app.config['UPLOAD_FOLDER'], img_name)
                    img.save(img_path)
                    conn.execute(
                        'INSERT INTO images (announcement_id, filename) VALUES (?, ?)',
                        (announcement_id, img_name)
                    )

            conn.commit()
        except sqlite3.Error as e:
            print(f"更新失敗: {e}")
        finally:
            conn.close()
        return redirect(url_for('admin_announcements'))

    conn.close()
    return render_template('edit.html', announcement=announcement, other_images=other_images)


@app.route('/admin')
def admin():
    """
    後臺首頁 未登入
    """
    return render_template('admin.html')


@app.route('/login', methods=['GET', 'POST'])
def admin_login():
    """
    後臺登入
    """
    if request.method == 'POST':
        account = request.form.get('account')
        password = request.form.get('password')

        if not account or not password:
            return render_template('admin_error.html', message='請輸入帳號和密碼')

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT iid, username FROM members WHERE account = ? AND password = ?', (account, password))
            row = cursor.fetchone()
            if not row:
                return render_template('admin_error.html', message='帳號或密碼錯誤')

            iid, username = row['iid'], row['username']
            session['logged_in'] = True
            session['username'] = username
            session['iid'] = iid
            session.permanent = True

            return redirect(url_for('admin_welcome'))

    return render_template('admin_login.html')


@app.route('/admin_welcome')
@login_required
def admin_welcome():
    """
    後臺首頁 已登入
    """
    username = session.get('username')
    iid = session.get('iid')
    return render_template('admin_welcome.html', username=username, iid=iid)


@app.route('/logout')
def logout():
    """
    後臺登出
    """
    session.clear()
    response = make_response(redirect(url_for('admin_login')))
    response.delete_cookie(current_app.config['SESSION_COOKIE_NAME'])
    return response

@app.route('/edit_profile/<int:iid>', methods=['GET', 'POST'])
@login_required
def admin_edit_profile(iid: int):
    """
    後臺管理員檔案編輯
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if request.method == 'POST':
            account = request.form.get('account')
            password = request.form.get('password')

            if not account or not password:
                return render_template('admin_error.html', message='請輸入帳號和密碼')

            cursor.execute('SELECT * FROM members WHERE account = ? AND iid != ?', (account, iid))
            if cursor.fetchone():
                return render_template('admin_error.html', message='帳號已被使用')

            cursor.execute('''
                UPDATE members SET account = ?, password = ?
                WHERE iid = ?
            ''', (account, password, iid))
            conn.commit()
            cursor.execute('SELECT username FROM members WHERE iid = ?', (iid,))
            username = cursor.fetchone()['username']
            return render_template('admin_welcome.html', username=username, iid=iid)

        cursor.execute('SELECT * FROM members WHERE iid = ?', (iid,))
        user = cursor.fetchone()
        if user:
            return render_template('admin_edit_profile.html', user=user)
        return render_template('admin_error.html', message='找不到用戶')


@app.route('/delete/<int:iid>')
@login_required
def admin_delete_user(iid: int):
    """
    後臺管理員檔案刪除
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM members WHERE iid = ?', (iid,))
        conn.commit()
    return redirect(url_for('admin'))


init_db()


@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001)
