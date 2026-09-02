# -*- coding: utf-8 -*-
"""og-card.py — E-065 (forja j93 F3, reformulada): card og:image POR PECA.

A premissa original ("extrair a 1a imagem do corpo") foi MEDIDA e caiu:
55/55 posts tem uma unica <img> no corpo — o emblema do cabecalho, igual
em todas (j94). A variante executavel e GERAR o card: 1200x630, fundo
escuro, titulo da peca, data e rodape — deterministico (mesmo titulo ->
mesmo PNG). Pachas og:image/twitter:image de cada pagina para o card
proprio; fallback = cover generico (bloco social completo preservado).

Uso:
  python og-card.py --dry          # lista o que faria, nada escrito
  python og-card.py                # gera PNGs + patch nas paginas
Regras: patch cirurgico so na URL de imagem (regra 37 — revisar git diff
antes de commit; o commit e feito pelo publicar-peca.py). SIGILO: so usa
titulo/data ja publicos na propria pagina.
"""
import pathlib, re, sys

from PIL import Image, ImageDraw, ImageFont

RAIZ = pathlib.Path(__file__).resolve().parent
POSTS = RAIZ / "posts"
# E-065 r2 (j95): as 12 paginas fora de posts/ que o 1o passe nao alcancou —
# raiz (porta da frente, workshop, digest, calculadora) + pt/ (pagina do
# COMPRADOR, E-009). Slug prefixado p/ nao colidir com post de mesmo nome.
EXTRAS = [RAIZ / n for n in (
    "digest.html", "index.html", "price-display-calculator.html",
    "series-field-notes.html", "start-here.html", "workshop.html")]
PT = RAIZ / "pt"
EXTRAS += [PT / p.name for p in sorted(PT.glob("*.html"))
           if not p.name.endswith(".bak")] if PT.exists() else []
OGDIR = RAIZ / "img" / "og"
BASE = "https://oroborolabs.github.io/"
COVER = BASE + "cover-field-notes.png"
DRY = "--dry" in sys.argv

W, H = 1200, 630
BG = (16, 20, 24)
FG = (232, 236, 240)
ACCENT = (255, 176, 32)   # laranja da marca
MUT = (140, 148, 156)

F_BOLD = ImageFont.truetype("arialbd.ttf", 58)
F_META = ImageFont.truetype("arial.ttf", 30)

META_P = re.compile(r"^20\d\d-\d\d-\d\d")


def _titulo(txt):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", txt, re.S) or \
        re.search(r"<title>(.*?)</title>", txt, re.S)
    if not m:
        return ""
    t = re.sub(r"<[^>]+>", " ", m.group(1))
    return re.sub(r"\s+", " ", t).strip()


def _data(txt):
    corpo = re.split(r"</h1>", txt, 1)[-1]
    for m in re.finditer(r"<p[^>]*>(.*?)</p>", corpo, re.S):
        t0 = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
        if META_P.match(t0):
            return t0.split("·")[0].strip()
    return ""


def _wrap(d, t, f, maxw):
    linhas, cur = [], ""
    for p in t.split():
        cand = (cur + " " + p).strip()
        if d.textlength(cand, font=f) <= maxw:
            cur = cand
        else:
            if cur:
                linhas.append(cur)
            cur = p
    if cur:
        linhas.append(cur)
    return linhas[:5]  # cabe em 5 linhas; titulo maior que isso e caso raro


def gera(slug, titulo, data):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 14, H], fill=ACCENT)
    y = 96
    for lin in _wrap(d, titulo, F_BOLD, W - 160):
        d.text((80, y), lin, font=F_BOLD, fill=FG)
        y += 72
    rodape = (data + " · " if data else "") + "oroborolabs.github.io"
    d.text((80, H - 96), rodape, font=F_META, fill=MUT)
    out = OGDIR / (slug + ".png")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG")


def main():
    feitos, pulados = [], []
    paginas = sorted(POSTS.glob("*.html")) + EXTRAS
    for p in paginas:
        txt = p.read_text(encoding="utf-8")
        rel = p.relative_to(RAIZ)
        # pt/foo.html -> pt-foo (evita colidir com post de mesmo nome);
        # posts/ mantem o slug nu da j94 (PNGs ja publicados) e a raiz tb
        slug = "pt-" + p.stem if rel.parent == pathlib.Path("pt") else p.stem
        titulo = _titulo(txt)
        if not titulo:
            pulados.append((slug, "sem titulo"))
            continue
        if not DRY:
            gera(slug, titulo, _data(txt))
            novo = txt.replace('content="' + COVER + '"',
                               'content="%simg/og/%s.png"' % (BASE, slug))
            if novo == txt:
                if "img/og/" in txt:
                    continue  # ja tem card proprio (E-065/r2) — ok, nao e falha
                pulados.append((slug, "og:image nao apontava o cover"))
                continue
            p.write_text(novo, encoding="utf-8")
        feitos.append(slug)
    print("E-065: %d cards %s" % (len(feitos), "geraria" if DRY else "gerados+patch"))
    for s in feitos[:5]:
        print("  ", s)
    if len(feitos) > 5:
        print("   ... +%d" % (len(feitos) - 5))
    for s, m in pulados:
        print("PULADO", s, "->", m)
    if pulados and not DRY:
        sys.exit(2)  # falha fechado: pagina ficou no cover generico sem motivo


if __name__ == "__main__":
    main()
