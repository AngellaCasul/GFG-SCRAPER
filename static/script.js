let selectedTopics = new Set();
let scrapedData = null;

// ── LOAD TOPICS AS CHECKBOXES ─────────────────────────────
async function loadTopics() {
  const res  = await fetch("/api/topics");
  const data = await res.json();

  const grid = document.getElementById("topics-grid");
  grid.innerHTML = data.topics.map(topic => `
    <div class="topic-checkbox" id="chk-${sanitize(topic)}" onclick="toggleTopic('${topic}')">
      <div class="custom-check" id="check-${sanitize(topic)}"></div>
      <span class="topic-name">${topic}</span>
    </div>
  `).join("");
}

function sanitize(str) {
  return str.replace(/\s+/g, "_").replace(/[^a-zA-Z0-9_]/g, "_");
}

// ── TOGGLE TOPIC SELECTION ────────────────────────────────
function toggleTopic(topic) {
  const id  = sanitize(topic);
  const box = document.getElementById("chk-" + id);
  const chk = document.getElementById("check-" + id);

  if (!box || !chk) return;

  if (selectedTopics.has(topic)) {
    selectedTopics.delete(topic);
    box.classList.remove("checked");
    chk.textContent = "";
  } else {
    selectedTopics.add(topic);
    box.classList.add("checked");
    chk.textContent = "✓";
  }

  const count = selectedTopics.size;
  document.getElementById("nav-badge").textContent = `${count} topic${count !== 1 ? "s" : ""} selected`;
  document.getElementById("btn-scrape").disabled = count === 0;
}

function selectAll() {
  document.querySelectorAll(".topic-checkbox").forEach(div => {
    const topic = div.querySelector(".topic-name").textContent;
    if (!selectedTopics.has(topic)) toggleTopic(topic);
  });
}

function selectNone() {
  [...selectedTopics].forEach(topic => toggleTopic(topic));
}

// ── HELPERS ───────────────────────────────────────────────
function diffClass(d) {
  return { Easy: "diff-easy", Basic: "diff-easy", Medium: "diff-medium", Hard: "diff-hard" }[d] || "diff-na";
}

function esc(s) {
  if (!s) return "";
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function trim(s, n = 300) {
  if (!s || s === "Not Available") return "Not Available";
  return s.length > n ? s.slice(0, n) + "…" : s;
}

function showToast(msg, type = "success") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast " + type + " show";
  setTimeout(() => t.className = "toast", 3000);
}

// ── UPDATE STATS ──────────────────────────────────────────
function updateStats(results) {
  const topics   = Object.keys(results);
  const articles = topics.reduce((sum, t) => sum + results[t].length, 0);
  const allArts  = topics.flatMap(t => results[t]);
  const easy     = allArts.filter(a => ["Easy","Basic"].includes(a.difficulty)).length;
  const hard     = allArts.filter(a => ["Medium","Hard","Expert"].includes(a.difficulty)).length;

  document.getElementById("stat-topics").textContent   = topics.length;
  document.getElementById("stat-articles").textContent = articles;
  document.getElementById("stat-easy").textContent     = easy;
  document.getElementById("stat-hard").textContent     = hard;
  document.getElementById("stats-row").style.display   = "grid";
}

// ── SORT BY DIFFICULTY ────────────────────────────────────
function sortByDifficulty(articles) {
  const order = { "Easy": 1, "Basic": 1, "Medium": 2, "Hard": 3, "Expert": 4, "Not Available": 5 };
  return [...articles].sort((a, b) => {
    const da = order[a.difficulty] || 5;
    const db = order[b.difficulty] || 5;
    return da - db;
  });
}

// ── RENDER ARTICLES ───────────────────────────────────────
function renderArticles(results) {
  scrapedData = results;
  updateStats(results);

  document.getElementById("btn-pdf").disabled = false;
  document.getElementById("articles-label").style.display = "block";

  const container = document.getElementById("articles-container");

  if (!Object.keys(results).length) {
    container.innerHTML = `<div id="empty-state"><div class="emoji">📭</div><p>No articles found.</p></div>`;
    return;
  }

  container.innerHTML = Object.entries(results).map(([topic, articles]) => `
    <div class="topic-section">
      <div class="topic-section-title">
        📂 ${esc(topic)}
        <span style="font-size:0.75rem; color:var(--text-muted); font-weight:400">${articles.length} articles</span>
      </div>
      ${sortByDifficulty(articles).map((a, i) => buildArticleCard(a, i, topic)).join("")}
    </div>
  `).join("");
}

function buildArticleCard(a, i, topic) {
  const id = sanitize(topic) + "-" + i;
  return `
    <div class="article-card" id="card-${id}" onclick="toggleCard('${id}')">
      <div class="art-header">
        <div class="art-num">${String(i+1).padStart(2,"0")}</div>
        <div class="art-title">${esc(a.title)}</div>
        <span class="diff-badge ${diffClass(a.difficulty)}">${esc(a.difficulty)}</span>
        <span class="chevron">▼</span>
      </div>
      <div class="art-body" id="body-${id}">

        <div class="art-section">
          <div class="art-section-title">Key Technical Concepts</div>
          <div class="art-text">${esc(trim(a.concepts, 400))}</div>
        </div>

        <div class="art-section">
          <div class="art-section-title">Code Snippets</div>
          ${buildCode(a)}
        </div>

        <div class="art-section">
          <div class="art-section-title">Complexity Analysis</div>
          ${buildComplexity(a)}
        </div>

        <div class="art-section">
          <div class="art-section-title">References / Related Links</div>
          ${buildLinks(a)}
        </div>

        <div style="font-size:0.75rem; color:var(--text-muted); margin-top:8px; font-family:'JetBrains Mono',monospace;">
          🔗 ${esc(a.url)}
        </div>
      </div>
    </div>
  `;
}

function buildCode(a) {
  const snips = (a.code_snippets || []).filter(s => s && s !== "Not Available");
  if (!snips.length) return `<div class="art-text">Not Available</div>`;
  return `<pre class="art-code">${esc(snips[0].slice(0, 500))}</pre>`;
}

function buildComplexity(a) {
  const cx = (a.complexity || []).filter(c => c && c !== "Not Available");
  if (!cx.length) return `<div class="art-text">Not Available</div>`;
  return cx.slice(0, 3).map(c => `<div class="art-text">• ${esc(trim(c, 180))}</div>`).join("");
}

function buildLinks(a) {
  const links = (a.related_links || []).filter(l => l.title && l.title !== "Not Available");
  if (!links.length) return `<div class="art-text">Not Available</div>`;
  return links.slice(0, 4).map(l =>
    `<a class="art-link" href="${esc(l.url)}" target="_blank" onclick="event.stopPropagation()">→ ${esc(trim(l.title, 70))}</a>`
  ).join("");
}

function toggleCard(id) {
  document.getElementById("card-" + id).classList.toggle("open");
  document.getElementById("body-" + id).classList.toggle("open");
}

// ── LOAD SAVED DATA ───────────────────────────────────────
async function loadData() {
  try {
    const res  = await fetch("/api/data");
    const data = await res.json();
    if (data.results && Object.keys(data.results).length) {
      renderArticles(data.results);
      showToast(`Loaded saved data ✓`);
    } else {
      showToast("No saved data found. Scrape first!", "error");
    }
  } catch(e) {
    showToast("Failed to load data.", "error");
  }
}

// ── CLEAR DATA ────────────────────────────────────────────
function clearData() {
  scrapedData = null;

  document.getElementById("articles-container").innerHTML = `
    <div id="empty-state">
      <div class="emoji">📚</div>
      <p>No data yet.<br>Select topics above and click <strong>Scrape Selected</strong>,<br>or click <strong>Load Saved Data</strong> if you've scraped before.</p>
    </div>
  `;

  document.getElementById("articles-label").style.display = "none";
  document.getElementById("stats-row").style.display      = "none";
  document.getElementById("btn-pdf").disabled             = true;

  showToast("Cleared! Data still saved on disk.");
}

// ── START SCRAPER ─────────────────────────────────────────
async function startScrape() {
  if (selectedTopics.size === 0) {
    showToast("Please select at least one topic!", "error");
    return;
  }

  document.getElementById("btn-scrape").disabled    = true;
  document.getElementById("progress-box").style.display = "block";
  document.getElementById("progress-log").innerHTML = "";
  document.getElementById("progress-bar").style.width = "0%";

  const res = await fetch("/api/scrape", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topics: [...selectedTopics] })
  });

  if (!res.ok) {
    showToast("Scraper is already running!", "error");
    document.getElementById("btn-scrape").disabled = false;
    return;
  }

  const es    = new EventSource("/api/progress");
  let msgCount = 0;

  es.onmessage = async (e) => {
    if (e.data === "ping") return;

    if (e.data === "__DONE__") {
      es.close();
      document.getElementById("progress-bar").style.width  = "100%";
      document.getElementById("btn-scrape").disabled = false;
      showToast("Scraping complete! ✓");
      await loadData();
      return;
    }

    // Progress bar
    msgCount++;
    const pct = Math.min(95, msgCount * 3);
    document.getElementById("progress-bar").style.width = pct + "%";

    // Log line
    const log  = document.getElementById("progress-log");
    const line = document.createElement("div");
    const isTopic = e.data.startsWith("Finding");
    const isDone  = e.data.startsWith("Done");
    line.className = "log-line" + (isDone ? " done" : isTopic ? " topic" : "");
    line.textContent = "› " + e.data;
    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
  };

  es.onerror = () => {
    es.close();
    document.getElementById("btn-scrape").disabled = false;
    showToast("Connection error.", "error");
  };
}

// ── GENERATE PDF ──────────────────────────────────────────
async function generatePDF() {
  if (!scrapedData) { showToast("No data to export.", "error"); return; }

  const name   = document.getElementById("student-name").value.trim() || "Anonymous";
  const topics = Object.keys(scrapedData);
  const btn    = document.getElementById("btn-pdf");
  btn.disabled    = true;
  btn.textContent = "⏳ Generating…";

  try {
    const res = await fetch("/api/generate-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_name: name, topics: topics })
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(err.error || "PDF error", "error");
      return;
    }

    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url; a.download = "GFG_Learning_Module.pdf"; a.click();
    URL.revokeObjectURL(url);
    showToast("PDF downloaded! ✓");

  } catch(e) {
    showToast("Failed to generate PDF.", "error");
  } finally {
    btn.disabled    = false;
    btn.textContent = "⬇ Download PDF";
  }
}

// ── AUTO-LOAD ON PAGE OPEN ────────────────────────────────
(async () => {
  await loadTopics();
  const status = await fetch("/api/status").then(r => r.json()).catch(() => ({ has_data: false }));
  if (status.has_data) await loadData();
})();