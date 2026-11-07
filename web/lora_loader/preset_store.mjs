import { api } from "/scripts/api.js";

let presets = Object.create(null);
let pending = null;
let loaded = false;

export function presetKey(name) { return String(name || "").replace(/\\/g, "/").trim().toLowerCase(); }

export async function loadPresets(force = false) {
  if (pending) return pending;
  if (loaded && !force) return presets;
  pending = (async () => {
    const response = await api.fetchApi("/category_lora/presets");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not read LoRA presets.");
    presets = Object.assign(Object.create(null), data.presets || {}); loaded = true; return presets;
  })();
  try { return await pending; } finally { pending = null; }
}

export function findPreset(name) { const key=presetKey(name); return Object.hasOwn(presets,key) ? presets[key] : null; }

export function restoredRow(name, row, nodeState) {
  const preset = findPreset(name);
  if (!preset) return row;
  // A new array for each row prevents edits from changing the library or peers.
  Object.assign(row, {
    sm:preset.sm, sc:preset.sc,
    categories:[...preset.categories], triggers:[...preset.triggers], custom:[...preset.custom],
  });
  if (row.sm !== row.sc) nodeState.linkStrength = false;
  return row;
}

export async function saveRowPreset(row) {
  const response = await api.fetchApi("/category_lora/presets", {
    method:"POST", headers:{"Content-Type":"application/json"},
    body:JSON.stringify({name:row.name,preset:{sm:row.sm,sc:row.sc,categories:row.categories || [],triggers:row.triggers || [],custom:row.custom || []}}),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Could not save this LoRA preset.");
  presets[data.key] = data.preset; loaded = true; return data.preset;
}

export function presetNotice(message, error = false) {
  document.querySelector(".category-lora-preset-notice")?.remove();
  const notice=document.createElement("div");notice.className="category-lora-preset-notice";
  notice.setAttribute("role",error ? "alert" : "status");notice.textContent=message;
  notice.style.cssText=`position:fixed;right:20px;top:140px;max-width:380px;padding:14px 18px;border:1px solid ${error ? "#bd6652" : "#589c88"};background:#202b30;color:#fff;border-radius:8px;font:13px system-ui;z-index:100100;box-shadow:0 8px 30px #0008`;
  notice.onclick=()=>notice.remove();document.body.append(notice);setTimeout(()=>notice.remove(),7000);
}
