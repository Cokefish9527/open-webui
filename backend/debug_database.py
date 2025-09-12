import os
import sqlite3
from pathlib import Path

# Check current directory and data directory
print(f"Current working directory: {os.getcwd()}")

# Check DATA_DIR environment variable
data_dir = os.environ.get('DATA_DIR')
print(f"DATA_DIR environment variable: {data_dir}")

# Get the script directory (like in env.py)
script_dir = Path(__file__).parent
backend_dir = script_dir.parent
print(f"Script directory: {script_dir}")
print(f"Backend directory: {backend_dir}")

# Default DATA_DIR calculation
default_data_dir = backend_dir / "data"
print(f"Default DATA_DIR: {default_data_dir}")
print(f"Default DATA_DIR exists: {default_data_dir.exists()}")

# Check database URL
database_url = os.environ.get("DATABASE_URL", f"sqlite:///{default_data_dir}/webui.db")
print(f"DATABASE_URL: {database_url}")

# Extract the database file path from URL
if database_url.startswith("sqlite:///"):
    db_file_path = database_url[10:]  # Remove "sqlite:///"
    print(f"Database file path: {db_file_path}")
    print(f"Database file exists: {os.path.exists(db_file_path)}")
    
    # Check if directory exists and is writable
    db_dir = os.path.dirname(db_file_path)
    print(f"Database directory: {db_dir}")
    print(f"Database directory exists: {os.path.exists(db_dir)}")
    print(f"Database directory is writable: {os.access(db_dir, os.W_OK)}")
    
    # Try to create a test database
    try:
        test_db_path = os.path.join(db_dir, "test.db")
        conn = sqlite3.connect(test_db_path)
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()
        print(f"Successfully created test database at: {test_db_path}")
        os.remove(test_db_path)
        print("Test database removed successfully")
    except Exception as e:
        print(f"Failed to create test database: {e}")