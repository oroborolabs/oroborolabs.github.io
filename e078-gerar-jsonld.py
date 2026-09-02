# -*- coding: utf-8 -*-
"""e078-gerar-jsonld.py — structured data (JSON-LD) em toda pagina do site.

Medido 2026-09-03 (j96): 0/73 paginas com application/ld+json. Doc viva do
Google confrontada 02/09 (developers.google.com Article): nenhum campo
obrigatorio; recomendados = headline, image, datePublished/dateModified
ISO 8601 COM timezone, author como Organization com url.

Tipos (uma regra por page-kind, regra 16):
  posts/*.html e pt/*.html (nao-index) -> BlogPosting
  demais (raiz e pt/index)            -> WebPage

Fontes dos campos (nada inventado — tudo ja vive na pagina):
  url         = canonical (1a) senao og:url; sem nenhuma -> pagina pulada
  headline    = og:title senao <title>
  description = og:description senao _descricao (mesma heuristica do
                publicar-peca: 1o <p> nao-.meta, <=160)
  image       = og:image (cards proprios desde a E-065)
  datePublished = data da linha .meta da peca; sem .meta -> 1o commit git
                (%aI). dateModified = ultimo commit git (%cI) — ambos com
                offset de timezone.

Idempotente pela presenca de 'application/ld+json'. Backup
.bak-<data>-j96 antes de escrever. --dry mostra e nao escreve.

Uso: python e078-gerar-jsonld.py [--dry]
"""
import json, re, subprocess, sys, time, pathlib

RAIZ = pathlib.Path(__file__).resolve().parent
BASE = "https://oroborolabs.github.io/"
DIA = time.strftime("%Y-%m-%d")
ORG = {"@type": "Organization", "name": "Oroboro Labs", "url": BASE}
META_P = re.compile(r"^20\d\d-\d\d-\d\d")

def git(caminho, fmt, primeiro=False):
    cmd = ["git", "log", "--format=" + fmt, "--", caminho]
    if primeiro:
        cmd.append("--reverse")
    r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True)
    linhas = [l for l in r.stdout.splitlines() if l.strip()]
    return linhas[0].strip() if linhas else None

def _descricao(txt):
    corpo = re.split(r"</h1>", txt, 1)[-1]
    m = None
    for m in re.finditer(r"<p[^>]*>(.*?)</p>", corpo, re.S):
        t0 = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
        if not META_P.match(t0):
            break
    else:
        return ""
    if not m:
        return ""
    t = re.sub(r"<[^>]+>", " ", m.group(1))
    return re.sub(r"\s+", " ", t).strip()[:160]

def _meta_data(txt):
    """Data da linha .meta da peca: 1o <p> pos-h1 que COMECA com a data
    ("2026-09-03 · field note ..."). Procurada no corpo (pos-h1) para nao
    pegar data de prose/nav; tz BRT declarada (Google recomenda tz)."""
    corpo = re.split(r"</h1>", txt, 1)[-1]
    m = re.search(r"<p[^>]*>\s*(20\d\d-\d\d-\d\d)", corpo)
    return m.group(1) + "T09:00:00-03:00" if m else None

def _attr(txt, prop):
    m = re.search(r'(?:property|name)="%s" content="([^"]*)"' % re.escape(prop), txt)
    return m.group(1) if m else None

DRY = "--dry" in sys.argv
paginas = [p for p in RAIZ.rglob("*.html") if ".bak-" not in p.name]
tocados, pulados = [], []
for p in sorted(paginas):
    rel = p.relative_to(RAIZ).as_posix()
    txt = p.read_text(encoding="utf-8")
    if "application/ld+json" in txt:
        pulados.append((rel, "ja tem JSON-LD")); continue
    if "</head>" not in txt:
        pulados.append((rel, "sem </head>")); continue
    url = _attr(txt, "og:url") or _attr(txt, "canonical") or None
    m = re.search(r'<link rel="canonical" href="([^"]+)"', txt)
    url = m.group(1) if m else (_attr(txt, "og:url") or None)
    if not url:
        pulados.append((rel, "sem url (canonical/og:url)")); continue
    headline = _attr(txt, "og:title") or _attr(txt, "og:title") \
        or (re.sub(r"\s+", " ", re.search(r"<title>(.*?)</title>", txt, re.S).group(1)).strip()
            if re.search(r"<title>(.*?)</title>", txt, re.S) else None)
    desc = _attr(txt, "og:description") or _descricao(txt)
    image = _attr(txt, "og:image")
    e_post = rel.startswith("posts/") or (rel.startswith("pt/") and rel != "pt/index.html")
    if e_post:
        pub = _meta_data(txt) or git(rel, "%aI", primeiro=True)
        # dateModified nunca anterior ao datePublished (ISO 8601 compara
        # lexicografico dentro do mesmo offset; commit de import pode ser
        # mais velho que o selo .meta da peca — pegou j96)
        mod = max(x for x in (git(rel, "%cI"), pub) if x)
        if not pub:
            pulados.append((rel, "post sem data (.meta e git)")); continue
        obj = {"@context": "https://schema.org", "@type": "BlogPosting",
               "mainEntityOfPage": url, "url": url, "headline": headline,
               "image": [image] if image else None,
               "datePublished": pub, "dateModified": mod,
               "author": ORG, "publisher": ORG}
        if desc:
            obj["description"] = desc
    else:
        obj = {"@context": "https://schema.org", "@type": "WebPage",
               "url": url, "name": headline}
        if desc:
            obj["description"] = desc
        if image:
            obj["image"] = [image]
    obj = {k: v for k, v in obj.items() if v is not None}  # campo vazio > suposicao
    bloco = ('<script type="application/ld+json">\n'
             + json.dumps(obj, ensure_ascii=False, indent=1)
             + "\n</script>\n")
    novo = txt.replace("</head>", bloco + "</head>", 1)
    if novo == txt:
        pulados.append((rel, "sem ancora </head>")); continue
    tocados.append((p, txt, novo, rel))

print("paginas: %d | com JSON-LD a criar: %d | puladas: %d"
      % (len(paginas), len(tocados), len(pulados)))
for rel, motivo in pulados:
    print("PULADA %s -> %s" % (rel, motivo))
if DRY:
    for _, _, _, rel in tocados[:5]:
        print("(dry) %s" % rel)
    print("dry: nada escrito"); sys.exit(0)
for p, velho, novo, rel in tocados:
    bak = p.with_name(p.name + ".bak-" + DIA + "-j96")
    if not bak.exists():
        bak.write_text(velho, encoding="utf-8")
    p.write_text(novo, encoding="utf-8")
print("JSON-LD gravado em %d paginas (backup .bak-%s-j96)" % (len(tocados), DIA))
