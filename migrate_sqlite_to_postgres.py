# migrate_sqlite_to_postgres.py

import sqlite3

from sqlalchemy import text

from app import app, db
from models import User, Link, ClickLog

# ==========================================
# SQLITE DATABASE PATH
# ==========================================

SQLITE_PATH = "instance/data.db"

# ==========================================
# CONNECT SQLITE
# ==========================================

sqlite_conn = sqlite3.connect(SQLITE_PATH)

sqlite_conn.row_factory = sqlite3.Row

sqlite_cursor = sqlite_conn.cursor()

# ==========================================
# MIGRATE
# ==========================================

with app.app_context():

    print("=" * 50)
    print("START SQLITE -> POSTGRESQL MIGRATION")
    print("=" * 50)

    # ==========================================
    # USER
    # ==========================================

    print("\nMigrating users...")

    sqlite_cursor.execute("""
        SELECT
            id,
            username,
            password,
            role
        FROM user
    """)

    users = sqlite_cursor.fetchall()

    user_count = 0

    for row in users:

        # tránh duplicate
        exists = User.query.filter_by(
            id=row["id"]
        ).first()

        if exists:
            continue

        user = User(
            id=row["id"],
            username=row["username"],
            password=row["password"],
            role=row["role"]
        )

        db.session.add(user)

        user_count += 1

    db.session.commit()

    print(f"Users migrated: {user_count}")

    # ==========================================
    # LINK
    # ==========================================

    print("\nMigrating links...")

    sqlite_cursor.execute("""
        SELECT
            id,
            user_id,
            original_url,
            short_code,
            clicks,
            title,
            created_at
        FROM link
    """)

    links = sqlite_cursor.fetchall()

    link_count = 0

    for row in links:

        exists = Link.query.filter_by(
            id=row["id"]
        ).first()

        if exists:
            continue

        link = Link(
            id=row["id"],
            user_id=row["user_id"],
            original_url=row["original_url"],
            short_code=row["short_code"],
            clicks=row["clicks"],
            title=row["title"],
            created_at=row["created_at"]
        )

        db.session.add(link)

        link_count += 1

    db.session.commit()

    print(f"Links migrated: {link_count}")

    # ==========================================
    # CLICK LOG
    # ==========================================

    print("\nMigrating click logs...")

    sqlite_cursor.execute("""
        SELECT
            id,
            link_id,
            user_id,
            country,
            device,
            revenue,
            created_at
        FROM click_log
    """)

    logs = sqlite_cursor.fetchall()

    log_count = 0

    for row in logs:

        exists = ClickLog.query.filter_by(
            id=row["id"]
        ).first()

        if exists:
            continue

        log = ClickLog(
            id=row["id"],
            link_id=row["link_id"],
            user_id=row["user_id"],
            country=row["country"],
            device=row["device"],
            revenue=row["revenue"],
            created_at=row["created_at"]
        )

        db.session.add(log)

        log_count += 1

    db.session.commit()

    print(f"Click logs migrated: {log_count}")

    # ==========================================
    # RESET POSTGRESQL SEQUENCES
    # ==========================================

    print("\nResetting PostgreSQL sequences...")

    db.session.execute(text("""
        SELECT setval(
            pg_get_serial_sequence('"user"', 'id'),
            COALESCE((SELECT MAX(id) FROM "user"), 1),
            true
        );
    """))

    db.session.execute(text("""
        SELECT setval(
            pg_get_serial_sequence('link', 'id'),
            COALESCE((SELECT MAX(id) FROM link), 1),
            true
        );
    """))

    db.session.execute(text("""
        SELECT setval(
            pg_get_serial_sequence('click_log', 'id'),
            COALESCE((SELECT MAX(id) FROM click_log), 1),
            true
        );
    """))

    db.session.commit()

    print("Sequences reset completed")

# ==========================================
# CLOSE SQLITE
# ==========================================

sqlite_conn.close()

# ==========================================
# DONE
# ==========================================

print("\n" + "=" * 50)
print("SQLITE -> POSTGRESQL MIGRATION COMPLETED")
print("=" * 50)