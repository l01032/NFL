# NFL Stats Local (presupuesto $0)

Hermano del proyecto de NBA, mismo patrón: elige un equipo de la NFL, ve sus
últimos partidos con scroll infinito, y mira el desglose por cuarto de cada uno.
Corre local, se publica gratis, y se actualiza sola.

## Diferencias con la app de NBA

| | NBA | NFL |
|---|---|---|
| Equipos | 30 | 32 |
| Conferencias | East / West | AFC / NFC |
| Organización del calendario | casi diario | por semana (1 a 18) |
| Tiempo extra | hasta 3 OT | 1 solo OT |
| URL de la API | `api.balldontlie.io/v1` | `api.balldontlie.io/nfl/v1` |

El resto (SQLite local, Flask, scroll infinito, Render, GitHub Actions) es
exactamente el mismo patrón que ya armamos para NBA.

## Instalación

```bash
cd nfl-stats-app
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edita `.env` y pon tu API key — **es la misma cuenta/clave** que usas para la
app de NBA, no hace falta crear una cuenta nueva.

## Primera carga de datos

```bash
cd backend
python sync.py teams
python sync.py games --season 2025
python sync.py games --season 2026
```

## Correr la app

```bash
python app.py
```

Abre **http://localhost:5001** (puerto distinto al de NBA, que usa el 5000,
así puedes tener las dos corriendo al mismo tiempo si quieres).

## Publicarla en internet y automatizarla (mismo proceso que NBA)

1. Repositorio nuevo en GitHub (por ejemplo `nfl-stats-apps`), subido con
   GitHub Desktop — recuerda NO subir `.env`, y SÍ subir `nfl_local.db`.
2. Nuevo servicio en Render apuntando a este repositorio, con:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python backend/app.py`
3. Para la actualización automática: sube el archivo
   `.github/workflows/update-nfl-data.yml` (ya incluido aquí) y crea el Secret
   `BALLDONTLIE_API_KEY` en este nuevo repositorio (Settings → Secrets and
   variables → Actions) — aunque sea la misma clave, el Secret hay que
   crearlo de nuevo en cada repositorio, no se comparte entre repos.

## Limitaciones (plan gratuito, sin inventar nada)

| Funcionalidad | Estado | Por qué |
|---|---|---|
| Equipos, calendario, marcador final, por cuarto | ✅ Funciona | Incluido en el plan Free |
| Historial desde 2002 | ✅ Funciona | Incluido en el plan Free |
| Posiciones de la liga (standings) | ❌ No incluido | Requiere plan pagado ALL-STAR/GOAT |
| Estadísticas de jugador | ❌ No incluido | Requiere plan pagado |
| Jugadas / play-by-play | ❌ No incluido | Requiere plan pagado |
| Fantasy / apuestas | ❌ No incluido | Requiere plan pagado |
