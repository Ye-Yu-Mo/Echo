"""
CLI工具：数据库初始化等管理命令
"""
from __future__ import annotations

import asyncio
import sys

from echo.db import close_pool, init_db


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m echo.cli <command>")
        print("Commands:")
        print("  init-db    Initialize database schema")
        sys.exit(1)

    command = sys.argv[1]

    if command == "init-db":
        print("Initializing database schema...")
        try:
            await init_db()
            print("Database schema initialized successfully.")
        except Exception as e:
            print(f"Failed to initialize database: {e}")
            sys.exit(1)
        finally:
            await close_pool()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
