from flask import Flask, render_template, redirect, url_for, session, request, make_response, send_from_directory, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
import json
import sqlite3
import os
from datetime import datetime, timedelta
import re

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_key')

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    return datetime.fromisoformat(value).strftime(format)

def get_db_connection():
    connection = sqlite3.connect('website_database.db')
    connection.row_factory = sqlite3.Row
    return connection

def require_admin_access(min_level=3):
    if 'admin_id' not in session:
        return False
    conn = get_db_connection()
    admin = conn.execute('SELECT * FROM admin_database WHERE id = ?', (session['admin_id'],)).fetchone()
    conn.close()
    return admin and admin['access'] <= min_level

def nocache(view):
    def no_cache_wrapper(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    no_cache_wrapper.__name__ = view.__name__
    return no_cache_wrapper

@app.after_request
def add_header(response):
    if 'admin_id' not in session:
        response.headers['Cache-Control'] = 'no-store'
    return response

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
    user_points = 0

    if 'user_id' in session:
        user = connection.execute('SELECT points FROM users_database WHERE id = ?', (session['user_id'],)).fetchone()
        if user and user['points'] is not None:
            user_points = user['points']
            if user_points >= 200:
                discount = 10
        total = max(subtotal - discount, 0)

    connection.close()
    return render_template('cartpage.html', cart=product_list, subtotal=subtotal, discount=discount, total=total, user_points=user_points)


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

        # Validate password pattern server-side
        if not re.match(r'^(?=.*[A-Z])(?=.*\d).{8,}$', password):
            error = 'Password must be at least 8 characters long, contain at least one uppercase letter and one number.'
            return render_template('signuppage.html', error=error)

        if password != confirmed_password:
            error = 'Passwords do not match.'
            return render_template('signuppage.html', error=error)

        # Continue with your existing user existence check and user creation...
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

@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')

@app.route('/locations')
def locations():
    return render_template('locations.html')

@app.route('/helpsupport')
def helpsupport():
    return render_template('helpsupport.html')


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
@nocache
def admindashboard():
    if 'admin_id' not in session:
        return redirect(url_for('adminlogin'))
    
    return render_template('admindashboard.html', username=session.get('employee_name'))

@app.route('/adminlogout', methods=['GET', 'POST'])
def adminlogout():
    session.clear()
    resp = make_response(redirect(url_for('homepage')))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.route('/category/<category_name>')
def categorypage(category_name):
    sort = request.args.get('sort')

    query = "SELECT * FROM product_database WHERE category = ?"
    params = [category_name]

    if sort == 'price_asc':
        query += " ORDER BY price ASC"
    elif sort == 'price_desc':
        query += " ORDER BY price DESC"
    elif sort == 'name_asc':
        query += " ORDER BY product ASC"
    elif sort == 'name_desc':
        query += " ORDER BY product DESC"

    conn = sqlite3.connect('website_database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, params)
    products = cur.fetchall()
    conn.close()

    empty = len(products) == 0

    return render_template('categorypage.html',
                           category=category_name,
                           products=products,
                           empty=empty)

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
    subtotal = sum(item['price'] * item['quantity'] for item in cart)

    discount = 0
    if user_id:
        conn = sqlite3.connect('website_database.db')
        conn.row_factory = sqlite3.Row 
        user = conn.execute('SELECT points FROM users_database WHERE id = ?', (user_id,)).fetchone()

        if user and user['points'] >= 200:
            discount = 10
        conn.close()

    total_amount = max(subtotal - discount, 0)

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

        cursor.execute("""
            UPDATE product_database
            SET stock = stock - ?
            WHERE id = ? AND stock >= ?
        """, (item['quantity'], item['product_id'], item['quantity']))

    if user_id:
        points_earned = int(total_amount)
        if discount == 10:
            cursor.execute("""
                UPDATE users_database
                SET points = points - 200 + ?
                WHERE id = ?
            """, (points_earned, user_id))
        else:
            cursor.execute("""
                UPDATE users_database
                SET points = points + ?
                WHERE id = ?
            """, (points_earned, user_id))

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
    if not require_admin_access(3):
        return redirect(url_for('adminlogin'))

    sort_order = request.args.get('sort', 'desc').lower()
    if sort_order not in ['asc', 'desc']:
        sort_order = 'desc'
    pickup_filters = request.args.getlist('pickup')

    conn = get_db_connection()
    all_pickups = [row['pickup_location'] for row in conn.execute('SELECT DISTINCT pickup_location FROM orders').fetchall()]
    if not pickup_filters:
        pickup_filters = all_pickups
    placeholders = ','.join('?' for _ in pickup_filters)
    
    orders = conn.execute(f'''
        SELECT o.*, u.first_name, u.last_name, u.email
        FROM orders o
        LEFT JOIN users_database u ON o.user_id = u.id
        WHERE o.pickup_location IN ({placeholders})
        ORDER BY o.order_date {sort_order.upper()}
    ''', pickup_filters).fetchall()

    orders_with_items = []
    for order in orders:
        items = conn.execute('''
            SELECT oi.quantity, oi.price, p.product
            FROM order_items oi
            JOIN product_database p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        ''', (order['id'],)).fetchall()
        orders_with_items.append({'order': order, 'items': items})

    conn.close()
    return render_template('adminorders.html', all_orders=orders_with_items, current_sort=sort_order, all_pickups=all_pickups, pickup_filters=pickup_filters)

@app.route('/admin/products')
def admin_products():
    if not require_admin_access(2):
        flash("This feature is not available for your level of security.")
        return redirect(url_for('admindashboard'))  
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM product_database').fetchall()
    conn.close()
    return render_template('adminproducts.html', products=products)

@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if not require_admin_access(2):
        flash("This feature is not available for your level of security.")
        return redirect(url_for('admindashboard'))  
    conn = get_db_connection()
    if request.method == 'POST':
        product = request.form['product']
        price = float(request.form['price'])
        category = request.form['category']
        stock = int(request.form['stock'])
        conn.execute('UPDATE product_database SET product = ?, price = ?, category = ?, stock = ? WHERE id = ?', (product, price, category, stock, product_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_products'))
    product = conn.execute('SELECT * FROM product_database WHERE id = ?', (product_id,)).fetchone()
    conn.close()
    if not product:
        return "Product not found", 404
    return render_template('editproduct.html', product=product)

@app.route('/admin/add_admin', methods=['GET', 'POST'])
def add_admin():
    if not require_admin_access(1):
        flash("This feature is not available for your level of security.")
        return redirect(url_for('admindashboard'))  

    conn = get_db_connection()
    error = success = None

    if request.method == 'POST':
        employee_name = request.form['employee_name']
        password = request.form['password']
        access_level = int(request.form['access'])
        hashed_password = generate_password_hash(password)
        try:
            conn.execute('INSERT INTO admin_database (employee_name, password, access) VALUES (?, ?, ?)', (employee_name, hashed_password, access_level))
            conn.commit()
            success = "New admin added."
        except sqlite3.IntegrityError:
            error = "Admin already exists."
    conn.close()
    return render_template('addadmin.html', error=error, success=success)


if __name__ == '__main__':
    app.run(debug=True)
