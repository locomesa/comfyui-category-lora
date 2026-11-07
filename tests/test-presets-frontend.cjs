const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const assert = require('node:assert/strict');
const base = path.resolve(__dirname, '../web/lora_loader');
const data = {'krea2/model.safetensors':{name:'Krea2/Model.safetensors',sm:.7,sc:.3,categories:['Eyes','Style'],triggers:['picked'],custom:['typed']}};
const context = vm.createContext({console,crypto:global.crypto,structuredClone,setTimeout,clearTimeout});
const modules = new Map();
async function load(file) {
  if (modules.has(file)) return modules.get(file);
  let mod;
  if (file==='/scripts/app.js') mod = new vm.SyntheticModule(['app'],function(){this.setExport('app',{ui:{settings:{getSettingValue:()=>null}}});},{context,identifier:file});
  else if (file==='/scripts/api.js') mod = new vm.SyntheticModule(['api'],function(){this.setExport('api',{fetchApi:async(url,options)=>{
    if (options?.method==='POST') {const body=JSON.parse(options.body),key=body.name.replace(/\\/g,'/').toLowerCase();data[key]={name:body.name,...body.preset};return {ok:true,json:async()=>structuredClone({key,preset:data[key]})};}
    return {ok:true,json:async()=>structuredClone({presets:data})};
  }});},{context,identifier:file});
  else mod = new vm.SourceTextModule(fs.readFileSync(file,'utf8'),{context,identifier:file});
  modules.set(file,mod);
  await mod.link((specifier,parent)=>load(specifier.startsWith('/scripts/')?specifier:path.resolve(path.dirname(parent.identifier),specifier.split('?')[0])));
  return mod;
}
(async()=>{
  const mod=await load(path.join(base,'core.mjs'));await mod.evaluate();const core=mod.namespace;
  const store=modules.get(path.join(base,'preset_store.mjs')).namespace;await store.loadPresets();
  const node={properties:{}};
  core.addLora(node,'Krea2\\MODEL.safetensors');let state=core.readState(node),row=state.loras[0];
  assert.equal(row.sm,.7);assert.equal(row.sc,.3);assert.equal(state.linkStrength,false);assert.equal(row.on,true);
  assert.deepEqual([...row.categories],['Eyes','Style']);assert.deepEqual([...row.triggers],['picked']);assert.deepEqual([...row.custom],['typed']);
  const id=row.id;row.categories.push('Skin');row.sm=.9;core.writeState(node,state);
  assert.deepEqual([...store.findPreset(row.name).categories],['Eyes','Style']);
  await store.saveRowPreset(row);core.removeLora(node,id);core.addLora(node,row.name);state=core.readState(node);row=state.loras[0];
  assert.equal(row.sm,.9);assert.equal(row.sc,.3);assert.notEqual(row.id,id);assert.deepEqual([...row.categories],['Eyes','Style','Skin']);
  core.patchLora(node,row.id,{name:'no-preset.safetensors'});row=core.readState(node).loras[0];
  assert.equal(row.categories.length,0);assert.equal(row.triggers.length,0);assert.equal(row.custom.length,0);
  core.patchLora(node,row.id,{name:'Krea2/Model.safetensors'});row=core.readState(node).loras[0];assert.equal(row.sm,.9);assert.equal(row.categories.length,3);
  console.log('PASS automatic restore, independent rows, remove/re-add, separate strengths, replacement and no-preset reset');
})().catch(error=>{console.error(error);process.exitCode=1;});
