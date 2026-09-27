const input = document.getElementById("input");
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");
const emptyEl = document.getElementById("empty");
const badgeEl = document.getElementById("badge");
const noteEl = document.getElementById("note");
const saveBtn = document.getElementById("save");

let lastMarkdown = "";
let lastTopic = "";

input.addEventListener("keydown", async (e) => {
  if (e.key !== "Enter") return;
  const text = input.value.trim();
  if (!text) return;
  await run(text);
});

saveBtn.addEventListener("click", async () => {
  saveBtn.disabled = true;
  saveBtn.textContent = "Saving…";
  try {
    const res = await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ markdown: lastMarkdown, topic: lastTopic }),
    });
    const data = await res.json();
    saveBtn.textContent = "Saved";
    statusEl.hidden = false;
    statusEl.textContent = `Saved to ${data.saved_path}`;
  } catch (err) {
    saveBtn.textContent = "Save failed";
  } finally {
    setTimeout(() => { saveBtn.disabled = false; saveBtn.textContent = "Save to vault"; }, 2200);
  }
});

async function run(text) {
  emptyEl.hidden = true;
  resultEl.hidden = true;
  statusEl.hidden = false;
  statusEl.textContent = "Searching PubMed…";

  try {
    const res = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();

    lastMarkdown = data.markdown;
    lastTopic = data.topic;
    badgeEl.textContent = data.note_type;
    noteEl.innerHTML = renderNote(data.markdown);

    statusEl.hidden = true;
    resultEl.hidden = false;
  } catch (err) {
    statusEl.textContent = "Something went wrong reaching PubMed or the local model.";
  }
}

/**
 * Renders exactly the markdown shape produced by app/export/markdown.py.
 * This is intentionally NOT a general markdown parser -- the backend's
 * output is a controlled, known template, so a small tuned parser is
 * more predictable than pulling in a generic markdown library.
 */
function renderNote(markdown) {
  const lines = markdown.split("\n");
  let html = "";
  let i = 0;
  let relationContext = "support";

  // skip YAML frontmatter
  if (lines[0] === "---") {
    i = 1;
    while (i < lines.length && lines[i] !== "---") i++;
    i++;
  }

  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  for (; i < lines.length; i++) {
    const line = lines[i];

    if (line.startsWith("# ")) { html += `<h1>${esc(line.slice(2))}</h1>`; continue; }
    if (line.startsWith("## ")) {
      const text = line.slice(3);
      relationContext = /contradict|against/i.test(text) ? "contradict" : "support";
      html += `<h2>${esc(text)}</h2>`;
      continue;
    }
    if (line.startsWith("### ")) {
      relationContext = "contradict";
      html += `<h3>${esc(line.slice(4))}</h3>`;
      continue;
    }
    if (line.trim() === "---") { html += `<hr class="divider" />`; continue; }
    if (/^\*.*\*$/.test(line.trim()) && line.trim().length > 2) {
      html += `<p class="insufficient">${esc(line.trim().slice(1, -1))}</p>`;
      continue;
    }
    if (line.startsWith("> ")) {
      const sentence = line.slice(2);
      const metaLines = [];
      let j = i + 1;
      while (j < lines.length && lines[j].trim() !== "" && !lines[j].startsWith(">")) {
        if (lines[j].startsWith("**")) metaLines.push(lines[j]);
        j++;
      }
      html += `<div class="evidence ${relationContext}"><p class="sentence">${esc(sentence)}</p>`;
      html += `<div class="meta">`;
      for (const m of metaLines) {
        const match = m.match(/\*\*(.+?):\*\*\s*(.+?)\s*$/);
        if (!match) continue;
        const [, label, value] = match;
        const cls = /pmid/i.test(label) ? "pmid" : /doi/i.test(label) ? "doi" : "";
        html += `${esc(label)}: <span class="${cls}">${esc(value.trim())}</span><br/>`;
      }
      html += `</div></div>`;
      i = j - 1;
      continue;
    }
    if (line.startsWith("- PMID:")) {
      html += `<div class="references">${esc(line.slice(2))}</div>`;
      continue;
    }
  }
  return html;
}
