import typer
import asyncio
from app.database import init_db

cli_app = typer.Typer()

@cli_app.command()
def init_db_command():
    """
    Initializes the database.
    """
    print("Initializing the database...")
    asyncio.run(init_db())
    print("Database initialized.")

if __name__ == "__main__":
    cli_app()