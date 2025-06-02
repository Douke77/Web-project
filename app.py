from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import json

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# 建立資料庫
def init_db():
    if not os.path.exists('database.db'):
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
        conn.close()
        print("✅ 資料庫已建立完成！")


# 取得資料庫連線
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# 首頁
@app.route('/')
def index():
    conn = get_db_connection()
    announcements = conn.execute('SELECT * FROM announcements ORDER BY id DESC LIMIT 3').fetchall()
    conn.close()
    return render_template('index.html', announcements=announcements)

# 公告列表
@app.route('/announcements')
def announcement_list():
    conn = get_db_connection()
    announcements = conn.execute('SELECT * FROM announcements ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('announcements.html', announcements=announcements)

# 公告詳情
@app.route('/announcements/<int:announcement_id>')
def announcement_detail(announcement_id):
    conn = get_db_connection()
    announcement = conn.execute('SELECT * FROM announcements WHERE id = ?', (announcement_id,)).fetchone()
    images = conn.execute('SELECT * FROM images WHERE announcement_id = ?', (announcement_id,)).fetchall()
    conn.close()
    return render_template('announcement_detail.html', announcement=announcement, images=images)


# 管理頁面
@app.route('/admin')
def admin():
    conn = get_db_connection()
    announcements = conn.execute('SELECT * FROM announcements ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin.html', announcements=announcements)

# 新增公告
@app.route('/admin/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        image = request.files['image']
        images = request.files.getlist('images')  # 多圖
        timestamp = datetime.now().strftime('%Y-%m-%d')

        image_filename = None
        if image and image.filename:
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            image_filename = filename

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO announcements (title, content, image, timestamp) VALUES (?, ?, ?, ?)',
                       (title, content, image_filename, timestamp))
        announcement_id = cursor.lastrowid  # 新增後拿 ID

        # 儲存多張圖片
        for img in images:
            if img and img.filename:
                img_name = secure_filename(img.filename)
                img_path = os.path.join(app.config['UPLOAD_FOLDER'], img_name)
                img.save(img_path)
                cursor.execute('INSERT INTO images (announcement_id, filename) VALUES (?, ?)',
                               (announcement_id, img_name))

        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    return render_template('create.html')

# 刪除公告
@app.route('/admin/delete/<int:announcement_id>')
def delete(announcement_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM announcements WHERE id = ?', (announcement_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

# 修改公告
@app.route('/admin/edit/<int:announcement_id>', methods=['GET', 'POST'])
def edit(announcement_id):
    conn = get_db_connection()
    announcement = conn.execute('SELECT * FROM announcements WHERE id = ?', (announcement_id,)).fetchone()

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        image = request.files.get('image')
        images = request.files.getlist('images')

        image_filename = None
        if image and image.filename:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename

        conn.execute('UPDATE announcements SET title = ?, content = ?, image = ? WHERE id = ?',
                     (title, content, image_filename, announcement_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))

    conn.close()
    return render_template('edit.html', announcement=announcement)



if __name__ == '__main__':
    if not os.path.exists('static/uploads'):
        os.makedirs('static/uploads')
    init_db()
    app.run(debug=True)
