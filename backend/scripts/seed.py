import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.db import SessionLocal
from backend.app.seed import seed_database


def main() -> None:
    db = SessionLocal()
    try:
        seed_database(db)
        print("Synthetic FlowWise demo data seeded.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
