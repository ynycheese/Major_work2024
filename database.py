import sqlite3
import pandas as pd

csv_file = './uploads/product-database.csv'

conn = sqlite3.connect('website_database.db')
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS product_database (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    product TEXT NOT NULL,
    price REAL NOT NULL,
    image TEXT
    )"""
)

conn.commit()

df = pd.read_csv(csv_file)
df.to_sql('product_database', conn, if_exists='append', index=False)

print('database established')
conn.close()