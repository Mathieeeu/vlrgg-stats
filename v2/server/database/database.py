import sqlite3
import os

DATABASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'vlrgg_stats.db'))

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # pour accéder aux colonnes par nom
    return conn

def init_database(overwrite: bool = False) -> None:
    """init la bdd avec le schéma"""
    print("Initializing database...")
    schema_path = os.path.join(os.path.dirname(__file__), '..', 'db', 'schema.sql')
    
    if not os.path.exists(schema_path):
        print("Schema file not found. Generating from models...")
        from .schema_generator import generate_schema
        schema_path = generate_schema()
        print(f"Schema generated: {schema_path}")
    
    if os.path.exists(DATABASE_PATH):
        print(f"Database already exists at: {DATABASE_PATH}")
        if not overwrite:
            print("Skipping initialization. Use overwrite=True to reinitialize.")
            return
        else:
            os.remove(DATABASE_PATH)
            print("Existing database removed.")
    
    conn = get_db_connection()
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = f.read()
    
    conn.executescript(schema)
    conn.commit()
    conn.close()
    
    print(f"Database initialized at: {DATABASE_PATH}")

def execute_query(query: str) -> list[dict] | None:
    """executer une requête sql et retourner les résultats"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(query)
        if cursor.description is not None:
            results = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            data = [dict(zip(columns, row)) for row in results]
            return data
        else:
            return None
    except sqlite3.Error as e:
        raise Exception(f"SQL error: {e}")
    finally:
        conn.close()