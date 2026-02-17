import psycopg2
from psycopg2.extras import RealDictCursor
from config import settings

def get_db_connection():
    """Create and return a database connection."""
    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

def execute_query(query, params=None):
    """Execute a query and return results."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            result = cursor.fetchall() if cursor.description else None
            conn.commit()  # ← Always commit (safe for SELECT too)
            return result
    finally:
        conn.close()