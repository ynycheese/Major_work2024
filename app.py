from flask import Flask, render_template, redirect, url_for, session, request, make_response, send_from_directory
from flask import request, jsonify, make_response
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

if __name__ == '__main__':
    app.run(debug=True)