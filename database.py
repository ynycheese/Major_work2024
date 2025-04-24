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
    price INTEGER REAL NOT NULL,
    image TEXT,
    stock INTEGER,
    reviews TEXT
               
    )"""
)

conn.commit()

cursor.execute("DELETE FROM product_database")
conn.commit()

df = pd.read_csv(csv_file)
df.to_sql('product_database', conn, if_exists='append', index=False)

print('Database updated')


conn.close()
