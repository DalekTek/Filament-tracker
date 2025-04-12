import aiosqlite
from datetime import datetime
from typing import List, Optional
from models import Filament

class Database:
    def __init__(self, database_path: str):
        self.database_path = database_path

    async def create_tables(self) -> None:
        async with aiosqlite.connect(self.database_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS filaments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    material_type TEXT NOT NULL,
                    initial_weight REAL NOT NULL,
                    current_weight REAL NOT NULL,
                    color TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """)
            await db.commit()

    async def add_filament(self, name: str, material_type: str, initial_weight: float, color: str) -> int:
        async with aiosqlite.connect(self.database_path) as db:
            now = datetime.utcnow()
            cursor = await db.execute(
                """
                INSERT INTO filaments (name, material_type, initial_weight, current_weight, color, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (name, material_type, initial_weight, initial_weight, color, now, now)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_filament(self, filament_id: int) -> Optional[Filament]:
        async with aiosqlite.connect(self.database_path) as db:
            async with db.execute(
                "SELECT * FROM filaments WHERE id = ?", (filament_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Filament(*row)
                return None

    async def get_all_filaments(self) -> List[Filament]:
        async with aiosqlite.connect(self.database_path) as db:
            async with db.execute("SELECT * FROM filaments") as cursor:
                rows = await cursor.fetchall()
                return [Filament(*row) for row in rows]

    async def update_weight(self, filament_id: int, new_weight: float) -> bool:
        async with aiosqlite.connect(self.database_path) as db:
            now = datetime.utcnow()
            cursor = await db.execute(
                """
                UPDATE filaments 
                SET current_weight = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_weight, now, filament_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete_filament(self, filament_id: int) -> bool:
        async with aiosqlite.connect(self.database_path) as db:
            cursor = await db.execute("DELETE FROM filaments WHERE id = ?", (filament_id,))
            await db.commit()
            return cursor.rowcount > 0