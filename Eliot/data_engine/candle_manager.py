# data_engine/candle_manager.py

import sqlite3


DB_NAME = "database/candles.db"


def init_candle_db():

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candles
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            symbol TEXT,
            timeframe TEXT,

            candle_time TEXT,

            open REAL,
            high REAL,
            low REAL,
            close REAL,

            tick_volume REAL
        )
    """)

    conn.commit()
    conn.close()


def save_candle(
        symbol,
        timeframe,
        candle_time,
        open_price,
        high_price,
        low_price,
        close_price,
        tick_volume
):

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO candles
        (
            symbol,
            timeframe,
            candle_time,
            open,
            high,
            low,
            close,
            tick_volume
        )
        VALUES
        (?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (
        symbol,
        timeframe,
        candle_time,
        open_price,
        high_price,
        low_price,
        close_price,
        tick_volume
    ))

    conn.commit()
    conn.close()