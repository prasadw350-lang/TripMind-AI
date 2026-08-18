"""PostgreSQL persistence layer: users, trips, contact messages."""

import json
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row
from werkzeug.security import check_password_hash, generate_password_hash

from config import config


def get_connection():
    database_url = config.DATABASE_URL

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")

    return psycopg.connect(
        database_url,
        row_factory=dict_row,
    )


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS trips (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                destination TEXT NOT NULL,
                country TEXT,
                budget_inr INTEGER NOT NULL,
                days INTEGER NOT NULL,
                travel_type TEXT,
                interests TEXT,
                season TEXT,
                start_location TEXT,
                image_url TEXT,
                plan_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.commit()


# ---------------------------------------------------------------- users

def create_user(email: str, password: str):
    email = email.strip().lower()

    with get_connection() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO users
                    (email, password_hash, created_at)
                VALUES
                    (%s, %s, %s)
                RETURNING id
                """,
                (
                    email,
                    generate_password_hash(password),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

            user_id = cur.fetchone()["id"]
            conn.commit()

        except psycopg.errors.UniqueViolation:
            conn.rollback()
            raise ValueError(
                "An account with that email already exists."
            )

        return {
            "id": user_id,
            "email": email,
        }


def verify_user(email: str, password: str):
    email = (email or "").strip().lower()

    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,),
        ).fetchone()

    if row and check_password_hash(
        row["password_hash"],
        password,
    ):
        return {
            "id": row["id"],
            "email": row["email"],
        }

    return None


def user_exists(user_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()

    return row is not None


# ---------------------------------------------------------------- trips

def save_trip(user_id: int, trip: dict) -> int:

    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO trips (
                user_id,
                destination,
                country,
                budget_inr,
                days,
                travel_type,
                interests,
                season,
                start_location,
                image_url,
                plan_json,
                created_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
            RETURNING id
            """,
            (
                user_id,
                trip.get("destination"),
                trip.get("country"),
                int(trip.get("budget_inr") or 0),
                int(trip.get("days") or 0),
                trip.get("travel_type"),
                json.dumps(trip.get("interests") or []),
                trip.get("season"),
                trip.get("start_location"),
                trip.get("image_url"),
                json.dumps(trip.get("plan") or {}),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        trip_id = cur.fetchone()["id"]
        conn.commit()

        return trip_id


def list_trips(user_id: int):

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM trips
            WHERE user_id = %s
            ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()

    trips = []

    for r in rows:
        trips.append(
            {
                "id": r["id"],
                "destination": r["destination"],
                "country": r["country"],
                "budget_inr": r["budget_inr"],
                "days": r["days"],
                "travel_type": r["travel_type"],
                "interests": json.loads(
                    r["interests"] or "[]"
                ),
                "season": r["season"],
                "start_location": r["start_location"],
                "image_url": r["image_url"],
                "plan": json.loads(
                    r["plan_json"] or "{}"
                ),
                "created_at": r["created_at"],
            }
        )

    return trips


def delete_trip(user_id: int, trip_id: int) -> bool:

    with get_connection() as conn:
        cur = conn.execute(
            """
            DELETE FROM trips
            WHERE id = %s
              AND user_id = %s
            """,
            (trip_id, user_id),
        )

        deleted = cur.rowcount > 0
        conn.commit()

        return deleted


# ------------------------------------------------------------- messages

def save_message(
    name: str,
    email: str,
    message: str,
    user_id=None,
) -> int:

    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO messages (
                user_id,
                name,
                email,
                message,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id,
                name,
                email,
                message,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        message_id = cur.fetchone()["id"]
        conn.commit()

        return message_id