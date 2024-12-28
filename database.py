import sqlite3

connection = sqlite3.connect('my-database.db')
cursor = connection.cursor()


def get_db_connection():
    """Connect to the SQLite database and return the connection object."""
    connection = sqlite3.connect('business-database.db')
    connection.row_factory = sqlite3.Row 
    return connection


def initialise_database():
    
    # create_table_users = '''
    # CREATE TABLE IF NOT EXISTS users (
    #     username TEXT NOT NULL UNIQUE,
    #     password TEXT NOT NULL,
    #     profile_picture TEXT NOT NULL
    # );'''


    # create_table_reviews = '''
    # CREATE TABLE IF NOT EXISTS reviews (
    # id INTEGER PRIMARY KEY AUTOINCREMENT,
    # game_id INTEGER NOT NULL,
    # rating INTEGER NOT NULL,
    # review TEXT,
    # title TEXT,
    # date TEXT NOT NULL,
    # username TEXT NOT NULL,
    # profile_picture TEXT,
    # FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
    # );'''

    # create_table_games = '''
    # CREATE TABLE IF NOT EXISTS games (
    # id INTEGER PRIMARY KEY AUTOINCREMENT,
    # title TEXT NOT NULL,
    # description TEXT,
    # tags TEXT,
    # rating REAL,
    # image TEXT NOT NULL
    # );'''

    create_table_products = '''
    CREATE TABLE IF NOT EXISTS products (
        id INTERGER PRIMARY KEY AUTOINCREMENT
        name TEXT NOT NULL
        image TEXT NOT NULL
        description TEXT
        )'''

    cursor.execute("PRAGMA foreign_keys = ON;")

    # cursor.execute(create_table_users)
    # cursor.execute(create_table_games)
    # cursor.execute(create_table_reviews)

    connection.commit()
    connection.close()
    
    print('database is created successfully and data is inserted')

initialise_database()
