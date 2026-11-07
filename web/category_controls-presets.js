import { app } from "/scripts/app.js";
import { allNodes, controllers, readControls, saveControls, categoryNames, rootGraph } from "./lora_loader/categories.mjs?v=presets1";
import { readState } from "./lora_loader/core.mjs?v=presets1";

app.registerExtension({
  name: "Codex.CategoryLoRA.Controls",
  nodeCreated(node) {
    if (node.comfyClass !== "LoraCategoryControls") return;
    const widget = node.widgets.find(w => w.name === "category_state");
    widget.type = "hidden"; widget.computeSize = () => [0, -4];
    if (widget.inputEl) widget.inputEl.style.display = "none";
    const root = document.createElement("div");
    root.style.cssText = "box-sizing:border-box;width:100%;padding:12px;background:#18262c;color:#e2edf0;border-radius:8px;font:12px system-ui";
    let height = 160;
    const dom = node.addDOMWidget("category_controls", "category_controls", root, { serialize:false, getMinHeight:()=>height, getMaxHeight:()=>height });
    dom.computeLayoutSize = () => ({ minHeight:height, minWidth:300 });
    function render() {
      const active = document.activeElement;
      if (root.contains(active) && active.tagName === "INPUT" && active.type === "text") return;
      root.replaceChildren();
      const categories = readControls(node), names = categoryNames(node.graph);
      const controlCount = controllers(node.graph).length;
      const header = document.createElement("p"); header.textContent = controlCount > 1 ? "Use only ONE Category Controls node in this workflow." : "Controls every Category LoRA Loader in this workflow.";
      header.style.cssText = "margin:0 0 10px;color:" + (controlCount > 1 ? "#ffa680" : "#a4c6cf"); root.append(header);
      const loaders = allNodes(node.graph).filter(n => n.comfyClass === "CategoryLoraLoader" || n.type === "CategoryLoraLoader");
      for (const name of names) {
        const key = Object.keys(categories).find(k => k.toLowerCase() === name.toLowerCase()) || name;
        const on = categories[key] !== false;
        const count = loaders.reduce((total,n) => total + readState(n).loras.filter(r => r.categories.some(c => c.toLowerCase() === name.toLowerCase())).length, 0);
        const label = document.createElement("label"); label.style.cssText = "display:flex;align-items:center;gap:9px;padding:7px 6px;border-bottom:1px solid #ffffff12;cursor:pointer";
        const check = document.createElement("input"); check.type = "checkbox"; check.checked = on; check.setAttribute("role", "switch"); check.setAttribute("aria-label", name); check.style.accentColor = "#57b7a8";
        check.onchange = () => { categories[key] = check.checked; saveControls(node,categories); render(); };
        const title = document.createElement("span"); title.textContent = name; title.style.flex = "1";
        const badge = document.createElement("span"); badge.textContent = `${on ? "ON" : "OFF"} · ${count}`; badge.style.color = on ? "#8fdfc9" : "#ffb29a";
        label.append(check,title,badge); root.append(label);
      }
      const input = document.createElement("input"); input.type = "text"; input.placeholder = "New category"; input.setAttribute("aria-label", "New category");
      input.style.cssText = "width:65%;box-sizing:border-box;padding:7px;background:#0f1b21;color:white;border:1px solid #47636b;border-radius:4px;margin:10px 6px 0 0";
      const add = document.createElement("button"); add.textContent = "Add"; add.style.cssText = "padding:7px;background:#355b64;color:white;border:0;border-radius:4px;cursor:pointer";
      add.onclick = () => { const name=input.value.trim(); if (name && !names.some(n=>n.toLowerCase()===name.toLowerCase())) { categories[name]=true; input.blur(); saveControls(node,categories); render(); } };
      input.onkeydown = e => { if (e.key === "Enter") { e.preventDefault(); add.click(); } e.stopPropagation(); };
      root.append(input,add);
      const foot = document.createElement("p"); foot.textContent = `${loaders.length} loaders · Off excludes weights and triggers. Row switches stay unchanged.`; foot.style.cssText = "margin:10px 0 0;color:#a4b6bd;font-size:11px"; root.append(foot);
      height = 115 + names.length * 34;
      if (node.size[1] < height+70) node.setSize([Math.max(node.size[0],350),height+70]);
      node.setDirtyCanvas?.(true,true);
    }
    const onChange = ev => { if (ev.detail === rootGraph(node.graph)) render(); };
    window.addEventListener("category-lora-change",onChange);
    const configure=node.onConfigure; node.onConfigure=function() { const r=configure?.apply(this,arguments); queueMicrotask(render); return r; };
    const removed=node.onRemoved; node.onRemoved=function() { window.removeEventListener("category-lora-change",onChange); return removed?.apply(this,arguments); };
    const timer=setInterval(()=>{if(node.graph)render();},2000);
    const cleanup=node.onRemoved;node.onRemoved=function(){clearInterval(timer);return cleanup?.apply(this,arguments);};
    queueMicrotask(render);
  },
});
