"use strict";
document.querySelectorAll("form[data-front]").forEach((form) => {
 const pt=form.dataset.lang==="pt", result=form.parentElement.querySelector(".brief-result");
 const status=result.querySelector('[role="status"]'), output=result.querySelector(".brief-output"), link=result.querySelector(".email-link");
 form.addEventListener("submit", (event) => {
  event.preventDefault(); if(!form.reportValidity()) return;
  const data=new FormData(form), lines=[];
  for(const field of form.querySelectorAll("textarea[name]")) {
   const value=String(data.get(field.name)||"").trim();
   if(field.required&&!value){field.setCustomValidity(pt?"Preencha este campo.":"Fill in this field.");field.reportValidity();return;}
   lines.push(form.querySelector('label[for="'+field.id+'"]').textContent+": "+value);
  }
  const subject=(pt?"Tenho interesse":"Interested")+" [frente:"+form.dataset.front+"] "+String(data.get("project")).trim().replace(/[\r\n]+/g," ").slice(0,120);
  const body=(pt?"Solicito avaliação de escopo antes de qualquer cobrança. Ainda não há prazo ou contratação confirmados.":"Please assess scope before any charge. No deadline or engagement has been confirmed.")+"\n\n"+lines.join("\n\n");
  output.value=subject+"\n\n"+body;link.href="mailto:contato@oroborolabs.com?subject="+encodeURIComponent(subject)+"&body="+encodeURIComponent(body);
  status.textContent=pt?"Pedido preparado. Nada foi enviado. Abra o e-mail ou copie o texto para enviar.":"Enquiry prepared. Nothing was sent. Open email or copy the text to send it.";
  result.hidden=false;
 });
 form.querySelectorAll("textarea").forEach(field=>field.addEventListener("input",()=>field.setCustomValidity("")));
 result.querySelector(".copy-brief").addEventListener("click",async()=>{
  try{await navigator.clipboard.writeText(output.value);status.textContent=pt?"Texto copiado. Envie pelo seu e-mail.":"Text copied. Send it using your email.";}
  catch(_){output.focus();output.select();status.textContent=pt?"Selecione e copie o texto acima.":"Select and copy the text above.";}
 });
});