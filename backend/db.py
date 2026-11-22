"""
Capa de base de datos local (SQLite) para NFL.
Mismo criterio que la app de NBA: SQLite local, $0, sin servidor.
"""
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "nfl_local.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    abbreviation TEXT NOT NULL,
    location TEXT,
    name TEXT,
    conference TEXT,
    division TEXT
);

CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,            -- YYYY-MM-DD
    season INTEGER,
    week INTEGER,
    postseason INTEGER DEFAULT 0,
    status TEXT,
    status_state TEXT,
    venue TEXT,
    summary TEXT,
    home_team_id INTEGER NOT NULL,
    visitor_team_id INTEGER NOT NULL,
    home_team_score INTEGER,
    visitor_team_score INTEGER,
    -- La NFL solo tiene UN campo de tiempo extra (no varios OT como NBA).
    -- Vienen vacios para partidos de ligas/temporadas que la API no cubra.
    home_q1 INTEGER, home_q2 INTEGER, home_q3 INTEGER, home_q4 INTEGER, home_ot INTEGER,
    visitor_q1 INTEGER, visitor_q2 INTEGER, visitor_q3 INTEGER, visitor_q4 INTEGER, visitor_ot INTEGER,
    FOREIGN KEY (home_team_id) REFERENCES teams(id),
    FOREIGN KEY (visitor_team_id) REFERENCES teams(id)
);

CREATE INDEX IF NOT EXISTS idx_games_home ON games(home_team_id, date);
CREATE INDEX IF NOT EXISTS idx_games_visitor ON games(visitor_team_id, date);
CREATE INDEX IF NOT EXISTS idx_games_date ON games(date);

CREATE TABLE IF NOT EXISTS sync_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def upsert_team(conn, t):
    conn.execute(
        """
        INSERT INTO teams (id, full_name, abbreviation, location, name, conference, division)
        VALUES (:id, :full_name, :abbreviation, :location, :name, :conference, :division)
        ON CONFLICT(id) DO UPDATE SET
            full_name=excluded.full_name,
            abbreviation=excluded.abbreviation,
            location=excluded.location,
            name=excluded.name,
            conference=excluded.conference,
            division=excluded.division
        """,
        t,
    )


def upsert_game(conn, g):
    conn.execute(
        """
        INSERT INTO games (
            id, date, season, week, postseason, status, status_state, venue, summary,
            home_team_id, visitor_team_id, home_team_score, visitor_team_score,
            home_q1, home_q2, home_q3, home_q4, home_ot,
            visitor_q1, visitor_q2, visitor_q3, visitor_q4, visitor_ot
        ) VALUES (
            :id, :date, :season, :week, :postseason, :status, :status_state, :venue, :summary,
            :home_team_id, :visitor_team_id, :home_team_score, :visitor_team_score,
            :home_q1, :home_q2, :home_q3, :home_q4, :home_ot,
            :visitor_q1, :visitor_q2, :visitor_q3, :visitor_q4, :visitor_ot
        )
        ON CONFLICT(id) DO UPDATE SET
            date=excluded.date, season=excluded.season, week=excluded.week,
            postseason=excluded.postseason, status=excluded.status, status_state=excluded.status_state,
            venue=excluded.venue, summary=excluded.summary,
            home_team_score=excluded.home_team_score, visitor_team_score=excluded.visitor_team_score,
            home_q1=excluded.home_q1, home_q2=excluded.home_q2, home_q3=excluded.home_q3,
            home_q4=excluded.home_q4, home_ot=excluded.home_ot,
            visitor_q1=excluded.visitor_q1, visitor_q2=excluded.visitor_q2, visitor_q3=excluded.visitor_q3,
            visitor_q4=excluded.visitor_q4, visitor_ot=excluded.visitor_ot
        """,
        g,
    )


def set_meta(conn, key, value):
    conn.execute(
        "INSERT INTO sync_meta (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def get_meta(conn, key, default=None):
    row = conn.execute("SELECT value FROM sync_meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def list_teams(conn):
    return conn.execute("SELECT * FROM teams ORDER BY full_name").fetchall()


def list_team_games(conn, team_id, before_date=None, limit=15):
    params = {"team_id": team_id, "limit": limit}
    date_filter = ""
    if before_date:
        date_filter = "AND g.date < :before_date"
        params["before_date"] = before_date

    query = f"""
        SELECT
            g.id, g.date, g.season, g.week, g.postseason, g.status, g.status_state, g.venue, g.summary,
            g.home_team_id, g.visitor_team_id, g.home_team_score, g.visitor_team_score,
            g.home_q1, g.home_q2, g.home_q3, g.home_q4, g.home_ot,
            g.visitor_q1, g.visitor_q2, g.visitor_q3, g.visitor_q4, g.visitor_ot,
            ht.full_name AS home_full_name, ht.abbreviation AS home_abbr,
            vt.full_name AS visitor_full_name, vt.abbreviation AS visitor_abbr
        FROM games g
        JOIN teams ht ON ht.id = g.home_team_id
        JOIN teams vt ON vt.id = g.visitor_team_id
        WHERE (g.home_team_id = :team_id OR g.visitor_team_id = :team_id)
          AND g.status_state = 'final'
          {date_filter}
        ORDER BY g.date DESC, g.id DESC
        LIMIT :limit
    """
    return conn.execute(query, params).fetchall()
