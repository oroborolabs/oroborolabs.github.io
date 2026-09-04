# -*- coding: utf-8 -*-
"""gerar-malha.py — E-089 (forja j115 F1): index.xml/feed de entrada em 1 comando.

Insere sozinho, para cada post passado, a entrada do index.html e o item do
feed.xml — a malha E-060 exigia edicao manual de 2 arquivos (2 abortos
medidos na j115 antes do LIVE 200). Idempotente por slug; backup
.bak-<data>-<janela> antes de escrever; --dry mostra e nao escreve;
--check so verifica (exit 2 se algum slug ausente).

Chamado por publicar-peca.py ANTES da guarda E-060; pode rodar isolado:
  python gerar-malha.py [--dry|--check] posts/foo.html [mais.html]

Nao tem efeito no import (licao j115: modulo com acao no top-level
publicou sem querer) — todo o corpo vive em funcoes e o main esta sob
if __name__ == "__main__".
"""
import pathlib
import re
import sys
import time
from html import escape as _esc

RAIZ = pathlib.Path(__file__).resolve().parent
BASE = "https://oroborolabs.github.io/"
JANELA = "j116"
META_P = re.compile(r"^20\d\d-\d\d-\d\d")


def titulo_de(txt):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", txt, re.S) or re.search(
        r"<title>(.*?)</title>", txt, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip().rstrip(".") if m else ""


def descricao_de(txt):
    """1o <p> NAO-.meta do corpo, texto puro (mesma regra do publicar-peca)."""
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
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
    return (t[:157] + "...") if len(t) > 160 else t


def xml_esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def entrada_index(slug, tit, desc, data):
    bloco = (
        '    <p style="margin-top:12px"><a href="posts/%s" '
        'style="color:var(--gold);text-decoration:none">NEW — %s →</a><br>\n'
        '    <span style="color:var(--dim);font-size:14px">Field note, %s: '
        '%s</span></p>\n'
    ) % (slug, _esc(tit, True), data, _esc(desc, True))
    return bloco


def item_feed(slug, tit, desc, data):
    return (
        "<item>\n<title>%s</title>\n<link>%s</link>\n<guid>%s</guid>\n"
        "<pubDate>%s</pubDate>\n<description>%s</description>\n</item>\n"
    ) % (xml_esc(tit), BASE + "posts/" + slug, BASE + "posts/" + slug,
         data, xml_esc(desc))


def main(argv):
    modo_dry = "--dry" in argv
    modo_check = "--check" in argv
    arqs = [a for a in argv if not a.startswith("--")]
    if not arqs:
        print("uso: python gerar-malha.py [--dry|--check] posts/arq.html [...]")
        return 2

    idx_p = RAIZ / "index.html"
    feed_p = RAIZ / "feed.xml"
    idx = idx_p.read_text(encoding="utf-8")
    feed = feed_p.read_text(encoding="utf-8")
    idx0, feed0 = idx, feed
    hoje = time.strftime("%Y-%m-%d")
    faltando = []

    for a in arqs:
        rel = a.replace("\\", "/")
        if not rel.startswith("posts/"):
            print("gerar-malha: alvo fora de posts/, pulando:", a)
            continue
        p = RAIZ / rel
        if not p.exists():
            print("NAO EXISTE:", a)
            return 2
        slug = rel[len("posts/"):]
        txt = p.read_text(encoding="utf-8")
        if slug not in idx:
            if modo_check:
                faltando.append("index.html: " + slug)
            else:
                tit = titulo_de(txt)
                desc = descricao_de(txt)
                if not tit or not desc:
                    print("gerar-malha: sem titulo/descricao derivaveis em",
                          a, "-> NAO insere (regra 7: campo vazio, nao suposicao)")
                    return 2
                # insere ANTES do 1o bloco de post existente (mais novo no topo)
                m = re.search(r'    <p style="margin-top:12px"><a href="posts/', idx)
                if not m:
                    print("gerar-malha: sem ancora de posts/ no index.html")
                    return 2
                # o rotulo NEW dos posts antigos sai ANTES da insercao (so o
                # novo entra com NEW; o replace pos-insercao comeria o proprio)
                idx = re.sub(r'(<a href="posts/[^"]*"[^>]*>)NEW — ', r"\1", idx)
                bloco = entrada_index(slug, tit, desc, hoje)
                idx = idx[:m.start()] + bloco + idx[m.start():]
                print("gerar-malha: entrada do index gerada p/", slug)
        if slug not in feed:
            if modo_check:
                faltando.append("feed.xml: " + slug)
            else:
                tit = titulo_de(txt)
                desc = descricao_de(txt)
                if not tit or not desc:
                    print("gerar-malha: sem titulo/descricao derivaveis em", a)
                    return 2
                if "<item>" not in feed:
                    print("gerar-malha: feed.xml sem <item> (formato inesperado)")
                    return 2
                feed = feed.replace("<item>", item_feed(slug, tit, desc, hoje), 1)
                print("gerar-malha: item do feed gerado p/", slug)

    if modo_check:
        if faltando:
            print("MALHA INCOMPLETA:", "; ".join(faltando))
            return 2
        print("gerar-malha --check: %d/%d na malha" % (len(arqs), len(arqs)))
        return 0
    if modo_dry or (idx == idx0 and feed == feed0):
        if modo_dry:
            print("dry: nada escrito")
        else:
            print("gerar-malha: nada a fazer (malha ja completa — idempotente)")
        return 0

    bak_suf = ".bak-" + time.strftime("%Y-%m-%d") + "-" + JANELA
    idx_p.with_name(idx_p.name + bak_suf).write_text(idx0, encoding="utf-8")
    idx_p.write_text(idx, encoding="utf-8")
    feed_p.with_name(feed_p.name + bak_suf).write_text(feed0, encoding="utf-8")
    feed_p.write_text(feed, encoding="utf-8")
    print("gerar-malha: index.html + feed.xml atualizados (backup", bak_suf + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
