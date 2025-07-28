import sqlite3

DB_NAME = "trades.db"

def init_db():
    """Initializes the database and creates the 'trades' table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coin_ticker TEXT NOT NULL,
            trade_type TEXT NOT NULL,
            average_entry_price REAL NOT NULL,
            total_position_size REAL NOT NULL,
            status TEXT NOT NULL,
            remaining_percent INTEGER NOT NULL,
            post_link TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_trade(ticker, trade_type, price, size, post_link):
    """Adds a new trade to the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO trades (coin_ticker, trade_type, average_entry_price, total_position_size, status, remaining_percent, post_link)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (ticker.upper(), trade_type.upper(), price, size, 'OPEN', 100, post_link))
    conn.commit()
    conn.close()

def get_open_trade_by_ticker(ticker, trade_type):
    """Retrieves a single open trade by its ticker and type."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM trades
        WHERE coin_ticker = ? AND trade_type = ? AND status != 'CLOSED'
    """, (ticker.upper(), trade_type.upper()))
    trade = cursor.fetchone()
    conn.close()
    if trade:
        # Convert tuple to a dictionary for easier access
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, trade))
    return None

def dca_update_trade(trade_id, new_avg_price, new_total_size):
    """Updates a trade after a DCA (buy) operation."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE trades
        SET average_entry_price = ?, total_position_size = ?
        WHERE id = ?
    """, (new_avg_price, new_total_size, trade_id))
    conn.commit()
    conn.close()

def sell_update_trade(trade_id, new_remaining_percent):
    """Updates a trade after a partial sell."""
    status = 'PARTIALLY_SOLD' if new_remaining_percent > 0 else 'CLOSED'
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE trades
        SET remaining_percent = ?, status = ?
        WHERE id = ?
    """, (new_remaining_percent, status, trade_id))
    conn.commit()
    conn.close()

def close_trade(trade_id):
    """Closes a trade completely."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE trades
        SET status = 'CLOSED', remaining_percent = 0
        WHERE id = ?
    """, (trade_id,))
    conn.commit()
    conn.close()
    
def get_all_open_positions():
    """Retrieves all open or partially sold positions."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades WHERE status = 'OPEN' OR status = 'PARTIALLY_SOLD'")
    trades = cursor.fetchall()
    conn.close()
    
    # Convert list of tuples to list of dictionaries
    if trades:
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, trade)) for trade in trades]
    return []