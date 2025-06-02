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
    conn.close()
    return render_template('announcement_detail.html', announcement=announcement)

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
        timestamp = datetime.now().strftime('%Y-%m-%d')

        image_filename = None
        if image and image.filename:
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            image_filename = filename

        conn = get_db_connection()
        conn.execute('INSERT INTO announcements (title, content, image, timestamp) VALUES (?, ?, ?, ?)',
                     (title, content, image_filename, timestamp))
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
        image = request.files['image']

        image_filename = announcement['image']  # 保留原本圖片
        if image and image.filename:
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
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
