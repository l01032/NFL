"""
Sincroniza datos de NFL desde balldontlie (plan gratuito).

USO:
    python sync.py teams                   -> descarga los 32 equipos
    python sync.py games --season 2025     -> descarga el historial de una temporada
    python sync.py update                  -> trae solo los partidos nuevos

LIMITE DEL PLAN FREE: 5 solicitudes/minuto (igual que NBA). Este script lo
respeta automaticamente.

LIMITACION (presupuesto $0, documentada): el plan Free de la API de NFL
incluye teams/players/games (con marcador por cuarto), pero NO incluye
standings (posiciones de la liga), stats de jugador, jugadas (play-by-play)
ni datos de fantasy/apuestas - esos requieren plan pagado ALL-STAR o GOAT.
No se simulan ni se inventan esos datos en ningun punto de esta app.
"""
import argparse
import os
import sys
import time
from datetime import date, datetime, timedelta

import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
import db  # noqa: E402

load_dotenv()

API_BASE = "https://api.balldontlie.io/nfl/v1"
API_KEY = os.environ.get("BALLDONTLIE_API_KEY", "").strip()
SECONDS_BETWEEN_REQUESTS = 13


def _headers():
    if not API_KEY or API_KEY == "pon_aqui_tu_api_key_gratis":
        raise SystemExit(
            "Falta configurar BALLDONTLIE_API_KEY en tu archivo .env.\n"
            "Es la MISMA cuenta/API key que ya usas para la app de NBA."
        )
    return {"Authorization": API_KEY}


def _get(path, params=None):
    url = f"{API_BASE}{path}"
    while True:
        resp = requests.get(url, headers=_headers(), params=params, timeout=30)
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 60))
            print(f"  Rate limit alcanzado, esperando {wait}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()


def sync_teams():
    print("Descargando equipos de NFL...")
    data = _get("/teams")
    # Al igual que con NBA, filtramos por si viniera algun registro que no
    # sea un equipo actual de la liga (por precaucion, aunque en las pruebas
    # esta API solo devolvio los 32 equipos reales).
    current_teams = [t for t in data["data"] if (t.get("conference") or "").strip() in ("AFC", "NFC")]
    print(f"  {len(data['data'])} registros recibidos, {len(current_teams)} son equipos actuales de la NFL.")
    with db.get_conn() as conn:
        for t in current_teams:
            db.upsert_team(
                conn,
                {
                    "id": t["id"],
                    "full_name": t["full_name"],
                    "abbreviation": t["abbreviation"],
                    "location": t["location"],
                    "name": t["name"],
                    "conference": t["conference"],
                    "division": t["division"],
                },
            )
    print("Listo: equipos guardados localmente.")


def _save_games_page(conn, games):
    saved = 0
    for g in games:
        db.upsert_game(
            conn,
            {
                "id": g["id"],
                "date": g["date"][:10],  # la API manda fecha+hora en ISO, nos quedamos con YYYY-MM-DD
                "season": g.get("season"),
                "week": g.get("week"),
                "postseason": 1 if g.get("postseason") else 0,
                "status": g.get("status"),
                "status_state": g.get("status_state"),
                "venue": g.get("venue"),
                "summary": g.get("summary"),
                "home_team_id": g["home_team"]["id"],
                "visitor_team_id": g["visitor_team"]["id"],
                "home_team_score": g.get("home_team_score"),
                "visitor_team_score": g.get("visitor_team_score"),
                "home_q1": g.get("home_team_q1"), "home_q2": g.get("home_team_q2"),
                "home_q3": g.get("home_team_q3"), "home_q4": g.get("home_team_q4"),
                "home_ot": g.get("home_team_ot"),
                "visitor_q1": g.get("visitor_team_q1"), "visitor_q2": g.get("visitor_team_q2"),
                "visitor_q3": g.get("visitor_team_q3"), "visitor_q4": g.get("visitor_team_q4"),
                "visitor_ot": g.get("visitor_team_ot"),
            },
        )
        saved += 1
    return saved


def sync_games_for_season(season):
    print(f"Descargando partidos de la temporada {season} de NFL...")
    cursor = None
    total = 0
    page = 1
    while True:
        params = {"seasons[]": season, "per_page": 100}
        if cursor is not None:
            params["cursor"] = cursor
        data = _get("/games", params=params)
        with db.get_conn() as conn:
            total += _save_games_page(conn, data["data"])
            db.set_meta(conn, "last_full_season_synced", str(season))
        meta = data.get("meta", {})
        cursor = meta.get("next_cursor")
        print(f"  pagina {page}: {len(data['data'])} partidos (total acumulado: {total})")
        page += 1
        if not cursor:
            break
        time.sleep(SECONDS_BETWEEN_REQUESTS)
    print(f"Listo: {total} partidos de la temporada {season} guardados localmente.")


def sync_update():
    with db.get_conn() as conn:
        last_date = db.get_meta(conn, "last_update_date")

    if not last_date:
        print(
            "No hay sincronizacion previa registrada. Corre primero:\n"
            "  python sync.py teams\n"
            "  python sync.py games --season <temporada, ej. 2025>\n"
        )
        return

    start = datetime.strptime(last_date, "%Y-%m-%d").date() - timedelta(days=1)
    end = date.today()
    print(f"Actualizando partidos entre {start.isoformat()} y {end.isoformat()}...")

    # La NFL juega en fechas puntuales (no hay partido casi cada dia como en
    # NBA), asi que pedimos un dia a la vez con el filtro "dates[]".
    total = 0
    current = start
    while current <= end:
        d = current.isoformat()
        cursor = None
        while True:
            params = {"dates[]": d, "per_page": 100}
            if cursor is not None:
                params["cursor"] = cursor
            data = _get("/games", params=params)
            with db.get_conn() as conn:
                total += _save_games_page(conn, data["data"])
            meta = data.get("meta", {})
            cursor = meta.get("next_cursor")
            if not cursor:
                break
            time.sleep(SECONDS_BETWEEN_REQUESTS)
        current += timedelta(days=1)
        if current <= end:
            time.sleep(SECONDS_BETWEEN_REQUESTS)

    end_date = end.isoformat()

    with db.get_conn() as conn:
        db.set_meta(conn, "last_update_date", end_date)
        db.set_meta(conn, "last_update_run_at", datetime.now().isoformat(timespec="seconds"))

    print(f"Listo: {total} partidos actualizados. Proxima vez partira desde {end_date}.")


def main():
    parser = argparse.ArgumentParser(description="Sincroniza datos NFL locales desde balldontlie (plan free).")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("teams", help="Descarga los 32 equipos")

    p_games = sub.add_parser("games", help="Descarga el historial completo de una temporada")
    p_games.add_argument("--season", type=int, required=True, help="Año de inicio de temporada, ej. 2025 para 2025-26")

    sub.add_parser("update", help="Descarga solo los partidos nuevos desde la ultima sincronizacion")

    args = parser.parse_args()
    db.init_db()

    if args.command == "teams":
        sync_teams()
    elif args.command == "games":
        sync_games_for_season(args.season)
        with db.get_conn() as conn:
            db.set_meta(conn, "last_update_date", date.today().isoformat())
    elif args.command == "update":
        sync_update()


if __name__ == "__main__":
    main()
