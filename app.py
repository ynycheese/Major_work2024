from flask import Flask, render_template, redirect, url_for, session, request, make_response, send_from_directory, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import json
import sqlite3
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_key')

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    return datetime.fromisoformat(value).strftime(format)

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

    if product_id in cart_data:
        cart_data[product_id] += quantity
    else:
        cart_data[product_id] = quantity

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
        product = connection.execute('SELECT * FROM product_database WHERE id = ?', (product_id,)).fetchone()
        if product:
            product = dict(product)
            product['quantity'] = quantity
            product_list.append(product)
    
    subtotal = round(sum(item['price'] * item['quantity'] for item in product_list), 2)
    discount = 0
    total = subtotal - discount

    connection.close()
    return render_template('cartpage.html', cart=product_list, subtotal=subtotal, discount=discount, total=total)

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
        email = request.form['email']
        password = request.form['password']

        connection = get_db_connection()
        user = connection.execute('SELECT * FROM users_database WHERE email = ?', (email,)).fetchone()
        connection.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['email'] = user['email']
            return redirect(url_for('homepage'))
        else:
            error = 'Invalid email or password.'

    return render_template('loginpage.html', error=error)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == 'POST':
        first_name = request.form['first_name'].strip().lower()
        last_name = request.form['last_name'].strip().lower()
        email = request.form['email'].strip().lower()
        confirmed_password = request.form['confirmed_password']
        password = request.form['password']

        if password != confirmed_password:
            error = 'Passwords do not match.'
            return render_template('signuppage.html', error=error)

        hashed_password = generate_password_hash(password)
        connection = get_db_connection()

        existing_user = connection.execute('SELECT * FROM users_database WHERE email = ?', (email,)).fetchone()

        if existing_user:
            error = 'Email already exists.'
            connection.close()
            return render_template('signuppage.html', error=error)

        try:
            connection.execute(
                'INSERT INTO users_database (first_name, last_name, email, password) VALUES (?, ?, ?, ?)',
                (first_name, last_name, email, hashed_password)
            )
            connection.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            error = 'An unexpected error occurred.'
        finally:
            connection.close()

    return render_template('signuppage.html', error=error)

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for('homepage'))

@app.route('/returns')
def returns():
    return render_template('returnspolicypage.html')

@app.route('/contactus')
def contactus():
    return render_template('contactuspage.html')

@app.route('/adminlogin', methods=['GET', 'POST'])
def adminlogin():
    error = None
    if request.method == 'POST':
        employee_name = request.form['employee_name']
        password = request.form['password']

        conn = get_db_connection()
        admin = conn.execute('SELECT * FROM admin_database WHERE employee_name = ?', (employee_name,)).fetchone()
        conn.close()

        if admin and check_password_hash(admin['password'], password):
            session['admin_id'] = admin['id']
            session['employee_name'] = admin['employee_name']
            return redirect(url_for('admindashboard'))
        else:
            error = 'Invalid credentials.'

    return render_template('adminlogin.html', error=error)

@app.route('/admin')
def admindashboard():
    if 'admin_id' not in session:
        return redirect(url_for('adminlogin'))
    
    return render_template('admindashboard.html', username=session.get('employee_name'))

@app.route('/adminlogout', methods=['GET', 'POST'])
def adminlogout():
    session.pop('admin_id', None)
    session.pop('employee_name', None)
    return '', 204

@app.route('/category/<category_name>')
def categorypage(category_name):
    connection = get_db_connection()
    products = connection.execute('SELECT * FROM product_database WHERE category = ?', (category_name,)).fetchall()
    connection.close()

    if not products:
        return render_template('categorypage.html', category=category_name, products=[], empty=True)
    return render_template('categorypage.html', category=category_name, products=products, empty=False)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    
    user = connection.execute('SELECT * FROM users_database WHERE id = ?', (session['user_id'],)).fetchone()

    orders = connection.execute('''
        SELECT * FROM orders
        WHERE user_id = ?
        ORDER BY order_date DESC
    ''', (session['user_id'],)).fetchall()

    orders_with_items = []
    for order in orders:
        items = connection.execute('''
            SELECT oi.quantity, oi.price, p.product 
            FROM order_items oi
            JOIN product_database p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        ''', (order['id'],)).fetchall()
        orders_with_items.append({
            'order': order,
            'items': items
        })

    connection.close()

    return render_template('profilepage.html', user=user, orders=orders_with_items)


@app.route('/checkout', methods=['POST'])
def checkout():
    user_id = session.get('user_id')
    guest_name = request.form.get('guest_name') if not user_id else None
    guest_email = request.form.get('guest_email') if not user_id else None

    pickup_location = request.form['pickup_location']
    cart = get_cart()
    total_amount = sum(item['price'] * item['quantity'] for item in cart)

    conn = sqlite3.connect('website_database.db')
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO orders (user_id, guest_name, guest_email, order_date, total_amount, pickup_location)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, guest_name, guest_email, datetime.now().isoformat(), total_amount, pickup_location))

    order_id = cursor.lastrowid

    for item in cart:
        cursor.execute("""
            INSERT INTO order_items (order_id, product_id, quantity, price)
            VALUES (?, ?, ?, ?)
        """, (order_id, item['product_id'], item['quantity'], item['price']))

    conn.commit()
    conn.close()

    resp = make_response("Order placed successfully!")
    resp.set_cookie('cart', '', max_age=0)
    return resp

def get_cart():
    cart_cookie = request.cookies.get('cart')
    cart_data = json.loads(cart_cookie) if cart_cookie else {}

    connection = get_db_connection()
    cart_items = []

    for product_id, quantity in cart_data.items():
        product = connection.execute('SELECT * FROM product_database WHERE id = ?', (product_id,)).fetchone()
        if product:
            item = dict(product)
            item['product_id'] = product['id']
            item['quantity'] = quantity
            cart_items.append(item)

    connection.close()
    return cart_items

@app.route('/admin/orders')
def view_all_orders():
    if 'admin_id' not in session:
        return redirect(url_for('adminlogin'))

    sort_order = request.args.get('sort', 'desc').lower()
    if sort_order not in ['asc', 'desc']:
        sort_order = 'desc'

    connection = get_db_connection()

    orders = connection.execute(f'''
        SELECT o.*, u.first_name, u.last_name, u.email
        FROM orders o
        LEFT JOIN users_database u ON o.user_id = u.id
        ORDER BY o.order_date {sort_order.upper()}
    ''').fetchall()

    orders_with_items = []
    for order in orders:
        items = connection.execute('''
            SELECT oi.quantity, oi.price, p.product
            FROM order_items oi
            JOIN product_database p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        ''', (order['id'],)).fetchall()

        orders_with_items.append({
            'order': order,
            'items': items
        })

    connection.close()

    return render_template('adminorders.html', all_orders=orders_with_items, current_sort=sort_order)

if __name__ == '__main__':
    app.run(debug=True)
