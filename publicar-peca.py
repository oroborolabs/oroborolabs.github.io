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
"""
import re, subprocess, sys, time, pathlib, urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent
SIGILO = re.compile(
    r"SIGILO|Gustavo|Oroboro\b(?! Labs)|99freelas|99 Freelas|pathofexile"
    r"|\d{3}\.\d{3}\.\d{3}-\d{2}|@gmail|@outlook|CPF|RG\b", re.I)
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

arqs = sys.argv[1:]
if not arqs:
    print("uso: python publicar-peca.py <arq.html> [mais.html]"); sys.exit(2)

# 1. SIGILO + existencia
for a in arqs:
    p = RAIZ / a
    if not p.exists(): print("NAO EXISTE:", a); sys.exit(2)
    m = SIGILO.search(p.read_text(encoding="utf-8"))
    if m: print("SIGILO em", a, "->", m.group(0)); sys.exit(2)

# 2. sitemap em sync
run([sys.executable, "gerar-sitemap.py"])
run([sys.executable, "gerar-sitemap.py", "--check"])

# 3. commit + push
run(["git", "add"] + arqs + ["sitemap.xml"])
msg = "publish: " + ", ".join(pathlib.Path(a).stem for a in arqs)
run(["git", "commit", "-m", msg])
run(["git", "push"])
print("pushed:", msg)

# 4. live 200 (Pages tem lag — ate 12 tentativas de 10 s)
urls = [BASE + pathlib.PurePosixPath(a.replace("\\", "/")).as_posix() for a in arqs]
urls.append(BASE + "sitemap.xml")
for i in range(12):
    try:
        codes = {u: viva(u) for u in urls}
        if all(c == 200 for c in codes.values()):
            print("LIVE:", codes); break
    except Exception as e:
        print("aguardando Pages:", e)
    time.sleep(10)
else:
    print("PAGINA(S) NAO CONFIRMADA EM 2 min — checar manualmente"); sys.exit(3)

# 5. IndexNow
lote = urls  # URLs alteradas + sitemap (último elemento do passo 4)
body = {"host": "oroborolabs.github.io", "key": KEY,
        "keyLocation": BASE + KEY + ".txt", "urlList": lote}
req = urllib.request.Request("https://api.indexnow.org/indexnow",
    data=__import__("json").dumps(body).encode(),
    headers={"Content-Type": "application/json; charset=utf-8"})
st = urllib.request.urlopen(req, timeout=30).status
(PROVA / "indexnow-publicar-peca.txt").write_text(
    "HTTP %s\npublicar-peca.py lote %d\n%s" % (st, len(lote), "\n".join(lote)),
    encoding="utf-8")
print("IndexNow", st, "-", len(lote), "URLs; recibo em radares\\indexnow-publicar-peca.txt")
