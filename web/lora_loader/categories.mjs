import { readState, writeState } from "./core.mjs?v=presets1";

export function rootGraph(graph) {
  const seen = new Set();
  while (graph?._subgraph_node?.graph && !seen.has(graph)) {
    seen.add(graph); graph = graph._subgraph_node.graph;
  }
  return graph;
}

export function allNodes(graph) {
  const result = [], seen = new Set();
  function visit(g) {
    if (!g || seen.has(g)) return;
    seen.add(g);
    for (const n of g._nodes || []) {
      result.push(n);
      if (n.subgraph) visit(n.subgraph);
    }
  }
  visit(rootGraph(graph)); return result;
}

export function controllers(graph) {
  return allNodes(graph).filter(n => n.comfyClass === "LoraCategoryControls" || n.type === "LoraCategoryControls");
}

export function readControls(node) {
  const value = node.widgets?.find(w => w.name === "category_state")?.value;
  try { return JSON.parse(value || "{}").categories || {}; } catch { return {}; }
}

export function notify(graph) {
  graph?.change?.();
  window.dispatchEvent(new CustomEvent("category-lora-change", { detail: rootGraph(graph) }));
}

export function saveControls(node, categories) {
  node.widgets.find(w => w.name === "category_state").value = JSON.stringify({ version: 1, categories });
  node.setDirtyCanvas?.(true, true); notify(node.graph);
}

export function categoryNames(graph) {
  const names = new Map();
  for (const n of controllers(graph)) for (const name of Object.keys(readControls(n))) names.set(name.toLowerCase(), name);
  for (const n of allNodes(graph)) {
    if (n.comfyClass !== "CategoryLoraLoader" && n.type !== "CategoryLoraLoader") continue;
    for (const row of readState(n).loras) for (const name of row.categories) if (!names.has(name.toLowerCase())) names.set(name.toLowerCase(), name);
  }
  return [...names.values()].sort((a,b) => a.localeCompare(b));
}

export function rowBlocked(node, row) {
  const control = controllers(node.graph)[0];
  const policy = Object.fromEntries(Object.entries(control ? readControls(control) : {}).map(([k,v]) => [k.toLowerCase(), v]));
  return row.categories?.some(c => policy[c.toLowerCase()] === false);
}

export function openCategoryEditor(node, id, refresh) {
  document.querySelector(".category-lora-editor")?.remove();
  const state = readState(node), row = state.loras.find(r => r.id === id);
  if (!row) return;
  const selected = new Set(row.categories.map(c => c.toLowerCase()));
  const names = categoryNames(node.graph);
  const overlay = document.createElement("div"); overlay.className = "category-lora-editor";
  overlay.style.cssText = "position:fixed;inset:0;background:#0009;z-index:100000;display:grid;place-items:center";
  const panel = document.createElement("div");
  panel.style.cssText = "background:#20282d;color:#eee;padding:22px;border:1px solid #58818a;border-radius:12px;width:380px;max-height:80vh;overflow:auto;font:14px system-ui;box-shadow:0 12px 60px #000";
  const heading = document.createElement("h3"); heading.textContent = "Assign categories";
  const hint = document.createElement("p"); hint.textContent = "Any category switched off blocks this row and its trigger words.";
  const file = document.createElement("p"); file.textContent = row.name.split(/[\\/]/).pop(); file.style.overflowWrap = "anywhere";
  const list = document.createElement("div");
  function addChoice(name) {
    const label = document.createElement("label"); label.style.cssText = "display:flex;gap:10px;padding:7px";
    const check = document.createElement("input"); check.type = "checkbox"; check.checked = selected.has(name.toLowerCase());
    check.onchange = () => check.checked ? selected.add(name.toLowerCase()) : selected.delete(name.toLowerCase());
    label.append(check, document.createTextNode(name)); list.append(label);
  }
  names.forEach(addChoice);
  const input = document.createElement("input"); input.placeholder = "New category name"; input.setAttribute("aria-label", "New category name");
  input.style.cssText = "padding:8px;margin:10px 6px 10px 0;background:#111b20;color:#fff;border:1px solid #56717b;border-radius:5px";
  const add = document.createElement("button"); add.textContent = "Add";
  add.onclick = () => {
    const value = input.value.trim(); if (!value) return;
    if (!names.some(n => n.toLowerCase() === value.toLowerCase())) { names.push(value); selected.add(value.toLowerCase()); addChoice(value); }
    input.value = "";
  };
  const save = document.createElement("button"); save.textContent = "Save categories";
  save.style.cssText = "display:block;margin-top:12px;padding:9px;background:#387b83;color:white;border:0;border-radius:5px;width:100%;cursor:pointer";
  save.onclick = () => {
    row.categories = names.filter(n => selected.has(n.toLowerCase())); writeState(node, state);
    const control = controllers(node.graph)[0];
    if (control) {
      const categories = readControls(control);
      for (const name of row.categories) if (!Object.keys(categories).some(k => k.toLowerCase() === name.toLowerCase())) categories[name] = true;
      saveControls(control, categories);
    }
    refresh(); notify(node.graph); overlay.remove();
  };
  const cancel = document.createElement("button"); cancel.textContent = "Cancel"; cancel.onclick = () => overlay.remove(); cancel.style.marginTop = "8px";
  panel.append(heading, file, hint, list, input, add, save, cancel); overlay.append(panel);
  overlay.onclick = e => { if (e.target === overlay) overlay.remove(); }; document.body.append(overlay); input.focus();
}
