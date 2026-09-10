// Passive Optimizer front end. Plain JS, no build step.
// Talks to the FastAPI app in src/web/app.py.

const $ = (sel) => document.querySelector(sel);
const state = {
  build: null,        // build card from /api/builds
  objective: "dps",
  job: null,          // job id
  es: null,           // EventSource
  result: null,
  tree: null,         // /api/tree/{version} payload
  treeVersion: null,
};

const fmt = {
  big(n) {
    if (n === null || n === undefined) return "–";
    const a = Math.abs(n);
    if (a >= 1e6) return (n / 1e6).toFixed(2) + "M";
    if (a >= 1e4) return (n / 1e3).toFixed(1) + "K";
    return Math.round(n).toLocaleString();
  },
  pct(p) { return (p >= 0 ? "+" : "") + p.toFixed(1) + "%"; },
};

function show(el, on = true) { el.hidden = !on; }
function setError(msg) { const e = $("#build-error"); e.textContent = msg || ""; show(e, !!msg); }

async function api(path, opts = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  let data = null;
  try { data = await res.json(); } catch (_) { /* no body */ }
  if (!res.ok) throw new Error((data && data.detail) || res.statusText);
  return data;
}

// ---------------------------------------------------------------- tabs
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
    show($("#pane-account"), tab.dataset.tab === "account");
    show($("#pane-paste"), tab.dataset.tab === "paste");
    setError("");
  });
});

// ---------------------------------------------------------------- 1. build
$("#account-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const name = $("#account-name").value.trim();
  if (!name) return;
  setError("");
  const box = $("#characters");
  box.innerHTML = '<span class="note">Looking up characters…</span>';
  show(box);
  try {
    const headers = {};
    const sess = $("#poesessid").value.trim();
    if (sess) headers["X-POESESSID"] = sess;
    const data = await api(`/api/accounts/${encodeURIComponent(name)}/characters`, { headers });
    if (!data.characters.length) { box.innerHTML = '<span class="note">No characters found on that account.</span>'; return; }
    box.innerHTML = "";
    data.characters
      .sort((a, b) => b.level - a.level)
      .forEach((c) => {
        const b = document.createElement("button");
        b.className = "opt";
        b.type = "button";
        b.innerHTML = `<span class="t">${esc(c.name)}</span><span class="s">${esc(c.ascendancy || c.class)} ${c.level} · ${esc(c.league)}</span>`;
        b.addEventListener("click", () => importCharacter(name, c.name, b));
        box.appendChild(b);
      });
  } catch (e) {
    box.innerHTML = "";
    show(box, false);
    setError(e.message);
  }
});

async function importCharacter(account, character, btn) {
  document.querySelectorAll("#characters .opt").forEach((o) => o.classList.toggle("sel", o === btn));
  setError("");
  showBuildCard(null, "Importing " + character + "…");
  try {
    const body = { account, character, poesessid: $("#poesessid").value.trim() || null };
    const card = await api("/api/builds", { method: "POST", body: JSON.stringify(body) });
    onBuildLoaded(card);
  } catch (e) { show($("#build-card"), false); setError(e.message); }
}

$("#paste-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const code = $("#paste-code").value.trim();
  if (!code) return;
  setError("");
  showBuildCard(null, "Reading build…");
  try {
    const card = await api("/api/builds", { method: "POST", body: JSON.stringify({ code }) });
    onBuildLoaded(card);
  } catch (e) { show($("#build-card"), false); setError(e.message); }
});

function showBuildCard(card, placeholder) {
  const el = $("#build-card");
  show(el);
  if (!card) { el.innerHTML = `<span class="note">${esc(placeholder)}</span>`; return; }
  const who = [card.ascendancy && card.ascendancy !== "None" ? card.ascendancy : card.class, card.level ? "Level " + card.level : ""].filter(Boolean).join(" · ");
  const s = card.stats;
  const statsLine = card.stats_source === "none"
    ? '<span class="note">Stats will be calculated when you run.</span>'
    : `<span class="mono small ash">${fmt.big(s.dps)} dps · ${(s.energy_shield > s.life) ? fmt.big(s.energy_shield) + " es" : fmt.big(s.life) + " life"} · ${fmt.big(s.ehp)} ehp · ${card.points} points</span>`;
  const src = card.stats_source === "pob" ? "Numbers from Path of Building" : card.stats_source === "estimated" ? "Numbers estimated with the assumptions below" : "";
  const jew = [];
  if (card.jewels.timeless) jew.push(card.jewels.timeless + " timeless");
  if (card.jewels.cluster) jew.push(card.jewels.cluster + " cluster");
  if (card.jewels.unique) jew.push(card.jewels.unique + " unique jewel" + (card.jewels.unique > 1 ? "s" : ""));
  el.innerHTML = `
    <span class="who">${esc(who)}</span>
    ${card.main_skill ? `<span class="small">${esc(card.main_skill)}</span>` : ""}
    ${statsLine}
    <span class="right">Tree ${esc((card.tree_version || "?").replace("_", "."))}${jew.length ? " · " + jew.join(", ") : ""}${src ? " · " + src : ""}</span>
    ${renderAssumptions(card)}`;
  el.querySelectorAll(".assume input").forEach((cb) => cb.addEventListener("change", () => toggleAssumption(card, cb)));
}

function renderAssumptions(card) {
  const list = card.assumptions || [];
  if (!list.length) return "";
  const chips = list.map((a) => `
    <label class="assume" title="${esc(a.reason)}"><input type="checkbox" data-var="${esc(a.var)}" ${a.enabled === false ? "" : "checked"}> ${esc(a.label)}</label>`).join("");
  return `<div class="assumptions"><span class="k">Assumed for the numbers</span>${chips}<span class="note">Hover a tag to see why. Untick anything you don't keep up on bosses.</span></div>`;
}

async function toggleAssumption(card, cb) {
  const disabled = [...document.querySelectorAll("#build-card .assume input")].filter((x) => !x.checked).map((x) => x.dataset.var);
  document.querySelectorAll("#build-card .assume input").forEach((x) => { x.disabled = true; });
  try {
    const updated = await api(`/api/builds/${card.build_id}/assumptions`, { method: "PATCH", body: JSON.stringify({ disabled }) });
    state.build = updated;
    showBuildCard(updated);
  } catch (e) {
    setError(e.message);
    document.querySelectorAll("#build-card .assume input").forEach((x) => { x.disabled = false; });
  }
}

function onBuildLoaded(card) {
  state.build = card;
  showBuildCard(card);
  show($("#step-goal"));
  show($("#step-working"), false);
  show($("#step-result"), false);
  $("#step-goal").scrollIntoView({ behavior: "smooth", block: "start" });
}

// ---------------------------------------------------------------- 2. goal
document.querySelectorAll(".goal .opt").forEach((o) => {
  o.addEventListener("click", () => {
    document.querySelectorAll(".goal .opt").forEach((x) => { x.classList.toggle("sel", x === o); x.setAttribute("aria-checked", x === o); });
    state.objective = o.dataset.objective;
  });
});

$("#run").addEventListener("click", startRun);
$("#again").addEventListener("click", () => {
  show($("#step-result"), false);
  show($("#step-working"), false);
  $("#step-goal").scrollIntoView({ behavior: "smooth", block: "start" });
});

async function startRun() {
  if (!state.build) return;
  const run = $("#run");
  run.disabled = true;
  setError("");
  const body = {
    build_id: state.build.build_id,
    objective: state.objective,
    allow_point_change: $("#allow-points").checked,
    max_point_change: +$("#max-point-change").value || 5,
    iterations: +$("#iterations").value || 15,
  };
  try {
    const { job_id } = await api("/api/jobs", { method: "POST", body: JSON.stringify(body) });
    state.job = job_id;
    state.result = null;
    $("#ticker").innerHTML = "";
    $("#meter-bar").style.width = "0%";
    $("#working-status").textContent = "Starting PoB workers…";
    show($("#step-working"));
    show($("#step-result"), false);
    $("#step-working").scrollIntoView({ behavior: "smooth", block: "start" });
    listen(job_id, body.iterations);
  } catch (e) {
    setError(e.message);
  } finally {
    run.disabled = false;
  }
}

$("#cancel").addEventListener("click", async () => {
  if (!state.job) return;
  $("#cancel").disabled = true;
  $("#working-status").textContent = "Stopping after this step…";
  try { await api(`/api/jobs/${state.job}/cancel`, { method: "POST" }); } catch (_) { /* ignore */ }
});

// ---------------------------------------------------------------- 3. working
function listen(jobId, maxIterations) {
  if (state.es) state.es.close();
  const es = new EventSource(`/api/jobs/${jobId}/events`);
  state.es = es;
  $("#cancel").disabled = false;

  es.addEventListener("queued", () => { $("#working-status").textContent = "Queued…"; });
  es.addEventListener("started", () => { $("#working-status").textContent = "Loading the build into PoB workers…"; });
  es.addEventListener("iteration", (e) => {
    const ev = JSON.parse(e.data);
    $("#meter-bar").style.width = Math.min(100, (ev.iteration / maxIterations) * 100) + "%";
    $("#working-status").textContent = `${ev.iteration} of up to ${maxIterations} · ${ev.candidates_evaluated} candidates checked · ${fmt.pct(ev.cumulative_pct)} so far`;
    const li = document.createElement("li");
    li.innerHTML = `<b>${ev.iteration}</b>${describeChange(ev)} <span class="up">${fmt.pct(ev.marginal_pct)}</span>`;
    $("#ticker").prepend(li);
  });
  es.addEventListener("done", async () => {
    es.close();
    state.es = null;
    $("#meter-bar").style.width = "100%";
    $("#working-status").textContent = "Done.";
    await showResult(jobId);
  });
  es.addEventListener("cancelled", async () => {
    es.close(); state.es = null;
    $("#working-status").textContent = "Stopped.";
    await showResult(jobId);
  });
  es.addEventListener("error", (e) => {
    let msg = "The optimizer stopped unexpectedly.";
    try { msg = JSON.parse(e.data).message || msg; } catch (_) { /* connection error */ }
    if (es.readyState === EventSource.CLOSED || (e.data)) {
      es.close(); state.es = null;
      $("#working-status").textContent = msg;
    }
  });
}

function describeChange(ev) {
  const names = (list) => list.map((x) => esc(x[1] || x[0])).join(", ");
  const rm = ev.removed && ev.removed.length ? `<span class="rm">${names(ev.removed)}</span>` : "";
  const add = ev.added && ev.added.length ? `<span class="add">${names(ev.added)}</span>` : "";
  const mast = ev.masteries && Object.keys(ev.masteries).length && !add ? '<span class="add">mastery effect</span>' : "";
  if (rm && add) return `Swapped ${rm} for ${add}`;
  if (add) return `Added ${add}`;
  if (rm) return `Removed ${rm}`;
  if (mast) return `Changed ${mast}`;
  return esc(ev.name);
}

// ---------------------------------------------------------------- 4. result
async function showResult(jobId) {
  let snap;
  try { snap = await api(`/api/jobs/${jobId}`); } catch (e) { $("#working-status").textContent = e.message; return; }
  if (!snap.result) { $("#working-status").textContent = snap.error || "No result."; return; }
  const r = snap.result;
  state.result = r;

  const objKey = state.objective === "balanced" ? "dps" : state.objective;
  const headline = state.objective === "balanced"
    ? (r.change_pct.dps + r.change_pct.life + r.change_pct.ehp) / 3
    : r.change_pct[objKey];
  const num = $("#hero-num");
  num.textContent = fmt.pct(headline);
  num.classList.toggle("down", headline < 0);
  const objName = { dps: "Damage", life: "Life", ehp: "Effective HP", balanced: "Overall" }[state.objective];
  const pts = r.points_after === r.points_before ? "same points" : `${r.points_before} → ${r.points_after} points`;
  $("#hero-lbl").textContent = `${objName} · ${r.iterations} change${r.iterations === 1 ? "" : "s"} · ${pts}${r.cancelled ? " · stopped early" : ""}`;

  $("#stats").innerHTML = ["dps", "life", "ehp"].map((k) => statTile(k, r)).join("") +
    `<div class="stat"><span class="k">Points</span><span class="v">${r.points_after} <span class="ash" style="font-size:14px">/ ${r.points_before}</span></span><span class="d ash">${r.points_after === r.points_before ? "unchanged" : (r.points_after > r.points_before ? "+" : "") + (r.points_after - r.points_before)}</span></div>`;

  const changes = $("#changes");
  changes.innerHTML = "";
  r.changes.forEach((c, i) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="n">${i + 1}</span><span class="what">${describeChange({ ...c, removed: c.removed || [], added: c.added || [], name: c.modification })}</span><span class="pct">${fmt.pct(c.improvement_pct)}</span>`;
    changes.appendChild(li);
  });

  const note = $("#result-note");
  const worse = [];
  if (state.objective !== "life" && r.change_pct.life < -2) worse.push(`Life dropped ${Math.abs(r.change_pct.life).toFixed(1)}%.`);
  if (state.objective !== "ehp" && r.change_pct.ehp < -5) worse.push(`Effective HP dropped ${Math.abs(r.change_pct.ehp).toFixed(1)}%.`);
  if (state.objective === "life" && r.change_pct.dps < -2) worse.push(`Damage dropped ${Math.abs(r.change_pct.dps).toFixed(1)}%.`);
  if (r.constraint_violations && r.constraint_violations.length) worse.push(r.constraint_violations.join(" "));
  if (worse.length) {
    note.textContent = worse.join(" ") + (state.objective === "dps" ? " Re-run with Survivability or Both if that matters for your content." : "");
    show(note);
  } else show(note, false);

  $("#download-xml").href = URL.createObjectURL(new Blob([r.xml], { type: "application/xml" }));

  show($("#step-result"));
  $("#step-result").scrollIntoView({ behavior: "smooth", block: "start" });
  await drawTree(r);
}

function statTile(k, r) {
  const label = { dps: "Damage", life: "Life", ehp: "Effective HP" }[k];
  if (k === "life" && r.before.life <= 1 && r.after.life <= 1) {
    return `<div class="stat"><span class="k">Life</span><span class="v">CI</span><span class="d ash">Chaos Inoculation; see effective HP</span></div>`;
  }
  const d = r.change_pct[k];
  const cls = d > 0.05 ? "up" : d < -0.05 ? "down" : "ash";
  return `<div class="stat"><span class="k">${label}</span><span class="v">${fmt.big(r.after[k])}</span><span class="d ${cls}">${fmt.pct(d)} <span class="ash">was ${fmt.big(r.before[k])}</span></span></div>`;
}

$("#copy-code").addEventListener("click", async () => {
  if (!state.result) return;
  const btn = $("#copy-code");
  try {
    await navigator.clipboard.writeText(state.result.pob_code);
    btn.textContent = "Copied";
  } catch (_) {
    window.prompt("Copy this build code:", state.result.pob_code);
    btn.textContent = "Copy new build code";
    return;
  }
  setTimeout(() => { btn.textContent = "Copy new build code"; }, 1800);
});

// ---------------------------------------------------------------- tree drawing
async function loadTree(version) {
  if (state.tree && state.treeVersion === version) return state.tree;
  const data = await api(`/api/tree/${encodeURIComponent(version || "latest")}`);
  state.tree = data;
  state.treeVersion = version;
  return data;
}

async function drawTree(r) {
  const wrap = $("#tree-wrap");
  wrap.innerHTML = '<span class="note" style="position:absolute;left:22px;bottom:14px">Drawing the tree…</span>';
  let tree;
  try { tree = await loadTree(r.tree_version || state.build.tree_version); }
  catch (e) { wrap.innerHTML = `<span class="note" style="position:absolute;left:22px;bottom:14px">Tree drawing unavailable: ${esc(e.message)}</span>`; return; }

  const byId = new Map(tree.nodes.map((n) => [n.i, n]));
  // Ascendancy nodes live in their own cluster far from the main tree and
  // never change; leave them out of the drawing entirely.
  const main = (id) => { const n = byId.get(id); return n && !n.a && n.t !== "ascendancy_start" ? n : null; };
  const orig = new Set(r.original_nodes.filter(main));
  const fin = new Set(r.final_nodes.filter(main));
  const removed = new Set([...orig].filter((n) => !fin.has(n)));
  const added = new Set([...fin].filter((n) => !orig.has(n)));
  const kept = new Set([...fin].filter((n) => orig.has(n)));
  const shown = [...new Set([...orig, ...fin])];
  if (!shown.length) { wrap.innerHTML = ""; return; }

  const xs = shown.map((n) => byId.get(n).x), ys = shown.map((n) => byId.get(n).y);
  const span = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys), 3000);
  const pad = span * 0.08;
  const box = { x: Math.min(...xs) - pad, y: Math.min(...ys) - pad };
  box.w = Math.max(...xs) + pad - box.x; box.h = Math.max(...ys) + pad - box.y;
  const inBox = (n) => n && n.x >= box.x && n.x <= box.x + box.w && n.y >= box.y && n.y <= box.y + box.h;
  // Sizes relative to the drawn area so a small build isn't dwarfed and a
  // sprawling one isn't a blob (u ~ 1% of the wider dimension).
  const u = Math.max(box.w, box.h) / 100;
  const radius = (n) => u * (n.t === "keystone" ? 0.95 : (n.t === "notable" || n.t === "jewel") ? 0.75 : n.t === "mastery" ? 0.6 : 0.48);
  const bgRadius = (n) => u * (n.t === "notable" ? 0.5 : 0.34);
  const line = (cls, na, nb, w) => `<line class="tree-edge ${cls}" x1="${na.x}" y1="${na.y}" x2="${nb.x}" y2="${nb.y}" style="stroke-width:${w.toFixed(0)}"/>`;

  const parts = [];
  parts.push(`<svg viewBox="${box.x.toFixed(0)} ${box.y.toFixed(0)} ${box.w.toFixed(0)} ${box.h.toFixed(0)}" xmlns="http://www.w3.org/2000/svg" role="img">`);
  parts.push(`<defs><filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="${(u * 0.8).toFixed(0)}" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>`);

  // background edges (main tree only)
  for (const [a, b] of tree.edges) {
    const na = byId.get(a), nb = byId.get(b);
    if (!inBox(na) || !inBox(nb) || na.a || nb.a) continue;
    parts.push(line("", na, nb, u * 0.16));
  }
  // removed path edges, then kept/added path edges on top
  for (const [a, b] of tree.edges) {
    if (orig.has(a) && orig.has(b) && !(fin.has(a) && fin.has(b))) parts.push(line("removed", byId.get(a), byId.get(b), u * 0.24));
  }
  for (const [a, b] of tree.edges) {
    if (fin.has(a) && fin.has(b)) parts.push(line("kept", byId.get(a), byId.get(b), u * 0.3));
  }
  // background nodes
  for (const n of tree.nodes) {
    if (!inBox(n) || n.a || orig.has(n.i) || fin.has(n.i) || n.t === "mastery" || n.t === "class_start" || n.t === "ascendancy_start") continue;
    parts.push(`<circle class="tree-node" cx="${n.x}" cy="${n.y}" r="${bgRadius(n).toFixed(0)}" style="stroke-width:${(u * 0.09).toFixed(0)}"/>`);
  }
  const labels = [];
  const drawSet = (set, cls) => {
    for (const id of set) {
      const n = byId.get(id);
      if (!n || n.t === "class_start") continue;
      parts.push(`<circle class="tree-node ${cls}" cx="${n.x}" cy="${n.y}" r="${radius(n).toFixed(0)}" style="stroke-width:${(u * 0.13).toFixed(0)}"/>`);
      if ((cls === "added" || cls === "removed") && (n.t === "notable" || n.t === "keystone" || n.t === "mastery")) {
        const dy = cls === "added" ? -u * 1.3 : u * 2.1;
        labels.push(`<text class="tree-label ${cls}" x="${n.x}" y="${(n.y + dy).toFixed(0)}" style="font-size:${(u * 1.3).toFixed(0)}px;letter-spacing:${(u * 0.07).toFixed(0)}px">${esc(n.n)}</text>`);
      }
    }
  };
  drawSet(kept, "kept");
  drawSet(removed, "removed");
  drawSet(added, "added");
  parts.push(...labels);
  parts.push("</svg>");
  wrap.innerHTML = parts.join("");
  enablePanZoom(wrap.querySelector("svg"), box);
}

function enablePanZoom(svg, box) {
  let vb = { ...box };
  const apply = () => svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
  let drag = null;
  svg.addEventListener("pointerdown", (e) => { drag = { x: e.clientX, y: e.clientY, vx: vb.x, vy: vb.y }; svg.setPointerCapture(e.pointerId); });
  svg.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const rect = svg.getBoundingClientRect();
    const scale = vb.w / rect.width;
    vb.x = drag.vx - (e.clientX - drag.x) * scale;
    vb.y = drag.vy - (e.clientY - drag.y) * scale;
    apply();
  });
  svg.addEventListener("pointerup", () => { drag = null; });
  svg.addEventListener("pointercancel", () => { drag = null; });
  svg.addEventListener("wheel", (e) => {
    e.preventDefault();
    const rect = svg.getBoundingClientRect();
    const mx = vb.x + ((e.clientX - rect.left) / rect.width) * vb.w;
    const my = vb.y + ((e.clientY - rect.top) / rect.height) * vb.h;
    const f = e.deltaY > 0 ? 1.15 : 1 / 1.15;
    const nw = Math.min(box.w * 3, Math.max(box.w / 8, vb.w * f));
    const nh = nw * (box.h / box.w);
    vb = { x: mx - (mx - vb.x) * (nw / vb.w), y: my - (my - vb.y) * (nh / vb.h), w: nw, h: nh };
    apply();
  }, { passive: false });
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
