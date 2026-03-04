/**
 * docsify - frontend script
 */

const PAGE_SIZE = 15;

const state = {
  articles:      [],
  filtered:      [],
  page:          1,
  activeTag:     null,
  activeAuthor:  null,
  searchQuery:   "",
  lang:          "vi",
  currentArticle: null,
  theme:         "light",
};

// ── Boot ──────────────────────────────────────────────────────────────────
async function boot() {
  // Configure marked to use highlight.js via custom renderer (marked v4+)
  const renderer = new marked.Renderer();
  renderer.code = function(code, lang) {
    // marked v4+ passes an object, v3 passes string
    const rawCode = typeof code === "object" ? code.text : code;
    const rawLang = (typeof code === "object" ? code.lang : lang) || "";
    const language = rawLang && hljs.getLanguage(rawLang) ? rawLang : null;
    const highlighted = language
      ? hljs.highlight(rawCode, { language }).value
      : hljs.highlightAuto(rawCode).value;
    const cls = language ? ` class="hljs language-${language}"` : ' class="hljs"';
    return `<pre><code${cls}>${highlighted}</code></pre>`;
  };
  marked.setOptions({ renderer });

  setTheme(localStorage.getItem("kb-theme") || "light", false);

  document.getElementById("search-input").addEventListener("input", (e) => {
    state.searchQuery = e.target.value.trim();
    document.getElementById("search-clear").style.display =
      state.searchQuery ? "inline" : "none";
    state.page = 1;
    applyFilters();
  });

  try {
    const base = document.querySelector("base")?.href || "./";
    const res = await fetch(base + "public/index.json");
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    state.articles = data.articles || [];
    state.filtered = [...state.articles];
    renderSidebar();
    renderList();
    document.getElementById("footer-stats").textContent =
      data.total + " articles // " + data.generated_at;
  } catch (e) {
    document.getElementById("article-list").innerHTML =
      '<div class="msg">[!] ' + e.message + "</div>";
  }
}

// ── Sidebar ───────────────────────────────────────────────────────────────
function renderSidebar() {
  // Tags
  const tagMap = {};
  state.articles.forEach((a) =>
    (a.tags || []).forEach((t) => { tagMap[t] = (tagMap[t] || 0) + 1; })
  );
  const tags = Object.entries(tagMap).sort((a, b) => b[1] - a[1]);
  document.getElementById("tag-list").innerHTML = tags
    .map(([t, n]) =>
      `<div class="tag-item${state.activeTag === t ? " on" : ""}" onclick="filterTag('${esc(t)}')">`+
      `#${t} <span class="tag-cnt">${n}</span></div>`
    ).join("");

  // Authors
  const authMap = {};
  state.articles.forEach((a) => {
    const au = field(a, "author");
    if (au) authMap[au] = (authMap[au] || 0) + 1;
  });
  const authors = Object.entries(authMap).sort((a, b) => b[1] - a[1]);
  document.getElementById("author-list").innerHTML = authors
    .map(([n, cnt]) =>
      `<div class="author-item${state.activeAuthor === n ? " on" : ""}" onclick="filterAuthor('${esc(n)}')">`+
      `${n} <span class="tag-cnt">${cnt}</span></div>`
    ).join("");
}

// ── List ──────────────────────────────────────────────────────────────────
function renderList() {
  const total = state.filtered.length;
  document.getElementById("result-count").textContent = total + " articles";

  // Filter badge
  const fb = document.getElementById("filter-badge");
  if (state.activeTag || state.activeAuthor || state.searchQuery) {
    const label = state.activeTag   ? "#" + state.activeTag
                : state.activeAuthor ? "@" + state.activeAuthor
                : '"' + state.searchQuery + '"';
    fb.innerHTML =
      `<span class="filter-chip">${label} <span class="filter-x" onclick="clearFilters()">[x]</span></span>`;
  } else {
    fb.innerHTML = "";
  }

  if (!total) {
    document.getElementById("article-list").innerHTML = '<div class="msg">-- no results --</div>';
    document.getElementById("pagination").innerHTML = "";
    return;
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);
  if (state.page > totalPages) state.page = 1;
  const slice = state.filtered.slice((state.page - 1) * PAGE_SIZE, state.page * PAGE_SIZE);

  document.getElementById("article-list").innerHTML = slice.map((a) => {
    const title   = field(a, "title")   || a.id;
    const summary = field(a, "summary") || "";
    const author  = field(a, "author")  || "";
    const tags    = (a.tags || []).slice(0, 6).map((t) => "#" + t).join("  ");
    return `<div class="article-card" onclick="openArticle('${esc(a.id)}')">` +
      `<div class="card-title">${h(title)}</div>` +
      `<div class="card-meta">${h(a.date || "")}  //  ${h(author)}</div>` +
      `<div class="card-summary">${h(summary)}</div>` +
      `<div class="card-tags">${h(tags)}</div>` +
      `</div>`;
  }).join("");

  renderPagination(totalPages);
}

function renderPagination(total) {
  const el = document.getElementById("pagination");
  if (total <= 1) { el.innerHTML = ""; return; }
  const p = state.page;

  let pages = [];
  if (total <= 7) {
    pages = Array.from({ length: total }, (_, i) => i + 1);
  } else if (p <= 4) {
    pages = [1,2,3,4,5,"…",total];
  } else if (p >= total - 3) {
    pages = [1,"…",total-4,total-3,total-2,total-1,total];
  } else {
    pages = [1,"…",p-1,p,p+1,"…",total];
  }

  let html = `<button class="pg-btn" onclick="goPage(${p-1})" ${p===1?"disabled":""}>[&lt;]</button>`;
  pages.forEach((n) => {
    if (n === "…") html += `<span class="pg-dots">...</span>`;
    else html += `<button class="pg-btn${n===p?" on":""}" onclick="goPage(${n})">${n}</button>`;
  });
  html += `<button class="pg-btn" onclick="goPage(${p+1})" ${p===total?"disabled":""}>[&gt;]</button>`;
  el.innerHTML = html;
}

function goPage(n) {
  const total = Math.ceil(state.filtered.length / PAGE_SIZE);
  if (n < 1 || n > total) return;
  state.page = n;
  renderList();
  document.getElementById("main").scrollTop = 0;
}

// ── Filters ───────────────────────────────────────────────────────────────
function filterTag(t) {
  state.activeTag    = state.activeTag === t ? null : t;
  state.activeAuthor = null;
  state.page = 1;
  applyFilters();
}

function filterAuthor(a) {
  state.activeAuthor = state.activeAuthor === a ? null : a;
  state.activeTag    = null;
  state.page = 1;
  applyFilters();
}

function clearFilters() {
  state.activeTag = state.activeAuthor = null;
  state.searchQuery = "";
  state.page = 1;
  document.getElementById("search-input").value = "";
  document.getElementById("search-clear").style.display = "none";
  applyFilters();
}

function clearSearch() {
  state.searchQuery = "";
  state.page = 1;
  document.getElementById("search-input").value = "";
  document.getElementById("search-clear").style.display = "none";
  applyFilters();
}

function applyFilters() {
  let list = [...state.articles];
  if (state.activeTag)
    list = list.filter((a) => (a.tags || []).includes(state.activeTag));
  if (state.activeAuthor)
    list = list.filter((a) => field(a, "author") === state.activeAuthor);
  if (state.searchQuery) {
    const q = state.searchQuery.toLowerCase();
    list = list.filter((a) => {
      const t  = (field(a, "title")   || "").toLowerCase();
      const s  = (field(a, "summary") || "").toLowerCase();
      const tg = (a.tags || []).join(" ").toLowerCase();
      return t.includes(q) || s.includes(q) || tg.includes(q);
    });
  }
  state.filtered = list;
  renderSidebar();
  renderList();
}

// ── Detail ────────────────────────────────────────────────────────────────
async function openArticle(id) {
  const a = state.articles.find((x) => x.id === id);
  if (!a) return;
  state.currentArticle = a;
  const langs = Object.keys(a.languages || {});
  const lang  = langs.includes(state.lang) ? state.lang : langs[0];
  showDetail();
  await loadLang(a, lang);
}

async function loadLang(a, lang) {
  const ld = a.languages[lang];
  if (!ld) return;

  // lang buttons
  document.getElementById("detail-langs").innerHTML =
    Object.keys(a.languages).map((l) =>
      `<button class="txt-btn${l===lang?" on":""}" onclick="switchLang('${l}')">${l}</button>`
    ).join("");

  // header
  document.getElementById("art-header").innerHTML =
    `<div class="article-h1">${h(ld.title || a.title || a.id)}</div>` +
    `<div class="article-byline">${h(a.date || "")}  //  ${h(ld.author || a.author || "")}</div>`;

  // body
  const body = document.getElementById("art-body");
  body.innerHTML = "<div class='msg'>loading...</div>";
  try {
    const base = document.querySelector("base")?.href || "./";
    const res = await fetch(base + ld.path);
    if (!res.ok) throw new Error("HTTP " + res.status);
    let txt = await res.text();
    txt = txt.replace(/^---[\s\S]*?---\s*/, "");
    body.innerHTML = marked.parse(txt);
    document.getElementById("detail-view").scrollTop = 0;
  } catch (e) {
    body.innerHTML = "<div class='msg'>[!] " + e.message + "</div>";
  }
}

function switchLang(l) {
  if (state.currentArticle) loadLang(state.currentArticle, l);
}

// ── View switching ────────────────────────────────────────────────────────
function showDetail() {
  document.getElementById("list-view").style.display   = "none";
  document.getElementById("detail-view").style.display = "flex";
}

function showList() {
  document.getElementById("list-view").style.display   = "flex";
  document.getElementById("detail-view").style.display = "none";
  state.currentArticle = null;
}

// ── Language ──────────────────────────────────────────────────────────────
function setLang(l) {
  state.lang = l;
  document.querySelectorAll("#lang-sw .txt-btn, #sidebar-controls .txt-btn[data-lang]").forEach((b) =>
    b.classList.toggle("on", b.dataset.lang === l)
  );
  renderSidebar();
  renderList();
}

// ── Theme ─────────────────────────────────────────────────────────────────
function setTheme(t, save = true) {
  state.theme = t;
  document.documentElement.setAttribute("data-theme", t);
  const label = t === "dark" ? "[light]" : "[dark]";
  const btn   = document.getElementById("theme-btn");
  const sbBtn = document.getElementById("sb-theme-btn");
  if (btn)   btn.textContent   = label;
  if (sbBtn) sbBtn.textContent = label;
  const gfmTheme = document.getElementById("gfm-theme");
  if (gfmTheme) {
    gfmTheme.href = t === "dark"
      ? "https://cdn.jsdelivr.net/npm/github-markdown-css@5/github-markdown-dark.min.css"
      : "https://cdn.jsdelivr.net/npm/github-markdown-css@5/github-markdown-light.min.css";
  }
  const hlTheme = document.getElementById("hljs-theme");
  if (hlTheme) {
    hlTheme.href = t === "dark"
      ? "https://cdn.jsdelivr.net/npm/highlight.js@11/styles/github-dark.min.css"
      : "https://cdn.jsdelivr.net/npm/highlight.js@11/styles/github.min.css";
  }
  if (save) localStorage.setItem("kb-theme", t);
}

function toggleTheme() { setTheme(state.theme === "dark" ? "light" : "dark"); }

// ── Mobile sidebar ────────────────────────────────────────────────────────
function toggleSidebar() {
  document.getElementById("sidebar").classList.toggle("open");
  document.getElementById("sidebar-overlay").classList.toggle("open");
}

// ── Helpers ───────────────────────────────────────────────────────────────
function field(a, f) {
  const langs = a.languages || {};
  for (const l of [state.lang, "vi", "en"]) {
    if (langs[l] && langs[l][f]) return langs[l][f];
  }
  return a[f] || null;
}

function h(s) {
  return String(s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;").replace(/'/g,"&#39;");
}

function esc(s) { return String(s).replace(/'/g,"\\'"); }

// ── Init ──────────────────────────────────────────────────────────────────
boot();
