// Colores oficiales reales de cada equipo (dato publico, no un logo).
const TEAM_COLORS = {
  ARI: ["#97233F", "#000000"], ATL: ["#A71930", "#000000"], BAL: ["#241773", "#000000"],
  BUF: ["#00338D", "#C60C30"], CAR: ["#0085CA", "#101820"], CHI: ["#0B162A", "#C83803"],
  CIN: ["#FB4F14", "#000000"], CLE: ["#311D00", "#FF3C00"], DAL: ["#041E42", "#869397"],
  DEN: ["#FB4F14", "#002244"], DET: ["#0076B6", "#B0B7BC"], GB: ["#203731", "#FFB612"],
  HOU: ["#03202F", "#A71930"], IND: ["#002C5F", "#A2AAAD"], JAX: ["#101820", "#D7A22A"],
  KC: ["#E31837", "#FFB81C"], LAC: ["#0080C6", "#FFC20E"], LAR: ["#003594", "#FFA300"],
  LV: ["#000000", "#A5ACAF"], MIA: ["#008E97", "#FC4C02"], MIN: ["#4F2683", "#FFC62F"],
  NE: ["#002244", "#C60C30"], NO: ["#D3BC8D", "#101820"], NYG: ["#0B2265", "#A71930"],
  NYJ: ["#125740", "#000000"], PHI: ["#004C54", "#A5ACAF"], PIT: ["#FFB612", "#101820"],
  SEA: ["#002244", "#69BE28"], SF: ["#AA0000", "#B3995D"], TB: ["#D50A0A", "#34302B"],
  TEN: ["#0C2340", "#4B92DB"], WAS: ["#5A1414", "#FFB612"],
};

function colorsFor(abbr) {
  return TEAM_COLORS[abbr] || ["#f0a500", "#1a1a1a"];
}

// Logos locales: carpeta "logos" junto a este archivo (un PNG por equipo, nombre = abreviatura).
// Si tu servidor sirve los archivos desde /static, cambia LOGO_DIR a "/static/logos".
const LOGO_DIR = "logos";
// Abreviaturas alternativas que puede mandar la API -> nombre real del archivo
const LOGO_ALIASES = { OAK: "LV", SD: "LAC", STL: "LAR", LA: "LAR", WSH: "WAS", JAC: "JAX" };

function logoFor(abbr) {
  if (!abbr) return "";
  return `${LOGO_DIR}/${LOGO_ALIASES[abbr] || abbr}.png`;
}

let currentTeam = null;
let nextBefore = null;
let hasMore = true;
let loadingPage = false;

const teamGridView = document.getElementById("team-grid-view");
const teamGamesView = document.getElementById("team-games-view");
const teamGrid = document.getElementById("team-grid");
const gamesList = document.getElementById("games-list");
const teamTitle = document.getElementById("team-title");
const loadingEl = document.getElementById("loading");
const noMoreEl = document.getElementById("no-more");
const syncStatusEl = document.getElementById("sync-status");

async function init() {
  await loadSyncStatus();
  await loadTeams();
  window.addEventListener("scroll", onScroll);
}

async function loadSyncStatus() {
  try {
    const res = await fetch("/api/sync-status");
    const data = await res.json();
    syncStatusEl.textContent = data.last_update_date
      ? `Datos actualizados hasta: ${data.last_update_date}`
      : "Sin datos aún — corre sync.py";
  } catch (e) {
    syncStatusEl.textContent = "";
  }
}

// Orden de las secciones en la pantalla principal (cambia el orden aquí si quieres otro)
const DIVISION_ORDER = ["West", "South", "North", "East"];
const CONFERENCE_ORDER = ["AFC", "NFC"];
// Prioridad: primero por división (West, South...), y dentro de cada una AFC y luego NFC
const SORT_BY_CONFERENCE_FIRST = false;
const LABEL_SEPARATOR = " ";

function orderIndex(list, text) {
  const i = list.findIndex((x) => (text || "").includes(x));
  return i === -1 ? 99 : i;
}

function divisionLabel(t) {
  const conf = t.conference || "";
  const div = t.division || "Otros equipos";
  return conf && !div.includes(conf) ? `${conf}${LABEL_SEPARATOR}${div}` : div;
}

function compareTeams(a, b) {
  const aDiv = orderIndex(DIVISION_ORDER, a.division);
  const bDiv = orderIndex(DIVISION_ORDER, b.division);
  const aConf = orderIndex(CONFERENCE_ORDER, a.conference || a.division);
  const bConf = orderIndex(CONFERENCE_ORDER, b.conference || b.division);
  const first = SORT_BY_CONFERENCE_FIRST ? [aConf - bConf, aDiv - bDiv] : [aDiv - bDiv, aConf - bConf];
  return first[0] || first[1] || divisionLabel(a).localeCompare(divisionLabel(b)) ||
    String(a.full_name).localeCompare(String(b.full_name));
}

function buildTeamCard(t) {
  const [primary, secondary] = colorsFor(t.abbreviation);
  const card = document.createElement("div");
  card.className = "team-card";
  card.style.setProperty("--team-primary", primary);
  card.style.setProperty("--team-secondary", secondary);
  card.onclick = () => openTeam(t);
  card.innerHTML = `
    <div class="team-badge">
      <img src="${logoFor(t.abbreviation)}" alt="${t.abbreviation}" loading="lazy">
    </div>
    <div class="team-name">${t.full_name}</div>
  `;

  // Si el logo no carga, se muestra la abreviatura como respaldo
  const img = card.querySelector(".team-badge img");
  img.addEventListener("error", () => {
    const span = document.createElement("span");
    span.className = "team-badge-abbr";
    span.textContent = t.abbreviation;
    img.replaceWith(span);
  });
  return card;
}

async function loadTeams() {
  const res = await fetch("/api/teams");
  const teams = await res.json();
  if (!teams.length) {
    teamGrid.innerHTML = `<p>No hay equipos guardados todavía. Corre <code>python sync.py teams</code> primero.</p>`;
    return;
  }

  // El contenedor principal ahora apila secciones; cada sección tiene su propia cuadrícula
  teamGrid.classList.remove("team-grid");
  teamGrid.classList.add("division-list");
  teamGrid.innerHTML = "";

  const sections = new Map();
  [...teams].sort(compareTeams).forEach((t) => {
    const label = divisionLabel(t);
    if (!sections.has(label)) {
      const section = document.createElement("section");
      section.className = "division";
      const title = document.createElement("h2");
      title.className = "division-title";
      title.textContent = label;
      const grid = document.createElement("div");
      grid.className = "team-grid";
      section.append(title, grid);
      teamGrid.appendChild(section);
      sections.set(label, grid);
    }
    sections.get(label).appendChild(buildTeamCard(t));
  });
}

function showTeamGrid() {
  teamGamesView.classList.add("hidden");
  teamGridView.classList.remove("hidden");
  currentTeam = null;
}

async function openTeam(team) {
  currentTeam = team;
  nextBefore = null;
  hasMore = true;
  gamesList.innerHTML = "";
  noMoreEl.classList.add("hidden");

  // Título con el logo del equipo
  teamTitle.textContent = "";
  const titleLogo = document.createElement("img");
  titleLogo.className = "title-logo";
  titleLogo.src = logoFor(team.abbreviation);
  titleLogo.alt = team.abbreviation;
  titleLogo.addEventListener("error", () => titleLogo.remove());
  teamTitle.appendChild(titleLogo);
  teamTitle.appendChild(document.createTextNode(team.full_name));

  const [primary, secondary] = colorsFor(team.abbreviation);
  teamGamesView.style.setProperty("--team-primary", primary);
  teamGamesView.style.setProperty("--team-secondary", secondary);
  teamGridView.classList.add("hidden");
  teamGamesView.classList.remove("hidden");
  window.scrollTo(0, 0);
  await loadMoreGames();
}

function quarterTableHTML(g) {
  if (!g.has_quarters) {
    return `<div class="quarters-empty">No hay desglose por cuarto para este partido.</div>`;
  }
  const labels = ["T1", "T2", "T3", "T4"];
  const teamRow = [...g.team_quarters];
  const oppRow = [...g.opponent_quarters];
  if (g.team_ot !== null || g.opponent_ot !== null) {
    labels.push("OT");
    teamRow.push(g.team_ot);
    oppRow.push(g.opponent_ot);
  }
  const headerCells = labels.map((l) => `<th>${l}</th>`).join("");
  const teamCells = teamRow.map((v) => `<td>${v ?? "-"}</td>`).join("");
  const oppCells = oppRow.map((v) => `<td>${v ?? "-"}</td>`).join("");

  return `
    <table class="quarters-table">
      <thead><tr><th></th>${headerCells}<th>F</th></tr></thead>
      <tbody>
        <tr><td>${g.is_home ? "Local" : "Visita"}</td>${teamCells}<td><b>${g.team_score}</b></td></tr>
        <tr><td>${g.opponent_abbr}</td>${oppCells}<td><b>${g.opponent_score}</b></td></tr>
      </tbody>
    </table>
  `;
}

function renderGame(g) {
  const row = document.createElement("div");
  row.className = "game-row-wrap";
  const vs = g.is_home ? "vs" : "@";
  const resultClass = g.result === "W" ? "badge-win" : g.result === "L" ? "badge-loss" : "";
  const weekLabel = g.postseason ? "Playoffs" : (g.week ? `Semana ${g.week}` : "");

  row.innerHTML = `
    <div class="game-row" role="button" tabindex="0">
      <div class="game-left">
        <span class="game-date">${g.date}${weekLabel ? " · " + weekLabel : ""}</span>
        <span class="game-opp">
          <img class="opp-logo" src="${logoFor(g.opponent_abbr)}" alt="" loading="lazy">
          <span>${vs} ${g.opponent_abbr} — ${g.opponent_name}</span>
        </span>
      </div>
      <div class="game-right">
        <span class="game-score">${g.team_score ?? "-"} : ${g.opponent_score ?? "-"}</span>
        ${g.result ? `<span class="badge-result ${resultClass}">${g.result}</span>` : ""}
        <span class="expand-arrow">▾</span>
      </div>
    </div>
    <div class="quarters-panel hidden">${quarterTableHTML(g)}</div>
  `;

  // Si el logo del rival no carga, simplemente se oculta
  const oppLogo = row.querySelector(".opp-logo");
  oppLogo.addEventListener("error", () => oppLogo.remove());

  const header = row.querySelector(".game-row");
  const panel = row.querySelector(".quarters-panel");
  header.addEventListener("click", () => panel.classList.toggle("hidden"));

  gamesList.appendChild(row);
}

async function loadMoreGames() {
  if (!currentTeam || loadingPage || !hasMore) return;
  loadingPage = true;
  loadingEl.classList.remove("hidden");

  const params = new URLSearchParams({ limit: 15 });
  if (nextBefore) params.set("before", nextBefore);

  const res = await fetch(`/api/teams/${currentTeam.id}/games?${params}`);
  const data = await res.json();

  data.games.forEach(renderGame);
  nextBefore = data.next_before;
  hasMore = data.has_more;

  loadingEl.classList.add("hidden");
  if (!hasMore) noMoreEl.classList.remove("hidden");
  loadingPage = false;
}

function onScroll() {
  if (teamGamesView.classList.contains("hidden")) return;
  const scrolledToBottom = window.innerHeight + window.scrollY >= document.body.offsetHeight - 300;
  if (scrolledToBottom) loadMoreGames();
}

init();
