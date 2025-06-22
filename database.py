import sqlite3
import pandas as pd
from werkzeug.security import generate_password_hash

csv_file = './uploads/product-database.csv'

conn = sqlite3.connect('website_database.db')
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS product_database (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    product TEXT NOT NULL,
    price REAL NOT NULL,
    image TEXT,
    stock INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users_database (
    id INTEGER PRIMARY KEY, 
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    password TEXT NOT NULL,
    mobile TEXT UNIQUE,
    email TEXT NOT NULL UNIQUE,
    address TEXT,
    points INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS admin_database (
    id INTEGER PRIMARY KEY,
    employee_name TEXT NOT NULL,
    password TEXT NOT NULL,
    access INTEGER NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    guest_name TEXT,
    guest_email TEXT,
    order_date TEXT,
    status TEXT DEFAULT 'Pending',
    total_amount REAL,
    pickup_location TEXT,
    FOREIGN KEY(user_id) REFERENCES users_database(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    price REAL,
    FOREIGN KEY(order_id) REFERENCES orders(id),
    FOREIGN KEY(product_id) REFERENCES product_database(id)
)
""")

cursor.execute("DELETE FROM product_database")
conn.commit()

df = pd.read_csv(csv_file)


expected_cols = {'category', 'product', 'price', 'image', 'stock'}
if expected_cols.issubset(df.columns):
    df.to_sql('product_database', conn, if_exists='append', index=False)
    print('Database updated')
else:
    print("CSV columns do not match table structure.")

conn.commit()
conn.close()
