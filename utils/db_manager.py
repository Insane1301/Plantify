import sqlite3


class DatabaseManager:
    DB_FILE = "plantify.db"

    @staticmethod
    def init_database():
        """Initialize the database with required tables"""
        conn = sqlite3.connect(DatabaseManager.DB_FILE)
        cursor = conn.cursor()

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                phone TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                land_size REAL,          
                annual_income REAL,      
                caste TEXT,              
                gender TEXT,             
                age INTEGER,             
                state TEXT,              
                is_tenant INTEGER DEFAULT 0, 
                has_bank_account INTEGER DEFAULT 0, 
                crops TEXT,              
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS market_trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                commodity TEXT NOT NULL,
                state TEXT NOT NULL,
                market TEXT NOT NULL,
                latest_price REAL,
                trend TEXT,
                percentage_change REAL,
                data_points_found INTEGER,
                average_price REAL,
                highest_price REAL,
                lowest_price REAL,
                prices_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
             """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS "diagnosis" (
	            "id"	INTEGER,
	            "user_id"	INTEGER NOT NULL,
	            "plant_name"	TEXT,
	            "disease_name"	TEXT,
	            "is_healthy"	INTEGER,
	            "created_at"	TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	            FOREIGN KEY("user_id") REFERENCES "users"("id"),
	            PRIMARY KEY("id" AUTOINCREMENT)
                )
            """
        )

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS api_cached_commodities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            commodity_id INTEGER,
            commodity_name TEXT UNIQUE
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_commodity_name ON api_cached_commodities(commodity_name)"
        )

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS api_cached_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_id INTEGER,
            state_name TEXT,
            district_id INTEGER,
            district_name TEXT,
            market_id INTEGER,
            market_name TEXT
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_state_name ON api_cached_locations(state_name)"
        )

        conn.commit()
        conn.close()
        print("Database initialized successfully!")

    @staticmethod
    def get_connection():
        conn = sqlite3.connect(DatabaseManager.DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn
