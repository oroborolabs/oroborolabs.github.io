# -*- coding: utf-8 -*-
"""publicar-peca.py — fluxo de publicacao em 1 comando (E-022, forja j61 F1).

Uso: python publicar-peca.py <caminho-relativo.html> [mais.html ...]

Ordem obrigatoria (falha fechado — aborta com exit 2 ANTES do push):
  1. grep LEI DO SIGILO em cada arquivo (aborta se achar);
  2. regenera sitemap.xml (gerar-sitemap.py) e roda --check (exit 2 se o
     sitemap divergir do disco — lastmod velho e pior que ausente, j60);
  3. git add so dos arquivos pedidos + sitemap.xml, commit, push;
  4. verifica AO VIVO cada URL + sitemap (HTTP 200, regra 43);
  5. IndexNow com o lote alterado + sitemap, recibo em missao\\radares\\.

E-022: sync por construcao — quem publicar NAO consegue esquecer o sitemap.

E-023 (forja j62 F1): antes de tudo, insere sozinho o bloco
"Read before or after" (2 links p/ as 2 notas mais recentes que a peca
ainda nao linka) em cada peca que ainda nao tem o bloco — nenhuma peca
nova nasce com 0 links internos. Idempotente pela marca; backup
.bak-<data>-j63 antes de escrever. --dry mostra e nao escreve.

E-036 (forja j71 F1): antes do commit, toda peca SEM og:image ganha
sozinha o bloco social completo (og:title/og:description/og:image/
og:url/twitter:card + canonical) — a E-035 foi corretiva em 61 paginas
que nasceram descobertas pelo fluxo velho. Idempotente pela presenca de
og:image; self-canonical existente e preservada (nao duplica); backup
.bak-<data>-j72 antes de escrever.
"""
import re, subprocess, sys, time, pathlib, urllib.request, hashlib

RAIZ = pathlib.Path(__file__).resolve().parent
SIGILO = re.compile(
    r"SIGILO|Gustavo|Oroboro\b(?! Labs)|99freelas|99 Freelas|pathofexile"
    r"|\d{3}\.\d{3}\.\d{3}-\d{2}|@gmail|@outlook|CPF"
    # j91: (?<!\.) — o literal "RG\b" case-insensitive casava o "rg" de
    # ".org" e bloqueou a publicacao de uma peca 2x na j91 (falso positivo);
    # RG-documento real nunca vem precedido de ponto.
    r"|(?<![.\w])RG\b", re.I)
BASE = "https://oroborolabs.github.io/"
KEY = (RAIZ / "1c8fea5ef0a4a1972a2126d2523d5bc0.txt").read_text().strip()
PROVA = pathlib.Path(r"C:\Users\Oroboro\missao\radares")

def run(cmd, **kw):
    r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(r.stdout, r.stderr); sys.exit(2)
    return r.stdout.strip()

def viva(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (publish-check)"})
    return urllib.request.urlopen(req, timeout=30).status

def main(argv=None):
    args = list(sys.argv[1:]) if argv is None else list(argv)
    arqs = [a for a in args if a not in ("--dry", "--arquivo")]
    DRY = "--dry" in args
    if not arqs:
        print("uso: python publicar-peca.py [--dry] <arq.html> [mais.html]"); sys.exit(2)

    # 0. E-023: encadeamento automatico (marca = idempotencia)
    MARCA = "Read before or after"
    # j74 (E-039): rota PT introduziu "Leia antes ou depois" — mesmo bloco, idioma
    # distinto. Idempotência aceita as duas marcas (a intenção é 1 bloco de
    # vizinhos por peça; regra 36/38). Fora de PT_EO, MARCA continua o gerado.
    MARCAS_BLOCO = ("Read before or after", "Leia antes ou depois")
    def _titulo(p):
        txt = p.read_text(encoding="utf-8")
        m = re.search(r"<h1[^>]*>(.*?)</h1>", txt, re.S) or re.search(r"<title>(.*?)</title>", txt, re.S)
        return re.sub(r"\s+", " ", m.group(1)).strip().rstrip(".") if m else p.stem

    def encadear(alvos, modo="recentes"):
        """E-024 (forja j63 F1): modo 'arquivo' linka VIZINHOS temporais
        (anterior e seguinte por mtime) em vez das 2 mais recentes — o
        arquivo vira grafo local, nao 22 paginas apontando o mesmo topo."""
        tocados = []
        posts = sorted(RAIZ.glob("posts/*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
        idx = {q.resolve(): i for i, q in enumerate(posts)}
        for a in alvos:
            p = RAIZ / a
            txt = p.read_text(encoding="utf-8")
            if any(m in txt for m in MARCAS_BLOCO):
                print("E-023: bloco ja presente em", a, "-> pula"); continue
            ja = set(re.findall(r'href="([^"]+\.html)"', txt))
            # j76 (E-041): alvo em pt/ ganha bloco PT ("Leia antes ou depois") e
            # candidatos de pt/ — o bloco EN em pagina PT foi o quase-erro da j74
            # (E-039 consertou so a idempotencia; o gerador continuava emitindo EN).
            if a.replace("\\", "/").startswith("pt/"):
                marca = "Leia antes ou depois"
                pool = [q for q in sorted(RAIZ.glob("pt/*.html"),
                        key=lambda q: q.stat().st_mtime, reverse=True)
                        if q.name not in ("index.html", "indice.html")]
            else:
                marca = MARCA
                pool = []
            if modo == "arquivo":
                i = idx[p.resolve()]
                cand = [q for q in (posts[i - 1:i] + posts[i + 1:i + 2])
                        if q.resolve() != p.resolve() and q.name not in ja
                        and not q.name.startswith("series-")]
            elif pool:
                cand = [q for q in pool
                        if q.resolve() != p.resolve() and q.name not in ja][:2]
            else:
                cand = [q for q in posts
                        if q.resolve() != p.resolve() and q.name not in ja and not q.name.startswith("series-")][:2]
            if len(cand) < (1 if modo == "arquivo" else 2):
                print("E-023: menos de", (1 if modo == "arquivo" else 2), "candidatas p/", a, "-> pula"); continue
            juntador = " e " if marca != MARCA else " ; and "
            links = juntador.join(
                f'<a href="{q.name}">{_titulo(q)}</a>' for q in cand)
            bloco = f'<p><em>{marca}: {links}.</em></p>\n'
            if '<div class="disclosure">' in txt:
                novo = txt.replace('<div class="disclosure">', bloco + '<div class="disclosure">', 1)
            elif "</article>" in txt:
                novo = txt.replace("</article>", bloco + "</article>", 1)
            else:
                novo = txt.replace("</body>", bloco + "</body>", 1)
            if novo == txt:
                print("E-023: sem ancora p/", a, "-> pula"); continue
            tocados.append((p, txt, novo, a))
        if DRY:
            for p, _, novo, a in tocados:
                print(f"E-023 (dry) {a}: inseriria bloco antes de disclosure/article/body")
            return
        for p, velho, novo, a in tocados:
            bak = p.with_name(p.name + ".bak-" + time.strftime("%Y-%m-%d") + "-j64")
            bak.write_text(velho, encoding="utf-8")
            p.write_text(novo, encoding="utf-8")
            print("E-023: bloco inserido em", a, "(backup", bak.name + ")")
    # 0. E-029 (forja j67 F1): SIGILO + existencia ANTES de qualquer escrita —
    # o lote nao pode ficar pela metade no disco (aconteceu no lote 2 do E-024:
    # 25 blocos inseridos, SIGILO abortou depois, nada publicado).
    def _check_template(a, txt):
        """E-030 (forja j67 F2): deriva de template vira exit 2 ANTES do push,
        nao achado de acidente (lote 2 do E-024: 2 posts com brand '>Oroboro<'
        pegos pela guarda SIGILO por sorte). Verificado contra 60 paginas
        (02/09): </article> NAO e exigido (11 paginas legitimas sem ele)."""
        probs = []
        if re.search(r">Oroboro<", txt): probs.append("brand deriva '>Oroboro<'")
        if "Oroboro Labs" not in txt: probs.append("sem 'Oroboro Labs'")
        if "<title>" not in txt: probs.append("sem <title>")
        return probs

    # E-089 (forja j115 F1): gerar-malha.py insere sozinho a entrada do index e o
    # item do feed ANTES da guarda E-060 rodar — a malha exigia 2 edicoes manuais
    # (2 abortos medidos na j115). Script SEPARADO, chamado por subprocess: nada
    # acontece ao IMPORTAR o gerar-malha.py (guarda __main__; licao j115). ATENCAO:
    # ESTE arquivo (publicar-peca.py) ainda executa o fluxo inteiro no import —
    # nunca o importe; validar literais com ast.parse/regex (regra 1 da peca #75).
    if not DRY:
        r = subprocess.run([sys.executable, "gerar-malha.py"] + arqs,
                           cwd=RAIZ, capture_output=True, text=True)
        print(r.stdout.strip())
        if r.returncode != 0:
            print("gerar-malha FALHOU:", r.stderr[-400:]); sys.exit(2)

    for a in arqs:
        p = RAIZ / a
        if not p.exists(): print("NAO EXISTE:", a); sys.exit(2)
        txt = p.read_text(encoding="utf-8")
        m = SIGILO.search(txt)
        if m: print("SIGILO em", a, "->", m.group(0)); sys.exit(2)
        probs = _check_template(a, txt)
        if probs: print("TEMPLATE em", a, "->", "; ".join(probs)); sys.exit(2)
        # E-060 (forja j90): peca FORA da malha de entrada e peca invisivel —
        # o lote j85-j89 publicou 5 notas que o index.html e o feed.xml nunca
        # listaram (medido j90: 6/59 posts fora do index, 5 fora do feed).
        # Exige entrada na malha ANTES do push; atualizar index/feed no mesmo commit.
        malha = (RAIZ / "index.html").read_text(encoding="utf-8")
        feedtxt = (RAIZ / "feed.xml").read_text(encoding="utf-8")
        slug = a.replace("posts/", "")
        # j116 (revisor item 18): no --dry a malha nao aborta — o preview tem que
        # chegar ate E-023/E-036; na execucao real a guarda segue fail-closed.
        if not DRY and a.startswith("posts/") and slug not in malha:
            print("MALHA em", a, "-> slug ausente de index.html (E-060)"); sys.exit(2)
        if not DRY and a.startswith("posts/") and slug not in feedtxt:
            print("MALHA em", a, "-> slug ausente de feed.xml (E-060)"); sys.exit(2)
        if DRY and a.startswith("posts/") and (slug not in malha or slug not in feedtxt):
            print("(dry) MALHA: ", a, "fora do index/feed — o gerar-malha.py "
                  "inserira na execucao real")

    # 0.5 E-036 (forja j71 F1): bloco social sozinho em peca sem og:image.
    COVER = BASE + "cover-field-notes.png"
    # E-063 (forja j92 F1): a 1a linha pos-h1 das pecas e o selo ".meta"
    # ("2026-09-03 · field note ...") — 2 datas publicadas provaram (j93).
    # Pula o <p> datado; se TODOS os <p> forem .meta, devolve vazio (regra 7).
    META_P = re.compile(r"^20\d\d-\d\d-\d\d")
    def _descricao(txt):
        """1o <p> NAO-.meta do corpo como og:description (texto puro, <=160)."""
        corpo = re.split(r"</h1>", txt, 1)[-1]
        m = None
        for m in re.finditer(r"<p[^>]*>(.*?)</p>", corpo, re.S):
            t0 = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
            if not META_P.match(t0):
                break
        else:
            return ""
        if not m: return ""
        t = re.sub(r"<[^>]+>", " ", m.group(1))
        t = re.sub(r"\s+", " ", t).strip()
        return (t[:157] + "...") if len(t) > 160 else t

    def social(alvos):
        tocados = []
        for a in alvos:
            p = RAIZ / a
            txt = p.read_text(encoding="utf-8")
            if 'property="og:image"' in txt or "property='og:image'" in txt:
                print("E-036: og:image ja presente em", a, "-> pula"); continue
            rel = pathlib.PurePosixPath(a.replace("\\", "/")).as_posix()
            url = BASE + rel
            desc = _descricao(txt)
            titulo = _titulo(p)
            # j107 (E-036 r2, regra 38): o defeito da j106 foi o CONSORTO na peca,
            # nao no gerador — descricao com aspas cruas quebrava o atributo HTML.
            # Todo valor interpolado em atributo passa por escape de atributo.
            from html import escape as _esc
            bloco = (
                '<link rel="canonical" href="%s"/>\n'
                '<meta property="og:type" content="article"/>\n'
                '<meta property="og:title" content="%s"/>\n'
                '<meta property="og:description" content="%s"/>\n'
                '<meta property="og:image" content="%s"/>\n'
                '<meta property="og:url" content="%s"/>\n'
                '<meta name="twitter:card" content="summary_large_image"/>\n'
                '<meta name="twitter:title" content="%s"/>\n'
                '<meta name="twitter:description" content="%s"/>\n'
                '<meta name="twitter:image" content="%s"/>\n'
            ) % (_esc(url, True), _esc(titulo, True), _esc(desc, True),
                 _esc(COVER, True), _esc(url, True),
                 _esc(titulo, True), _esc(desc, True), _esc(COVER, True))
            if "<head" not in txt:
                print("E-036: sem <head> em", a, "-> pula"); continue
            novo = re.sub(r"(<head[^>]*>)", r"\1\n" + bloco, txt, count=1)
            if novo == txt:
                print("E-036: sem ancora de head em", a, "-> pula"); continue
            tocados.append((p, txt, novo, a))
        if DRY:
            for p, _, _, a in tocados:
                print(f"E-036 (dry) {a}: inseriria bloco social (og/twitter/canonical)")
            return
        for p, velho, novo, a in tocados:
            bak = p.with_name(p.name + ".bak-" + time.strftime("%Y-%m-%d") + "-j72")
            bak.write_text(velho, encoding="utf-8")
            p.write_text(novo, encoding="utf-8")
            print("E-036: bloco social inserido em", a, "(backup", bak.name + ")")

    encadear(arqs, modo="arquivo" if "--arquivo" in args else "recentes")
    social(arqs)
    if DRY:
        print("dry: nada escrito, fluxo de publicacao nao iniciado"); sys.exit(0)

    # 1. sitemap em sync (SIGILO ja rodou antes da escrita — E-029)
    run([sys.executable, "gerar-sitemap.py"])
    run([sys.executable, "gerar-sitemap.py", "--check"])

    # 3. commit + push
    alvos = arqs + ["sitemap.xml"]
    # E-066 (forja j94 F3): feed.xml alterado ficava FORA do commit — a 1a
    # verificacao ao vivo da j94 mostrou 41 itens no ar com 62 no disco ate
    # commit manual extra. Entra no commit quando estiver modificado.
    if subprocess.run(["git", "diff", "--quiet", "--", "feed.xml"],
                      cwd=RAIZ).returncode != 0:
        alvos.append("feed.xml")
    # E-066 r2 (j95): cards og referenciados pelas paginas moram em img/og/ —
    # pagina patcheada apontando PNG nao commitado da 404 no card. O dir entra
    # inteiro (so havera mudanca no que mudou).
    if (RAIZ / "img" / "og").exists():
        alvos.append("img/og")
    run(["git", "add"] + alvos)
    msg = "publish: " + ", ".join(pathlib.Path(a).stem for a in arqs)
    # j76: publish idempotente — nada a commitar e SUCESSO (os arquivos ja estao
    # no ar; a intencao do fail-closed e abortar ANTES do push em SIGILO/sitemap,
    # nao punir a reexecucao). Empurra push so quando houve commit.
    r = subprocess.run(["git", "commit", "-m", msg], cwd=RAIZ, capture_output=True, text=True)
    if r.returncode != 0 and "no changes added" not in r.stdout + r.stderr and "nothing to commit" not in r.stdout + r.stderr:
        print(r.stdout, r.stderr); sys.exit(2)
    if r.returncode == 0:
        run(["git", "push"])
        print("pushed:", msg)
    else:
        print("nada a commitar (publish idempotente) — verificando ao vivo")

    # 4. live 200 + CONTEUDO (Pages tem lag — ate 20 tentativas de 15 s)
    # j86 (E-052, forja j85 F1): 200 ≠ atualizado (regra 43 estendida) — o build
    # do Pages demora ~2 min e 4/5 amostras de E-051 serviram conteudo VELHO com
    # 200. A verificacao passa a conferir o CONTEUDO servido contra o disco
    # (sha256; cache-buster p/ furar CDN). Falha apos o teto = exit 3.
    urls = [BASE + pathlib.PurePosixPath(a.replace("\\", "/")).as_posix() for a in arqs]
    urls.append(BASE + "sitemap.xml")

    def _baixado(u):
        req = urllib.request.Request(
            u + ("&" if "?" in u else "?") + "cb=%d" % int(time.time() * 1000),
            headers={"User-Agent": "Mozilla/5.0 (publish-check)"})
        return urllib.request.urlopen(req, timeout=30).read()

    def conteudo_confere(caminho, url):
        # core.autocrlf=true: o disco guarda CRLF e o repo (o que o Pages serve)
        # tem LF — comparação byte a byte daria falso "velho" em toda página
        # Windows (medido j86: index.html, 203 linhas, hash só confere
        # normalizado). O que se quer detectar é CONTEÚDO velho, não quebra de
        # linha.
        _norm = lambda b: b.replace(b"\r\n", b"\n")
        servido = _norm(_baixado(url))
        return hashlib.sha256(servido).digest() == \
            hashlib.sha256(_norm((RAIZ / caminho).read_bytes())).digest()

    for i in range(20):
        try:
            codes = {u: viva(u) for u in urls}
            if all(c == 200 for c in codes.values()):
                # sitemap.xml no disco nao e o que o Pages serve byte a byte? E:
                # gerar-sitemap.py escreveu antes do push (passo 1) — mesmo bytes.
                stale = [a for a, u in zip(arqs, urls[:-1])
                         if not conteudo_confere(a, u)]
                if not stale:
                    print("LIVE + CONTEUDO:", codes); break
                print("200 com conteudo VELHO em %d/%d (aguardando build): %s"
                      % (len(stale), len(arqs), ", ".join(stale)))
        except Exception as e:
            print("aguardando Pages:", e)
        time.sleep(15)
    else:
        print("PAGINA(S) NAO CONFIRMADAS (200+conteudo) EM 5 min — checar "
              "manualmente"); sys.exit(3)

    # 4.5 E-067 (forja j95 F3): os PNGs img/og referenciados pelo lote sao
    # verificados AO VIVO — a verificacao de CONTEUDO (E-052) cobre so HTML, e
    # pagina no ar apontando card 404 passava como publicado (buraco medido j95:
    # commit da j94 ficou sem os 12 PNGs ate commit manual). GET (headless CDN
    # do Pages responde 200 no HEAD, mas GET e o que o card real faz).
    def _og_images(txt):
        return sorted(set(re.findall(
            r'<meta property="og:image" content="([^"]+)"', txt)))
    pngs = {}
    for a in arqs:
        for u in _og_images((RAIZ / a).read_text(encoding="utf-8")):
            if u.startswith("http"):
                pngs[u] = a
    falha_png = []
    for u, origem in sorted(pngs.items()):
        try:
            if viva(u) != 200:
                falha_png.append("%s (em %s): HTTP nao-200" % (u, origem))
        except Exception as e:
            falha_png.append("%s (em %s): %s" % (u, origem, e))
    if falha_png:
        print("E-067: CARD(S) NAO CONFIRMADOS AO VIVO:\n" + "\n".join(falha_png))
        sys.exit(3)
    print("E-067: %d card(s) og ao vivo 200" % len(pngs))

    # 5. IndexNow
    lote = urls  # URLs alteradas + sitemap (último elemento do passo 4)
    body = {"host": "oroborolabs.github.io", "key": KEY,
            "keyLocation": BASE + KEY + ".txt", "urlList": lote}
    req = urllib.request.Request("https://api.indexnow.org/indexnow",
        data=__import__("json").dumps(body).encode(),
        headers={"Content-Type": "application/json; charset=utf-8"})
    st = urllib.request.urlopen(req, timeout=30).status
    recibo = PROVA / "indexnow-publicar-peca.txt"
    recibo.write_text(
        "HTTP %s\npublicar-peca.py lote %d\n%s" % (st, len(lote), "\n".join(lote)),
        encoding="utf-8")
    print("IndexNow", st, "-", len(lote), "URLs; recibo em radares\\indexnow-publicar-peca.txt")

    # 6. E-061 (forja j91 F2): outcome SERP do dia JUNTO do recibo — o par
    # recibo+datapoint nasce no mesmo arquivo (7 recibos 200 e 5 datapoints 0
    # viveram separados de j49 a j91 e "0 indexado" foi descoberta tardia).
    # A sonda depende da nave viva (CDP); se cair, o recibo fica com o motivo
    # e campo vazio (regra 7) — nunca recibo sem outcome em silêncio.
    # E-090 (forja j115 F2): sonda V3 (aba unica, Page.navigate) — a v2 depende
    # do padrao aba-nova que o chromium local recusa apos uso (0,0 s hold novo x
    # 45,0 s pos-sonda, recibo serp-j115-timing-conexoes.txt). Exit 3 da v3 e
    # DATAPONTE INVALIDO (SERP lixo), um outcome valido — nao "indisponivel".
    sonda = pathlib.Path(r"C:\Users\Oroboro\missao\nave\sonda-bing-indexacao-v3.py")
    r = subprocess.run([sys.executable, str(sonda), time.strftime("%Y-%m-%d")],
                       capture_output=True, text=True, timeout=300)
    with recibo.open("a", encoding="utf-8") as f:
        f.write("\n--- outcome SERP Bing (E-061, mesmo dia; sonda v3/E-090) ---\n")
        linhas = (r.stdout or "").strip().splitlines()
        veredito = [l for l in linhas
                    if l.startswith(("DATAPONTE", "— quórum", "NAVE CAIU", "captcha"))]
        if veredito:
            f.write("\n".join(veredito) + "\n")
            print("E-061: outcome SERP v3 anexado ao recibo (%d linhas)"
                  % len(veredito))
        else:
            f.write("SONDA INDISPONIVEL: exit %d\n%s\n"
                    % (r.returncode, (r.stderr or "")[-400:]))
            print("E-061: sonda v3 indisponivel (exit %d) — motivo no recibo"
                  % r.returncode)


# E-091 (forja j116 F1, executada j117): fluxo inteiro embrulhado em
# main() + guarda __main__ — este script COMMITA e EMPURRA, entao importa-lo
# precisa ser inofensivo (licao do acidente j115: validacao importou script
# executavel e o fluxo de publicacao rodou sem querer).
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]) or 0)
