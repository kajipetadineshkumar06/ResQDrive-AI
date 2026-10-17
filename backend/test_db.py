from database import engine


def check_database_connection() -> bool:
    """Check database connectivity only when explicitly called."""
    try:
        connection = engine.connect()
        connection.close()
    except Exception:
        print("Database connection failed.")
        return False
    print("Database connection succeeded.")
    return True


if __name__ == "__main__":
    check_database_connection()
