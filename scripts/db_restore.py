import argparse
import sqlalchemy as sa


def import_sql(db_url: str, input_file: str) -> None:
    engine = sa.create_engine(db_url)

    with open(input_file, "r", encoding="utf-8") as f:
        sql_statements = f.read()
    with engine.begin() as conn:
        conn.execute(sa.text(sql_statements))
    print(f"Imported SQL objects from {input_file} to {db_url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import SQL file into database")
    parser.add_argument(
        "db",
        help="Database URL (SQLAlchemy style, e.g., postgresql://user:pass@host/db)",
    )
    parser.add_argument(
        "--input", help="SQL file to import. Default - dump.sql", default="dump.sql"
    )

    args = parser.parse_args()
    import_sql(db_url=args.db, input_file=args.input)
