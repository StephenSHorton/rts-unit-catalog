(() => {
  const C = window.CATALOG;
  const units = C.units;
  const lineage = C.lineage;
  const GAMES = C.games || [
    { id: "ta", year: 1997, short: "TA", name: "Total Annihilation" },
    { id: "sc", year: 2007, short: "SC", name: "Supreme Commander" },
    { id: "bar", year: 2023, short: "BAR", name: "Beyond All Reason" },
  ];
  const GAME_BY_ID = Object.fromEntries(GAMES.map((g) => [g.id, g]));

  const FACTIONS = {
    ta: [
      { id: "arm", label: "ARM" },
      { id: "core", label: "CORE" },
    ],
    sc: [
      { id: "uef", label: "UEF" },
      { id: "cybran", label: "Cybran" },
      { id: "aeon", label: "Aeon" },
      { id: "seraphim", label: "Seraphim" },
    ],
    bar: [
      { id: "arm", label: "Armada" },
      { id: "core", label: "Cortex" },
      { id: "legion", label: "Legion" },
    ],
  };
  const DOMAINS = [
    { id: "commander", label: "Command" },
    { id: "land", label: "Land" },
    { id: "air", label: "Air" },
    { id: "navy", label: "Navy" },
    { id: "structure", label: "Structure" },
    { id: "other", label: "Other" },
  ];
  const TECHS = [
    { id: "0", label: "Cmd" },
    { id: "1", label: "T1" },
    { id: "2", label: "T2" },
    { id: "3", label: "T3" },
    { id: "4", label: "Exp" },
  ];

  const state = {
    view: "gallery",
    game: "ta",
    unitId: null,
    returnTo: "#/ta",
    q: "",
    factions: new Set(),
    domains: new Set(DOMAINS.map((d) => d.id)),
    techs: new Set(TECHS.map((t) => t.id)),
  };

  const $ = (id) => document.getElementById(id);
  const stage = $("stage");
  const byId = Object.fromEntries(units.map((u) => [u.id, u]));

  function resetFactions(game) {
    state.factions = new Set((FACTIONS[game] || []).map((f) => f.id));
  }

  function parseHash() {
    const raw = (location.hash || "#/ta").replace(/^#\/?/, "");
    const parts = raw.split("/").filter(Boolean);
    if (parts[0] === "unit" && parts[1]) {
      return { view: "unit", unitId: parts[1], game: state.game };
    }
    if (parts[0] === "lineage") return { view: "lineage", unitId: null, game: state.game };
    if (GAME_BY_ID[parts[0]]) return { view: "gallery", unitId: null, game: parts[0] };
    return { view: "gallery", unitId: null, game: "ta" };
  }

  function applyRoute(route, isPop) {
    const prevView = state.view;
    const gameChanged = route.game && route.game !== state.game;
    state.view = route.view;
    if (route.game) state.game = route.game;
    state.unitId = route.unitId;
    if (route.view !== "unit") {
      state.returnTo = route.view === "lineage" ? "#/lineage" : `#/${state.game}`;
    }
    if (route.view === "lineage") {
      state.factions = new Set(["arm", "core", "uef", "cybran", "aeon", "seraphim", "legion"]);
    } else if (route.view === "gallery" && (gameChanged || prevView === "lineage" || state.factions.size === 0)) {
      resetFactions(state.game);
    }
    if (route.view !== "gallery" || !isPop) window.scrollTo(0, 0);
    render();
  }

  function go(path) {
    const next = path.startsWith("#") ? path : `#${path}`;
    if (location.hash === next) applyRoute(parseHash(), false);
    else location.hash = next;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function fmt(n) {
    if (n == null || Number.isNaN(Number(n))) return "—";
    const x = Number(n);
    if (Math.abs(x) >= 1000) return Math.round(x).toLocaleString();
    return String(x);
  }

  function techLabel(t) {
    if (t === 0) return "Cmd";
    if (t >= 4) return "T4";
    return "T" + t;
  }

  function gameLabel(id) {
    return (GAME_BY_ID[id] || {}).short || id.toUpperCase();
  }

  function metalWord(game) {
    return game === "sc" ? "MASS" : "METAL";
  }

  function matches(u) {
    if (state.view === "gallery" && u.game !== state.game) return false;
    if (state.view === "gallery" && !state.factions.has(u.faction)) return false;
    if (!state.domains.has(u.domain || "other")) return false;
    if (!state.techs.has(String(u.tech >= 4 ? 4 : u.tech))) return false;
    if (state.q) {
      const hay = `${u.name} ${u.aka || ""} ${u.code} ${u.description || ""} ${u.kind || ""} ${u.role}`.toLowerCase();
      if (!hay.includes(state.q)) return false;
    }
    return true;
  }

  function unitCard(u, opts = {}) {
    const a = document.createElement("a");
    a.className = `unit ${u.game}${opts.same ? " same-machine" : ""}`;
    a.href = `#/unit/${u.id}`;
    a.style.setProperty("--fac", `var(--${u.faction})`);
    const frame = document.createElement("div");
    frame.className = "frame";
    const pip = document.createElement("i");
    pip.className = "fac-pip";
    frame.appendChild(pip);
    if (u.image) {
      const img = document.createElement("img");
      img.src = u.image;
      img.alt = u.name;
      img.loading = "lazy";
      frame.appendChild(img);
    }
    const cap = document.createElement("div");
    cap.className = "caption";
    cap.innerHTML = `<strong>${escapeHtml(u.name)}</strong><span>${gameLabel(u.game)} · ${u.faction} · ${techLabel(u.tech)}</span>`;
    a.append(frame, cap);
    return a;
  }

  function chips(el, items, selected, onToggle, extraClass) {
    el.innerHTML = "";
    items.forEach((item) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = `chip ${extraClass ? item.id : ""}`;
      b.textContent = item.label;
      b.classList.toggle("on", selected.has(item.id));
      b.addEventListener("click", () => onToggle(item.id));
      el.appendChild(b);
    });
  }

  function renderEras() {
    const nav = $("eras");
    nav.innerHTML = "";
    GAMES.forEach((g) => {
      const a = document.createElement("a");
      a.href = `#/${g.id}`;
      a.className = state.view === "gallery" && state.game === g.id ? "on" : "";
      a.innerHTML = `<span class="yr">${g.year}</span>${g.short}`;
      nav.appendChild(a);
    });
    const lin = document.createElement("a");
    lin.href = "#/lineage";
    lin.className = state.view === "lineage" ? "on" : "";
    lin.innerHTML = `<span class="yr">1997–now</span>Lineage`;
    nav.appendChild(lin);
  }

  function renderFilters() {
    const onUnit = state.view === "unit";
    $("filters").classList.toggle("hidden", onUnit);
    $("search-wrap").classList.toggle("hidden", onUnit);
    if (onUnit) return;

    const facs = FACTIONS[state.view === "lineage" ? "ta" : state.game] || [];
    const facList = state.view === "lineage"
      ? [
          ...FACTIONS.ta,
          ...FACTIONS.sc,
          { id: "legion", label: "Legion" },
        ]
      : facs;

    if (state.view === "lineage" && ![...state.factions].some((f) => facList.find((x) => x.id === f))) {
      state.factions = new Set(facList.map((f) => f.id));
    }

    chips($("faction-filters"), facList, state.factions, (id) => {
      if (state.factions.has(id)) {
        if (state.factions.size === 1) return;
        state.factions.delete(id);
      } else state.factions.add(id);
      render();
    }, true);
    chips($("domain-filters"), DOMAINS, state.domains, (id) => {
      if (state.domains.has(id)) {
        if (state.domains.size === 1) return;
        state.domains.delete(id);
      } else state.domains.add(id);
      render();
    });
    chips($("tech-filters"), TECHS, state.techs, (id) => {
      if (state.techs.has(id)) {
        if (state.techs.size === 1) return;
        state.techs.delete(id);
      } else state.techs.add(id);
      render();
    });
  }

  function renderGallery() {
    const list = units.filter(matches);
    const g = GAME_BY_ID[state.game];
    $("count").textContent = `${list.length} ${g ? g.short : ""} machines`;
    document.title = `${g.name} · Archive`;
    const wall = document.createElement("div");
    wall.className = "wall";
    const frag = document.createDocumentFragment();
    list.forEach((u) => frag.appendChild(unitCard(u)));
    wall.appendChild(frag);
    stage.replaceChildren(wall);
  }

  function eraCol(gameId, list) {
    const g = GAME_BY_ID[gameId];
    const col = document.createElement("div");
    const lab = document.createElement("div");
    lab.className = "era-label";
    lab.textContent = `${g.year} · ${g.name}`;
    col.appendChild(lab);
    if (!list.length) {
      const empty = document.createElement("div");
      empty.className = "empty-era";
      empty.textContent = "No counterpart.";
      col.appendChild(empty);
      return col;
    }
    const grid = document.createElement("div");
    grid.className = "era";
    list.forEach((u) => grid.appendChild(unitCard(u)));
    col.appendChild(grid);
    return col;
  }

  function arrow() {
    const a = document.createElement("div");
    a.className = "arrow";
    a.textContent = "→";
    return a;
  }

  function renderLineage() {
    const list = units.filter((u) => {
      if (!state.factions.has(u.faction)) return false;
      if (!state.domains.has(u.domain || "other")) return false;
      if (!state.techs.has(String(u.tech >= 4 ? 4 : u.tech))) return false;
      if (state.q) {
        const hay = `${u.name} ${u.aka || ""} ${u.code} ${u.description || ""} ${u.role}`.toLowerCase();
        if (!hay.includes(state.q)) return false;
      }
      return true;
    });
    $("count").textContent = `${list.length} across three eras`;
    document.title = "Lineage · Archive";
    const wrap = document.createElement("div");
    wrap.className = "lineage";
    const byRole = new Map();
    list.forEach((u) => {
      const arr = byRole.get(u.role) || [];
      arr.push(u);
      byRole.set(u.role, arr);
    });
    lineage.forEach((role) => {
      if (role.id === "other") return;
      const group = byRole.get(role.id) || [];
      const ta = group.filter((u) => u.game === "ta");
      const sc = group.filter((u) => u.game === "sc");
      const bar = group.filter((u) => u.game === "bar");
      if (!ta.length && !sc.length && !bar.length) return;
      const block = document.createElement("section");
      block.className = "role-block";
      block.innerHTML = `<h2>${escapeHtml(role.label)}</h2>`;
      const row = document.createElement("div");
      row.className = "role-row";
      row.append(eraCol("ta", ta), arrow(), eraCol("sc", sc), arrow(), eraCol("bar", bar));
      block.appendChild(row);
      wrap.appendChild(block);
    });
    stage.replaceChildren(wrap);
  }

  function sameCode(a, b) {
    return a.code && b.code && a.code.toLowerCase() === b.code.toLowerCase();
  }

  function progressionFor(u) {
    const byGame = { ta: [], sc: [], bar: [] };
    units.forEach((x) => {
      if (x.id === u.id) return;
      const direct = sameCode(x, u) && x.game !== u.game;
      const cousin = x.role === u.role && x.role !== "other";
      if (!direct && !cousin) return;
      byGame[x.game].push({ unit: x, direct });
    });
    ["ta", "sc", "bar"].forEach((g) => {
      byGame[g].sort((a, b) => Number(b.direct) - Number(a.direct) || a.unit.faction.localeCompare(b.unit.faction));
    });
    return byGame;
  }

  function renderUnit() {
    const u = byId[state.unitId];
    $("count").textContent = "";
    if (!u) {
      document.title = "Missing unit · Archive";
      stage.innerHTML = `<p class="missing">No unit at <code>${escapeHtml(state.unitId || "")}</code>.</p>`;
      return;
    }
    document.title = `${u.name} · ${gameLabel(u.game)}`;
    const g = GAME_BY_ID[u.game];
    const backHref = state.returnTo || `#/${u.game}`;
    const backLabel = state.returnTo === "#/lineage" ? "Lineage" : `${g ? g.short : u.game} wall`;
    const prog = progressionFor(u);
    const page = document.createElement("article");
    page.className = "page";
    page.innerHTML = `
      <a class="back" href="${backHref}" style="grid-column:1/-1">← ${escapeHtml(backLabel)}</a>
      <div class="page-hero ${u.game}">${u.image ? `<img src="${u.image}" alt="${escapeHtml(u.name)}" />` : ""}</div>
      <div>
        <h2>${escapeHtml(u.name)}</h2>
        <p class="aka">${escapeHtml([u.aka || u.kind, u.code, g && g.name].filter(Boolean).join(" · "))}</p>
        <div class="meta">
          <div><b>ERA</b>${g ? g.year + " · " + g.name : u.game}</div>
          <div><b>FACTION</b>${u.faction}</div>
          <div><b>TECH</b>${techLabel(u.tech)}</div>
          <div><b>DOMAIN</b>${u.domain}</div>
          <div><b>HP</b>${fmt(u.hp)}</div>
          <div><b>${metalWord(u.game)}</b>${fmt(u.cost_metal)}</div>
          <div><b>ENERGY</b>${fmt(u.cost_energy)}</div>
          <div><b>BUILD TIME</b>${fmt(u.build_time)}</div>
          <div><b>SPEED</b>${fmt(u.speed)}</div>
          <div><b>ROLE</b>${u.role}</div>
        </div>
        ${u.weapons && u.weapons.length ? `<ul class="weapons">${u.weapons.map((w) => `<li>${escapeHtml(w)}</li>`).join("")}</ul>` : ""}
      </div>
      <div class="progression"></div>
    `;
    const progEl = page.querySelector(".progression");
    const directBar = (prog.bar.find((x) => x.direct) || {}).unit;
    const directTa = (prog.ta.find((x) => x.direct) || {}).unit;
    let note = "Same battlefield job, three eras.";
    if (u.game === "ta" && directBar) note = `This chassis kept its unit code. In BAR it is <strong>${escapeHtml(directBar.name)}</strong>.`;
    if (u.game === "bar" && directTa) note = `Same unit code as TA’s <strong>${escapeHtml(directTa.name)}</strong> — the machine, rebuilt.`;
    progEl.innerHTML = `<h3>TA → SC → BAR</h3><p class="prog-note">${note}</p>`;
    const row = document.createElement("div");
    row.className = "role-row";
    function col(gameId) {
      const items = prog[gameId];
      const self = u.game === gameId ? [{ unit: u, direct: true }] : items;
      const wrap = eraCol(gameId, self.map((x) => x.unit));
      wrap.querySelectorAll(".unit").forEach((el, i) => {
        const rec = self[i];
        if (rec && rec.direct && rec.unit.id !== u.id) el.classList.add("same-machine");
        if (rec && rec.unit.id === u.id) el.style.opacity = "1";
      });
      return wrap;
    }
    row.append(col("ta"), arrow(), col("sc"), arrow(), col("bar"));
    progEl.appendChild(row);
    stage.replaceChildren(page);
  }

  function render() {
    renderEras();
    renderFilters();
    if (state.view === "unit") renderUnit();
    else if (state.view === "lineage") renderLineage();
    else renderGallery();
  }

  $("q").addEventListener("input", (e) => {
    state.q = e.target.value.trim().toLowerCase();
    render();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement !== $("q") && state.view !== "unit") {
      e.preventDefault();
      $("q").focus();
    }
    if (e.key === "Escape" && state.view === "unit") go(`/${state.game}`);
  });
  window.addEventListener("hashchange", () => applyRoute(parseHash(), true));

  if (!location.hash) location.hash = "#/ta";
  else applyRoute(parseHash(), false);
})();
