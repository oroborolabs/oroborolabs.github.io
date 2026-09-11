"use strict";
const fields = {fornecedor:"Fornecedor", sku:"Código do item", preco:"Preço", moeda:"Moeda", unidade:"Unidade", vigencia:"Vigência"};
let latest = null;
function invalidate(){ latest=null; document.querySelector("#result").hidden=true; document.querySelector("#output").value=""; document.querySelector("#copy-status").textContent=""; }
function draw(){
 const box=document.querySelector("#files");box.replaceChildren(); invalidate();
 for(let i=0;i<Number(document.querySelector("#count").value);i++){
  const set=document.createElement("fieldset");const legend=document.createElement("legend");legend.textContent="Arquivo "+(i+1);set.append(legend);
  function input(label,key,type="text") {const l=document.createElement("label");l.textContent=label;const el=document.createElement("input");el.name=key;el.type=type;el.required=true;if(type==="text")el.maxLength=120;l.append(el);set.append(l);return el;}
  input("Nome do arquivo CSV (sem pastas)","caminho");const n=input("Registros, sem contar o cabeçalho","linhas","number");n.min="1";n.max="1000";n.step="1";
  function select(label,key,values){const l=document.createElement("label");l.textContent=label+" ";const el=document.createElement("select");el.name=key;for(const [v,t] of values){const o=document.createElement("option");o.value=v;o.textContent=t;el.append(o);}l.append(el);set.append(l);}
  select("Separador de campos","delimiter",[[";","Ponto e vírgula"],[",","Vírgula"],["\t","Tabulação"],["|","Barra vertical"]]);
  select("Separador decimal","decimal_separator",[[",","Vírgula"],[".","Ponto"]]);
  input("Unidades permitidas, separadas por vírgula (ex.: UN, CX)","unidades");
  for(const [key,label] of Object.entries(fields))input("Nome exato da coluna: "+label,key);
  box.append(set);
 }
}
function collect(){
 const arquivos=[], names=new Set();let total=0;
 for(const set of document.querySelectorAll("fieldset")){
  const v=k=>set.querySelector('[name="'+k+'"]').value;
  const name=v("caminho"); if(!/^[^\\/:*?"<>|]+\.csv$/i.test(name)||name.includes("..")||name.trim()!==name)throw Error("Informe nomes CSV sem pastas ou caracteres reservados.");
  if(names.has(name.toLowerCase()))throw Error("Os arquivos precisam ter nomes diferentes.");names.add(name.toLowerCase());
  const n=Number(v("linhas"));if(!Number.isInteger(n)||n<1)throw Error("Informe registros inteiros positivos.");total+=n;
  const mapeamento={};for(const key of Object.keys(fields)){const value=v(key);if(!value.trim())throw Error("Preencha cada coluna.");mapeamento[key]=value;}
  if(new Set(Object.values(mapeamento)).size!==6)throw Error("As seis colunas devem ser distintas em cada arquivo.");
  const unidades_permitidas=v("unidades").split(",").map(x=>x.trim()).filter(Boolean);if(!unidades_permitidas.length)throw Error("Declare as unidades permitidas.");
  arquivos.push({caminho:name,decimal_separator:v("decimal_separator"),delimiter:v("delimiter"),unidades_permitidas,mapeamento});
 }
 if(arquivos.length<1||arquivos.length>6||total>1000)throw Error("O escopo informado excede seis arquivos ou mil registros. Contate o suporte para avaliação.");
 return {manifesto:{versao:1,arquivos},total};
}
document.querySelector("#count").addEventListener("change",draw);
document.querySelector("#scope").addEventListener("input",invalidate);
document.querySelector("#scope").addEventListener("submit",e=>{e.preventDefault();invalidate();document.querySelector("#error").textContent="";try{
 const data=collect();latest=data.manifesto;
 document.querySelector("#output").value="Solicito proposta de consolidação CSV.\nPreço experimental anunciado: R$750, sujeito à conferência do escopo.\nRegistros declarados: "+data.total+". Os arquivos ainda não foram conferidos.\nSolicito confirmação de viabilidade, prazo e condições antes da contratação.\n\nLayout declarado:\n"+JSON.stringify(latest,null,2);
 document.querySelector("#result").hidden=false;
}catch(err){document.querySelector("#error").textContent=err.message;}});
document.querySelector("#download").addEventListener("click",()=>{if(!latest)return;const url=URL.createObjectURL(new Blob([JSON.stringify(latest,null,2)],{type:"application/json"}));const a=document.createElement("a");a.href=url;a.download="layout-declarado.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
document.querySelector("#copy").addEventListener("click",async()=>{
 if(!latest)return;
 const output=document.querySelector("#output"), status=document.querySelector("#copy-status");
 const text=output.value;
 try {
  await navigator.clipboard.writeText(text);
  if(latest && output.value===text)status.textContent="Solicitação copiada. Cole no seu e-mail para revisar e enviar.";
 } catch {
  if(!latest || output.value!==text)return;
  output.focus();output.select();
  status.textContent="Texto selecionado. Use a opção Copiar do seu dispositivo.";
 }
});
draw();
