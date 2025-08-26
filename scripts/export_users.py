import argparse
import dataset
from datetime import datetime


def dump_users(
    db_url: str,
    output: str,
    emails: list[str] | None = None,
    domains: list[str] | None = None,
    is_staff: bool = False,
    last_login_after: datetime | None = None,
) -> None:
    db = dataset.connect(db_url)

    conditions = []
    params = {}

    if emails:
        placeholders = ", ".join([f":email_{i}" for i in range(len(emails))])
        conditions.append(f"email IN ({placeholders})")
        for index, email in enumerate(emails):
            params[f"email_{index}"] = email

    if domains:
        domain_conditions = []
        for index, domain in enumerate(domains):
            domain_conditions.append(f"email LIKE :domain_{index}")
            params[f"domain_{index}"] = f"%@{domain}"
        conditions.append("(" + " OR ".join(domain_conditions) + ")")

    if is_staff:
        conditions.append("is_staff = :is_staff")
        params["is_staff"] = is_staff

    if last_login_after:
        conditions.append("last_login >= :last_login_after")
        params["last_login_after"] = last_login_after

    where_clause = " AND ".join(conditions)
    sql = 'SELECT * FROM "user"'
    if where_clause:
        sql += " WHERE " + where_clause

    rows = list(db.query(sql, params))

    # Generate update-or-insert statements
    with open(output, "w", encoding="utf-8") as f:
        for row in rows:
            updates = []
            insert_cols = []
            insert_vals = []

            for col, val in row.items():
                if col == "id":
                    continue  # don't include id in update, only in WHERE/INSERT
                insert_cols.append(f'"{col}"')

                if val is None:
                    updates.append(f"{col}=NULL")
                    insert_vals.append("NULL")
                else:
                    escaped = str(val).replace("'", "''")
                    updates.append(f"{col}='{escaped}'")
                    insert_vals.append(f"'{escaped}'")

            set_clause = ", ".join(updates)
            insert_cols_str = ", ".join(['"id"'] + insert_cols)
            insert_vals_str = ", ".join([str(row["id"])] + insert_vals)

            # UPDATE first
            f.write(f'UPDATE "user" SET {set_clause} WHERE id={row["id"]};\n')

            # INSERT if no row with that id exists
            f.write(
                f'INSERT INTO "user" ({insert_cols_str})\n'
                f"SELECT {insert_vals_str}\n"
                f"WHERE NOT EXISTS (SELECT 1 FROM \"user\" WHERE id={row['id']});\n\n"
            )

    print(f"Exported {len(rows)} users → {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dump users with filters.")
    parser.add_argument("uri", help="Database URL (SQLAlchemy style)")
    parser.add_argument("--emails", nargs="*", help="List of specific emails to export")
    parser.add_argument(
        "--domains", nargs="+", help="Filter by one or more email domains"
    )
    parser.add_argument(
        "--is-staff", action="store_true", help="Filter only staff users"
    )
    parser.add_argument(
        "--last-login-after",
        help="Filter users whose last_login is on or after this date (YYYY-MM-DD)",
    )
    parser.add_argument("--output", default="user_dump.sql", help="Output SQL file")

    args = parser.parse_args()

    if args.last_login_after:
        try:
            args.last_login_after = datetime.strptime(args.last_login_after, "%Y-%m-%d")
        except ValueError:
            parser.error(
                "Invalid date format for --last-login-after (expected YYYY-MM-DD)"
            )

    dump_users(
        db_url=args.uri,
        emails=args.emails,
        domains=args.domains,
        is_staff=args.is_staff,
        last_login_after=args.last_login_after,
        output=args.output,
    )
