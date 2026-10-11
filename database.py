import aiosqlite

DB_NAME = "surebets.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS surebet_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_name TEXT, sport TEXT, market TEXT,
                bk1 TEXT, k1 REAL, bk2 TEXT, k2 REAL,
                profit_percent REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY, bank REAL, round_step INTEGER, min_profit REAL DEFAULT 1.0
            )
        """)
        await db.commit()

async def get_user_settings(user_id: int, default_bank: float, default_step: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT bank, round_step FROM user_settings WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0], row[1]
            else:
                await db.execute(
                    "INSERT INTO user_settings (user_id, bank, round_step) VALUES (?, ?, ?)",
                    (user_id, default_bank, default_step)
                )
                await db.commit()
                return default_bank, default_step

async def update_user_bank(user_id: int, bank: float):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO user_settings (user_id, bank, round_step) VALUES (?, ?, 500)
            ON CONFLICT(user_id) DO UPDATE SET bank = excluded.bank
        """, (user_id, bank))
        await db.commit()

async def update_user_step(user_id: int, step: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO user_settings (user_id, bank, round_step) VALUES (?, 100000.0, ?)
            ON CONFLICT(user_id) DO UPDATE SET round_step = excluded.round_step
        """, (user_id, step))
        await db.commit()
