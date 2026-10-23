/* Scanner magazzino UltraPixel — pistola USB in modalità tastiera (terminatore Invio).
   Ogni scansione/comando ha un ID generato qui: se la rete cade, la richiesta resta in coda
   e viene rispedita con lo stesso ID → il server non la esegue mai due volte. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const store = {
    get(k, d) { try { const v = localStorage.getItem("wms." + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem("wms." + k, JSON.stringify(v)); } catch (e) { /* storage non disponibile */ } },
  };
  const uuid = () => (crypto.randomUUID ? crypto.randomUUID() :
    ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, (c) => (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)));

  let mode = "login", senzaBadge = false;            // login | scan
  let lastCode = null, lastCommand = null, lastPrint = null, undoArmed = 0, askState = null, choiceState = null;

  // ---------- suoni ----------
  let actx = null;
  function beep(kind) {
    try {
      actx = actx || new (window.AudioContext || window.webkitAudioContext)();
      const seq = kind === "ok" ? [[1320, .08]] : kind === "errore" ? [[220, .18], [0, .06], [220, .18]] : [[660, .12], [0, .05], [660, .12]];
      let t = actx.currentTime;
      for (const [f, d] of seq) {
        if (f) { const o = actx.createOscillator(), g = actx.createGain(); o.frequency.value = f; o.type = "square";
          g.gain.value = .08; o.connect(g); g.connect(actx.destination); o.start(t); o.stop(t + d); }
        t += d;
      }
    } catch (e) { /* audio non disponibile */ }
  }

  // ---------- rete ----------
  async function api(path, body, method) {
    const h = { "Content-Type": "application/json", "X-Device-Token": store.get("device", "") };
    const s = store.get("session", null); if (s) h.Authorization = "Bearer " + s;
    const r = await fetch(path, { method: method || (body ? "POST" : "GET"), headers: h, body: body ? JSON.stringify(body) : undefined });
    const ct = r.headers.get("content-type") || "";
    const data = ct.includes("json") ? await r.json() : await r.text();
    if (!r.ok) { const e = new Error((data && data.messaggio) || "Errore"); e.data = data; e.status = r.status; throw e; }
    return data;
  }
  const isNetErr = (e) => !e.status;

  // ---------- coda offline ----------
  function queue() { return store.get("queue", []); }
  function setQueue(q) { store.set("queue", q); const el = $("queue"); el.hidden = !q.length; el.textContent = q.length + " da inviare"; }
  async function flush() {
    let q = queue();
    while (q.length) {
      const item = q[0];
      try {
        const r = await api(item.path, { ...item.body, offline: true });
        if (r.esito === "ERRORE") addReview(item, r.titolo || r.messaggio);
      } catch (e) {
        if (isNetErr(e)) { setNet(false); return; }
        addReview(item, (e.data && e.data.messaggio) || e.message);
      }
      q = queue().slice(1); setQueue(q);
    }
    setNet(true);
  }
  function enqueue(path, body) { const q = queue(); q.push({ path, body }); setQueue(q); setNet(false); }
  function addReview(item, why) {
    const list = store.get("review", []); list.push({ quando: item.body.client_ts, cosa: item.body.code || item.body.tipo, why });
    store.set("review", list.slice(-50)); renderReview();
  }
  function renderReview() {
    const list = store.get("review", []); $("review").hidden = !list.length;
    $("reviewlist").innerHTML = list.map((r) => `<li>${esc(r.cosa)} — ${esc(r.why)} <small>(${esc(new Date(r.quando).toLocaleString("it-IT"))})</small></li>`).join("");
  }
  function setNet(on) { const n = $("net"); n.className = "net " + (on ? "on" : "off"); n.textContent = on ? "Online" : "Senza rete"; }
  window.addEventListener("online", flush);
  setInterval(() => { if (queue().length) flush(); }, 8000);

  // ---------- rendering ----------
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const n = (v) => v == null ? "-" : Number(v).toLocaleString("it-IT", { maximumFractionDigits: 2 });
  const ICON = { ok: '<svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
    info: '<svg viewBox="0 0 24 24"><path d="M12 11v6M12 7.5v.01"/></svg>',
    err: '<svg viewBox="0 0 24 24"><path d="M7 7l10 10M17 7L7 17"/></svg>',
    att: '<svg viewBox="0 0 24 24"><path d="M12 6.5v7M12 17.5v.01"/></svg>', idle: '<svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>' };
  const FI = {
    roll: '<svg viewBox="0 0 24 24"><ellipse cx="8" cy="12" rx="4" ry="7"/><path d="M8 5h9c2.2 0 4 3.1 4 7s-1.8 7-4 7H8"/><ellipse cx="8" cy="12" rx="1.3" ry="2.3"/></svg>',
    layers: '<svg viewBox="0 0 24 24"><path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/></svg>',
    pin: '<svg viewBox="0 0 24 24"><path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg>',
    doc: '<svg viewBox="0 0 24 24"><path d="M14 3H6v18h12V7z"/><path d="M14 3v4h4M9 12h6M9 16h6"/></svg>',
    ruler: '<svg viewBox="0 0 24 24"><path d="M3 16l13-13 5 5L8 21z"/><path d="M7 12l2 2M10 9l2 2M13 6l2 2"/></svg>',
    user: '<svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/></svg>',
    cal: '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>',
    tag: '<svg viewBox="0 0 24 24"><path d="M3 12V3h9l9 9-9 9z"/><circle cx="7.5" cy="7.5" r="1.5"/></svg>',
    box: '<svg viewBox="0 0 24 24"><path d="M3 7l9-4 9 4v10l-9 4-9-4z"/><path d="M3 7l9 4 9-4M12 11v10"/></svg>',
  };
  // numeri all'italiana: "54.00 m" → "54 m", "57.78" → "57,78"
  const pretty = (t) => String(t || "").replace(/\b(\d+)\.(\d{1,3})\b/g, (m, a, b) => { b = b.replace(/0+$/, ""); return b ? a + "," + b : a; });
  function show(cls, title, msg) {
    $("result").className = "card result " + cls; $("ricon").innerHTML = ICON[cls] || ICON.idle;
    $("rtitle").textContent = pretty(title); $("rmsg").textContent = pretty(msg);
  }
  function facts(r) {
    const f = [], b = r.bobina, c = r.commessa, k = r.collo, res = r.risultato || r;
    if (b) f.push(["roll", "Bobina", b.barcode], ["layers", "Materiale", b.materiale], ["ruler", b.metri_stimati != null ? "Metri (stima)" : "Metri", (b.metri_stimati != null ? "≈ " + n(b.metri_stimati) : n(b.metri_fisici)) + " m"], ["pin", "Ubicazione", b.ubicazione || "—"]);
    else if (res.bobine && res.bobine.length) f.push(["roll", "Bobina", res.bobine[0].barcode + (res.bobine.length > 1 ? " +" + (res.bobine.length - 1) : "")],
      ["ruler", "Metri", n(res.bobine[0].metri) + " m"], ["pin", "Ubicazione suggerita", (res.ubicazione_suggerita || {}).codice || "leggi uno scaffale"]);
    if (c) f.push(["doc", "Commessa", c.commessa], ["user", "Cliente", c.cliente], ["tag", "Etichette", n(c.quantita)], ["cal", "Consegna", fmtDate(c.consegna)]);
    if (k) f.push(["box", "Collo", k.barcode], ["tag", "Articolo", k.articolo], ["ruler", "Pezzi", n(k.quantita)], ["pin", "Ubicazione", k.ubicazione || "—"]);
    const ctx = r.contesto || {};
    if (!c && ctx.commessa && f.length && f.length < 4) f.push(["doc", "Commessa", ctx.commessa]);
    const out = f.slice(0, 4);
    $("facts").hidden = !out.length;
    $("facts").innerHTML = out.map(([i, l, v]) => `<div class="fact"><span class="ic">${FI[i]}</span><span><small>${esc(l)}</small><b title="${esc(v)}">${esc(v)}</b></span></div>`).join("");
  }
  // ---------- ultime scansioni ----------
  const QUARTI = { UPQ0: "Finita", UPQ1: "1/4", UPQ2: "2/4", UPQ3: "3/4", UPQ4: "Intera" };
  function pushHistory(code, cls, title) {
    code = QUARTI[String(code).trim().toUpperCase()] || code;
    const h = store.get("history", []); h.unshift({ t: new Date().toISOString(), code, cls, title }); store.set("history", h.slice(0, 8)); renderHistory();
  }
  function renderHistory() {
    const h = store.get("history", []); $("historybox").hidden = !h.length;
    $("history").innerHTML = h.map((x) => `<li><span class="st ${esc(x.cls)}">${ICON[x.cls] || ICON.ok}</span>
      <time>${new Date(x.t).toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" })}</time>
      <span class="c">${esc(x.code)}</span><span class="t">${esc(x.title)}</span></li>`).join("");
  }
  function clearExtras() { $("opts").hidden = true; $("opts").innerHTML = ""; $("facts").hidden = true; $("facts").innerHTML = ""; $("ask").hidden = true; $("ask").innerHTML = ""; $("choices").hidden = true; $("choices").innerHTML = "";
    $("detail").innerHTML = ""; askState = null; choiceState = null; }

  function render(r) {
    clearExtras();
    const cls = { OK: "ok", INFO: "info", ERRORE: "err", SCONOSCIUTO: "err", DOPPIA: "att", AVVISO: "att", CHIEDI: "att", SCEGLI: "att", LOGIN: "ok" }[r.esito] || "idle";
    let title = r.titolo || r.messaggio, msg = r.titolo ? r.messaggio : "";
    // titoli brevi e leggibili da lontano: "Materiale sbagliato: serve X..." → titolo + spiegazione
    const cut = title ? title.indexOf(": ") : -1;
    if (cut > 0 && cut < 40 && title.length > 48) { msg = title.slice(cut + 2) + (msg ? " — " + msg : ""); title = title.slice(0, cut); }
    if (r.commessa && title && title.startsWith("Commessa")) title = "Commessa " + r.commessa.commessa;   // il cliente è già nei dati sotto
    show(cls, title, msg);
    facts(r);
    if (r.esito !== "LOGIN") pushHistory(r._code || lastCode || "", cls, title);
    beep(r.suono || (cls === "err" ? "errore" : cls === "att" ? "attenzione" : "ok"));
    if (r.contesto) renderCtx(r.contesto);
    if (r.comando) lastCommand = r.comando;
    if (r.stampa && r.stampa.length) { lastPrint = r.stampa; printLabels(r.stampa); }
    if (r.esito === "LOGIN" && r.badge) { if (senzaBadge) { show("info", "Badge non necessario", "Questa postazione lavora già a nome dell'operatore"); return; } return doLogin(r.badge); }
    if (r.chiedi) buildAsk(r.chiedi);
    if (r.scelte) buildChoices(r.scelte);
    if (r.opzioni) buildOptions(r.opzioni);
    if (r.prossimo) showNext(r.prossimo, true);
    if (r.commessa) $("detail").innerHTML = jobHtml(r.commessa);
    if (r.spedizione) $("detail").innerHTML = shipHtml(r.spedizione);
  }
  function renderCtx(c) {
    const chips = [];
    if (c.commessa) chips.push("Commessa " + c.commessa);
    if (c.in_attesa_ubicazione) chips.push("Da riporre " + c.in_attesa_ubicazione);
    if (c.stoccaggio_in) chips.push("Stoccaggio in " + c.stoccaggio_in);
    if (c.spedizione) chips.push("Spedizione " + c.spedizione);
    const el = document.querySelector(".sub"); if (el) el.textContent = chips.length ? chips.join(" · ") : (baseSub || "Leggi una commessa, una bobina o un'ubicazione.");
  }
  function jobHtml(j) {
    const rows = j.materiali.map((m) => {
      const bob = m.bobine.map((b) => `<span class="code">${esc(b.barcode)}</span> in ${esc(b.ubicazione || "?")}`).join("<br>");
      return `<tr><td>${esc(m.materiale)}${m.risolto ? "" : ' <span class="short">non associato</span>'}</td>
        <td class=num>${n(m.larghezza_mm)} mm</td><td class=num>${n(m.teorico)} m</td><td class=num>${n(m.prenotato)} m</td>
        <td class=num>${n(m.consumato)} m${Number(m.stimato) ? `<br><small>stima ${n(m.stimato)} m</small>` : ""}</td>
        <td>${bob || (Number(m.da_coprire) ? `<span class="short">mancano ${n(m.da_coprire)} m</span>` : "—")}</td></tr>`;
    }).join("");
    const fasi = (j.fasi || []).map((f) => `<span class="fase ${esc(f.stato)}">${esc(f.fase.charAt(0) + f.fase.slice(1).toLowerCase().replace(/_/g, " "))}</span>`).join("");
    return `<div class="who">${esc(j.cliente)}<small>articolo ${esc(j.articolo)} ${esc(j.descrizione || "")}, ${n(j.quantita)} etichette, consegna ${esc(fmtDate(j.consegna))}</small></div>
      <div class="scroll"><table><tr><th>Materiale</th><th class=num>Larghezza</th><th class=num>Previsto</th><th class=num>Prenotato</th><th class=num>Consumato</th><th>Bobine</th></tr>${rows}</table></div>
      <div class="fasi">${fasi}</div>`;
  }
  function fmtDate(d) { if (!d) return "-"; const [y, m, g] = String(d).split("-"); return g ? `${g}/${m}/${y}` : d; }
  function shipHtml(s) {
    return `<div class="who">${esc(s.cliente)}<small>spedizione ${esc(s.barcode)}</small></div><div class="scroll"><table><tr><th>Articolo</th><th class=num>Richiesti</th><th class=num>Preparati</th><th>Colli da prendere</th></tr>` +
      s.righe.map((r) => `<tr><td class="code">${esc(r.articolo)}</td><td class=num>${n(r.quantita_richiesta)}</td><td class=num>${n(r.quantita_preparata)}</td>
      <td>${(r.colli_suggeriti || []).map((c) => `<span class="code">${esc(c.barcode)}</span> ${n(c.pz)} pz in ${esc(c.ubicazione || "?")}`).join("<br>") || "—"}</td></tr>`).join("") + "</table></div>";
  }

  // ---------- modulo dati mancanti (in linea, niente finestre) ----------
  function buildAsk(ch) {
    askState = { tipo: ch.azione, dati: ch.dati, event_id: uuid() };   // un solo event_id per modulo: Invio doppio = una sola operazione
    const f = $("ask");
    f.innerHTML = ch.campi.map((c, i) => `<label>${esc(c.etichetta)}<input name="${esc(c.nome)}" data-tipo="${esc(c.tipo)}"
       ${c.obbligatorio ? "required" : ""} inputmode="${c.tipo === "numero" ? "decimal" : "text"}" value="${c.default != null ? esc(c.default) : ""}" ${i === 0 ? "autofocus" : ""}></label>`).join("")
      + `<button class="btn" type="submit">Conferma (Invio)</button>`;
    f.hidden = false;
    const first = f.querySelector("input"); (first || f.querySelector("button")).focus();
  }
  $("ask").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!askState) return;
    const payload = { ...askState.dati };
    for (const inp of $("ask").querySelectorAll("input")) {
      const v = inp.value.trim(); if (v === "") continue;
      payload[inp.name] = inp.dataset.tipo === "numero" ? Number(v.replace(",", ".")) : v;
    }
    const body = { event_id: askState.event_id, tipo: askState.tipo, payload, client_ts: new Date().toISOString() };
    await sendCommand(body);
  });
  async function sendCommand(body) {
    try { const r = await api("/api/command", body); clearExtras(); render({ ...r, _code: (body.tipo || "").replace(/_/g, " ").toLowerCase(), esito: (r.avvisi && r.avvisi.length) ? "AVVISO" : (r.esito === "OK" ? "OK" : r.esito === "INVARIATO" ? "INFO" : r.esito),
        titolo: r.messaggio, messaggio: [...(r.avvisi || []), r.prossimo_passo].filter(Boolean).join(" · "),
        comando: { event_id: r.event_id, tipo: r.comando }, stampa: r.stampa, contesto: r.contesto });
      if (r.esito === "OK" && r.bobine) { /* dopo un ricevimento la bobina aspetta l'ubicazione: basta scansionarla */ } }
    catch (e) {
      if (isNetErr(e)) { enqueue("/api/command", body); clearExtras(); show("att", "Registrato offline", "Sarà inviato appena torna la rete"); beep("attenzione"); }
      else { show("err", (e.data && e.data.messaggio) || e.message, ""); beep("errore"); }
    }
    focusScan();
  }

  // ---------- risposta a un tocco (fine lavoro: quanto è rimasto) ----------
  function buildOptions(list) {
    $("opts").innerHTML = list.map((o) => {
      const q = Number(o.codice.slice(-1));
      return `<button type="button" data-code="${esc(o.codice)}" class="${q === 0 ? "end" : ""}">${esc(o.etichetta)}<span class="tank"><i style="width:${q * 25}%"></i></span></button>`;
    }).join("");
    $("opts").hidden = false;
    for (const b of $("opts").querySelectorAll("button")) b.addEventListener("click", () => { const c = b.dataset.code; clearExtras(); doScan(c); });
  }

  // ---------- scelta tra codici ambigui ----------
  function buildChoices(scelte) {
    choiceState = scelte;
    $("choices").innerHTML = scelte.slice(0, 9).map((s) => `<li>${esc(s.etichetta)}</li>`).join("");
    $("choices").hidden = false;
  }

  // ---------- scansione ----------
  async function doScan(code, scelta) {
    lastCode = code;
    const body = { code, client_scan_id: uuid(), client_ts: new Date().toISOString(), scelta };
    if (queue().length) { enqueue("/api/scan", body); show("att", "Registrato offline", code); beep("attenzione"); flush(); return; }
    try { render(await api("/api/scan", body)); }
    catch (e) {
      if (isNetErr(e)) { enqueue("/api/scan", body); show("att", "Registrato offline", code + " · sarà inviato appena torna la rete"); beep("attenzione"); }
      else if (e.data && e.data.codice === "LOGIN_RICHIESTO") { setMode("login"); show("att", e.data.messaggio); beep("attenzione"); }
      else { show("err", (e.data && e.data.messaggio) || e.message); beep("errore"); }
    }
  }
  async function doLogin(badge) {
    try {
      const r = await api("/api/login", { badge });
      store.set("session", r.sessione); setStation(r); setMode("scan");
      show("ok", "Ciao " + r.operatore, "Postazione " + r.postazione.toLowerCase()); beep("ok");
    } catch (e) { show("err", isNetErr(e) ? "Senza rete non si può accedere" : ((e.data && e.data.messaggio) || e.message)); beep("errore"); }
  }
  function setMode(m) {
    mode = m; $("scanlabel").textContent = m === "login" ? "Leggi il tuo badge" : "Scansiona un codice"; $("logout").hidden = m === "login" || senzaBadge;
  }
  $("scan").addEventListener("keydown", (ev) => {
    if (ev.key !== "Enter") return;
    ev.preventDefault();
    const code = ev.target.value; ev.target.value = "";
    if (!code.trim()) return;
    if (mode === "login") doLogin(code.trim()); else doScan(code);
  });

  // ---------- tasti ----------
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && (askState || choiceState)) { clearExtras(); show("idle", "Annullato", ""); focusScan(); return; }
    if (choiceState && /^[1-9]$/.test(ev.key) && document.activeElement === $("scan")) {
      const s = choiceState[Number(ev.key) - 1]; if (!s) return; ev.preventDefault(); clearExtras(); doScan(lastCode, s); return;
    }
    if (ev.key === "F8") {
      ev.preventDefault();
      if (!lastCommand) { show("att", "Nessuna operazione da annullare"); return; }
      if (Date.now() - undoArmed > 5000) { undoArmed = Date.now(); show("att", "Premi di nuovo F8 per annullare", lastCommand.tipo.replace(/_/g, " ").toLowerCase()); beep("attenzione"); return; }
      undoArmed = 0;
      sendCommand({ event_id: uuid(), tipo: "ANNULLA_COMANDO", payload: { event_id: lastCommand.event_id }, client_ts: new Date().toISOString() });
      lastCommand = null;
    }
    if (ev.key === "F9" && lastPrint) { ev.preventDefault(); printLabels(lastPrint); }
  });

  // ---------- stampa etichette (iframe, nessun popup) ----------
  async function printLabels(list) {
    const byType = {}; for (const s of list) (byType[s.tipo] = byType[s.tipo] || []).push(s.id);
    for (const [tipo, ids] of Object.entries(byType)) {
      try {
        const html = await api("/api/etichette", { tipo, ids });
        const fr = $("printframe"); fr.onload = () => { try { fr.contentWindow.focus(); fr.contentWindow.print(); } catch (e) { /* stampa bloccata */ } focusScan(); };
        fr.srcdoc = html;
      } catch (e) { show("att", "Etichetta non stampata", "Premi F9 per riprovare"); }
    }
  }

  // ---------- focus sempre sul campo scanner ----------
  function focusScan() { if (!askState) $("scan").focus(); }
  document.addEventListener("click", (ev) => { if (!ev.target.closest("form,button,input")) focusScan(); });
  setInterval(() => { const a = document.activeElement; if (!askState && (!a || a === document.body)) focusScan(); }, 700);

  const SUB = { RICEVIMENTO: "Leggi l'etichetta del fornitore: al resto pensa il sistema.",
    MACCHINA: "Leggi la bobina prima di stampare e di nuovo a fine lavoro.",
    MAGAZZINO: "Leggi una bobina e poi lo scaffale, o lo scaffale e poi le bobine.",
    SPEDIZIONE: "Leggi la spedizione e poi i colli." };
  let baseSub = null;
  function showNext(nx, append) {
    if (!nx) return;
    const txt = `Prossimo: commessa ${nx.commessa}` + (nx.bobina ? ` — prendi ${nx.bobina} in ${nx.ubicazione || "?"}` : "");
    if (append) { $("rmsg").textContent = ($("rmsg").textContent ? $("rmsg").textContent + "  ·  " : "") + txt; }
    else show("info", `Prossimo lavoro: commessa ${nx.commessa}`, nx.bobina ? `Prendi ${nx.bobina} in ${nx.ubicazione || "?"} e leggila` : `${nx.cliente}`);
  }
  function setStation(r) { const st = r.dispositivo.replace(/^Postazione /, ""); $("station").textContent = st.charAt(0).toUpperCase() + st.slice(1); $("opname").textContent = r.operatore;
    baseSub = SUB[r.postazione] || null; if (baseSub) document.querySelector(".sub").textContent = baseSub;
    if (r.prossimo) showNext(r.prossimo, false); }
  function tick() { const d = new Date(); $("clock").textContent = d.toLocaleDateString("it-IT", { weekday: "short", day: "numeric", month: "short" }) + "  " + d.toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" }); }
  tick(); setInterval(tick, 20000);
  $("clearhist").addEventListener("click", () => { store.set("history", []); renderHistory(); focusScan(); });
  renderHistory();
  // ---------- avvio ----------
  $("savetoken").addEventListener("click", () => { store.set("device", $("devtoken").value.trim()); location.reload(); });
  $("logout").addEventListener("click", async () => { try { await api("/api/logout", {}); } catch (e) { /* offline */ }
    store.set("session", null); setMode("login"); show("idle", "Uscito"); focusScan(); });
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/static/sw.js", { scope: "/" }).catch(() => {});
  setQueue(queue()); renderReview();
  if (!store.get("device", "")) { $("setup").hidden = false; $("scanbox").hidden = true; $("devtoken").focus(); return; }
  if (store.get("session", null)) {
    api("/api/stato").then((r) => { setStation(r); setMode("scan"); })
      .catch((e) => { if (isNetErr(e)) { setMode("scan"); setNet(false); } else { store.set("session", null); setMode("login"); } })
      .finally(focusScan);
  } else {
    // una postazione con operatore predefinito lavora subito, senza badge
    api("/api/stato").then((r) => { senzaBadge = !!r.senza_badge; setStation(r); setMode("scan"); })
      .catch((e) => { if (isNetErr(e)) { setNet(false); setMode("scan"); } else setMode("login"); }).finally(focusScan);
  }
})();
