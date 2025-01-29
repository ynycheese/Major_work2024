from flask import Flask, render_template, redirect, url_for, session, request, make_response, send_from_directory
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_key')

def get_db_connection():
    connection = sqlite3.connect('website_database.db')
    connection.row_factory = sqlite3.Row
    return connection

@app.route('/')
def homepage():
    connection = get_db_connection()
    products = connection.execute('SELECT * FROM product_database ORDER BY RANDOM() LIMIT 12').fetchall()
    connection.close()
    return render_template('homepage.html', products=products)

if __name__ == '__main__':
    app.run(debug=True)