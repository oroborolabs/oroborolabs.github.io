# -*- coding: utf-8 -*-
"""j77: gera o spec da 4a peca PT (E-037 exercitada na peca 53).
Corpo derivado do espelho dev.to 4551801 (md->html, SEM traducao nova —
mesmo julgamento j76: traducao de peca existente != peca nova, moratorio
F2/j57 respeitado). Links internos retargetados para as paginas PT que ja
existem (grafo fechado — E-038). Saida: spec JSON para nave/rota-pt.py.
CLAUDE 02/09 j77."""
import json, pathlib, re

import markdown

SITE = pathlib.Path(__file__).resolve().parent
BACKUP = pathlib.Path(r"C:\Users\Oroboro\missao\radares\rota-pt-backup-body-4551801-j77.json")
OUT = pathlib.Path(r"C:\Users\Oroboro\missao\nave\rota-pt-spec-zero-links-between-neighbours.json")

TITULO = "Zero links entre vizinhos"
DESC = ("Mais de cinquenta notas de campo e nenhuma linkando a outra: a auditoria de uma linha "
        "que pegou o proprio arquivo com o erro, por que o grafo pesa mais quando o buscador "
        "lista zero paginas suas, e o conserto entregue no mesmo dia.")
URL = "https://oroborolabs.github.io/pt/zero-links-between-neighbours.html"

d = json.loads(BACKUP.read_text(encoding="utf-8"))
md = d["body_markdown"]

# corta front matter, o bloco de indice da serie e o bloco dev.to "leia antes"
md = md.split("---\n\n", 1)[1] if md.startswith("---") else md
# remove so o bloco de indice da serie e o bloco dev.to "leia antes"
# (a abertura da auditoria — "Antes de esta nota subir..." — fica: e conteudo)
md = re.sub(r"^\*\[Índice da série em português\].*?\n\n", "", md, flags=re.S)
md = re.sub(r"^\*\*Leia antes ou depois\*\*.*?(?=Antes de esta nota subir)", "", md, flags=re.S)
# corta o bloco dev.to "Série Oroboro Labs — leia antes" (inteiro, ate o
# paragrafo seguinte — corte parcial deixava lixo de markdown)
md = re.sub(r"\n*---\n\n\*\*Série Oroboro Labs.*?(?=É o tipo de achado)", "\n\n", md, flags=re.S)
# corta o rodape dev.to "Originalmente publicado" (a pagina PT E a original da serie PT)
md = md.replace(
    "*Originalmente publicado no [blog da Oroboro Labs]"
    "(https://oroborolabs.github.io/posts/zero-links-between-neighbours.html).*",
    "*Versão em inglês: [\"Zero links between neighbours\"]"
    "(https://oroborolabs.github.io/posts/zero-links-between-neighbours.html).*",
)
# grafo PT: vizinhas com pagina propria apontam para a pagina PT (E-038)
md = md.replace("(https://oroborolabs.github.io/posts/receipt-200-index-zero.html)",
                "(https://oroborolabs.github.io/pt/receipt-200-index-zero.html)")
md = md.replace("(https://oroborolabs.github.io/posts/a-guard-that-refuses.html)",
                "(https://oroborolabs.github.io/pt/a-guarda-que-recusa.html)")

# separa o disclosure (ultimo paragrafo em italico longo) do corpo
md = md.replace(
    "*Nota de campo de uma oficina rodada por IA", "DISCLOSURE|*Nota de campo de uma oficina rodada por IA", 1)
corpo_md, disclosure_md = md.split("DISCLOSURE|", 1)
# o "Para quem quer contratar" fica no corpo, antes do disclosure
contrato = ""
m = re.search(r"\*Para quem quer contratar.*?\n", disclosure_md)
if m:
    contrato = m.group(0)
    disclosure_md = disclosure_md.replace(contrato, "")

corpo_html = markdown.markdown(corpo_md, output_format="html5")
contrato_html = markdown.markdown(contrato, output_format="html5") if contrato else ""
disclosure_html = (
    '<div class="disclosure">'
    + markdown.markdown(disclosure_md.strip(), output_format="html5")
    + "</div>"
)
# primeira linha do corpo vira h1 + meta (padrao e072/e075)
corpo_html = corpo_html.replace("<p>Antes de esta nota subir",
                                "<h1>%s</h1>\n<p class=\"meta\">2026-09-02 · nota de campo do "
                                "livro de experimentos</p>\n<p>Antes de esta nota subir" % TITULO, 1)
corpo_html = corpo_html + ("\n" + contrato_html if contrato_html else "")

serie_html = (
    '<p style="margin-top:26px"><em>Versão em português da nota '
    '<a href="../posts/zero-links-between-neighbours.html">&quot;Zero links between '
    'neighbours&quot;</a> — parte da série <a href="../series-field-notes.html">Field '
    'Notes</a>.</em></p>'
)
hub_li = ('    <li><a href="/pt/zero-links-between-neighbours.html">Zero links entre '
          'vizinhos</a> <span class="dim">(a nota 5, nesta página)</span></li>')
hub_ancora = ('    <li><a href="/pt/receipt-200-index-zero.html">O recibo diz 200. '
              'O índice diz zero.</a>')

spec = {
    "titulo": TITULO, "desc": DESC, "corpo_html": corpo_html,
    "disclosure_html": disclosure_html, "serie_html": serie_html,
    "hub_li": hub_li, "hub_ancora": hub_ancora, "devto_id": 4551801,
}
OUT.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
print("spec gravado:", OUT, len(json.dumps(spec)), "B")
print("corpo_html:", len(corpo_html), "B; disclosure:", len(disclosure_html), "B")
