from flask import Flask, render_template, redirect, url_for, session, request, make_response, send_from_directory
from flask import request, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
import json
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

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    connection = get_db_connection()
    product = connection.execute('SELECT * FROM product_database WHERE id = ?', (product_id,)).fetchone()
    connection.close()

    if product is None:
        return "Product not found", 404

    return render_template('productpage.html', product=product)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    cart = request.cookies.get('cart')
    cart_data = json.loads(cart) if cart else {}

    data = request.get_json()
    product_id = str(data['productId'])
    quantity = int(data['quantity'])

    # Update quantity or add new item
    if product_id in cart_data:
        cart_data[product_id] += quantity
    else:
        cart_data[product_id] = quantity

    # Save updated cart back into a cookie
    resp = make_response(jsonify({'message': 'Added to cart!'}))
    resp.set_cookie('cart', json.dumps(cart_data), max_age=60*60*24)  # 1 day
    return resp

@app.route('/cart')
def view_cart():
    cart = request.cookies.get('cart')
    cart_data = json.loads(cart) if cart else {}

    connection = get_db_connection()
    product_list = []

    for product_id, quantity in cart_data.items():
        product = connection.execute(
            'SELECT * FROM product_database WHERE id = ?', (product_id,)
        ).fetchone()
        if product:
            product = dict(product)
            product['quantity'] = quantity
            product_list.append(product)
    
    subtotal = round(sum(item['price'] * item['quantity'] for item in product_list),2)
    discount = 0

    total = (subtotal - discount)

    connection.close()
    return render_template('cartpage.html', cart=product_list, subtotal=subtotal,discount=discount, total=total)

@app.route('/search')
def search():
    query = request.args.get('query', '')

    connection = get_db_connection()
    results = connection.execute(
        "SELECT * FROM product_database WHERE product LIKE ?",
        ('%' + query + '%',)
    ).fetchall()
    connection.close()

    return render_template('searchresults.html', query=query, results=results)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        connection = get_db_connection()
        user = connection.execute('SELECT * FROM users_database WHERE username = ?', (username,)).fetchone()
        connection.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('homepage'))
        else:
            error = 'Invalid username or password.'

    return render_template('loginpage.html', error=error)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        confirmed_password = request.form['confirmed_password']
        password = request.form['password']

        if password != confirmed_password:
            error = 'Passwords do not match.'
            return render_template('signuppage.html', error=error)

        hashed_password = generate_password_hash(password)

        connection = get_db_connection()
        try:
            connection.execute(
                'INSERT INTO users_database (first_name, last_name, email, password) VALUES (?, ?, ?, ?)',
                (first_name, last_name, email, hashed_password)
            )
            connection.commit()
            connection.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            connection.close()
            error = 'Username or email already exists.'

    return render_template('signuppage.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('homepage'))

@app.route('/returns')
def returns():
    return render_template('returnspolicypage.html')

@app.route('/contactus')
def contactus():
    return render_template('contactuspage.html')

@app.route('/adminlogin')
def adminlogin():
    return render_template('adminlogin.html')

@app.route('/category/<category_name>')
def categorypage(category_name):
    connection = get_db_connection()
    products = connection.execute(
        'select * from product_database where category = ?', (category_name,)).fetchall()
    connection.close()

    if not products:
        return render_template('categorypage.html', category=category_name, products=[], empty=True)
    return render_template('categorypage.html', category=category_name,products=products, empty=False)
    

if __name__ == '__main__':
    app.run(debug=True)

