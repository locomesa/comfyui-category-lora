import { app } from "/scripts/app.js";
import { loadPresets, presetNotice } from "./lora_loader/preset_store.mjs?v=presets1";

app.registerExtension({
  name:"Codex.CategoryLoRA.Presets",
  async setup() {
    try { await loadPresets(); }
    catch(error) { presetNotice(error.message,true); }
  },
});
