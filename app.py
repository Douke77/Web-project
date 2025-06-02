from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from typing import List, Optional
from sqlite3 import Connection, Row

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'


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


@app.route('/admin')
def admin():
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
    return render_template('admin.html', announcements=announcements)


@app.route('/admin/create', methods=['GET', 'POST'])
def create():
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

        return redirect(url_for('admin'))

    return render_template('create.html')


@app.route('/admin/delete/<int:announcement_id>')
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
    return redirect(url_for('admin'))


@app.route('/admin/edit/<int:announcement_id>', methods=['GET', 'POST'])
def edit(announcement_id: int):
    """
    編輯公告（支援更換封面圖，不支援多圖修改）。
    """
    conn = get_db_connection()
    announcement = conn.execute(
        'SELECT * FROM announcements WHERE id = ?',
        (announcement_id,)
    ).fetchone()

    if request.method == 'POST':
        title: str = request.form['title']
        content: str = request.form['content']
        image = request.files.get('image')

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
            conn.commit()
        except sqlite3.Error as e:
            print(f"更新失敗: {e}")
        finally:
            conn.close()
        return redirect(url_for('admin'))

    conn.close()
    return render_template('edit.html', announcement=announcement)

