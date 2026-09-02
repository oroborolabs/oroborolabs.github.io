"""Gera sitemap.xml com <lastmod> real (mtime do arquivo — nunca data de execucao).

E-021 (forja j60): o sitemap vivia sem NENHUM lastmod (grep 02/09) enquanto o
IndexNow pingava 200 desde 29/08 e a ingestao do Bing media 0 (E-016/j56).
Regras:
  - lastmod = mtime do arquivo correspondente, no dia (W3C YYYY-MM-DD);
  - o conjunto de URLs e o mesmo servido antes (chave = caminho relativo);
  - backups (*.bak-*) e o gerador nunca entram;
  - saida idempotente: rodar 2x sem mudanca de mtime = byte a byte igual.
Uso: python gerar-sitemap.py [--check]   # --check so compara, exit 2 se diverge
"""
import sys, datetime, pathlib, subprocess

RAIZ = pathlib.Path(__file__).parent
BASE = "https://oroborolabs.github.io/"

# prioridade/changefreq por regra de caminho (mesmo esquema do sitemap anterior)
def regra(rel: str):
    if rel == "index.html":
        return "1.0", "weekly"
    if rel in ("series-field-notes.html", "pt/index.html", "start-here.html"):
        return "0.9", "weekly"
    if rel in ("workshop.html", "price-display-calculator.html", "digest.html"):
        return "0.8" if rel != "digest.html" else "0.7", "monthly"
    return "0.8", "monthly"  # posts/*

def urls():
    ents = []
    for p in sorted(RAIZ.rglob("*.html")):
        rel = p.relative_to(RAIZ).as_posix()
        if any(seg.startswith(".bak") or ".bak-" in p.name for seg in rel.split("/")):
            continue
        if rel == "gerar-sitemap.html":
            continue
        path = {"index.html": "", "pt/index.html": "pt/"}.get(rel, rel)
        loc = BASE + path
        pri, freq = regra(rel)
        mtime = datetime.date.fromtimestamp(p.stat().st_mtime).isoformat()
        ents.append((loc, mtime, freq, pri))
    return ents

def render(ents):
    linhas = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, mtime, freq, pri in ents:
        linhas.append(f'  <url><loc>{loc}</loc><lastmod>{mtime}</lastmod>'
                      f'<changefreq>{freq}</changefreq><priority>{pri}</priority></url>')
    linhas.append("</urlset>")
    return "\n".join(linhas) + "\n"

if __name__ == "__main__":
    novo = render(urls())
    alvo = RAIZ / "sitemap.xml"
    velho = alvo.read_text(encoding="utf-8") if alvo.exists() else ""
    if "--check" in sys.argv:
        if novo != velho:
            print("DIVERGE do disco", file=sys.stderr)
            sys.exit(2)
        print(f"OK: sitemap em sync, {novo.count('<loc>')} URLs")
        sys.exit(0)
    alvo.write_text(novo, encoding="utf-8")
    print(f"sitemap.xml gravado: {novo.count('<loc>')} URLs, "
          f"{novo.count('<lastmod>')} lastmod")
