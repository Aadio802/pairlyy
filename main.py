print("BOOT: main.py loaded")

import asyncio

async def main():
    print("BOOT: inside main()")

    from db.connection import init_database
    print("BOOT: imported init_database")

    await init_database()
    print("BOOT: init_database done")

    print("BOT IS ALIVE")

if __name__ == "__main__":
    asyncio.run(main())
