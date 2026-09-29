#!/usr/bin/env python3
"""Vigia de Ofertas: robô de monitoramento de preço com aviso no celular.

Só biblioteca padrão (Python 3.12). Lê alvos.json, extrai preço e disponibilidade
de cada página (JSON-LD schema.org, com fallback por meta itemprop), compara com
estado.json, registra mudanças em historico.csv e avisa por ntfy.sh.

Uso:  python robo.py [arquivo_de_alvos.json]
Env:  NTFY_TOPICO  tópico do ntfy (padrão oroborolabs-vigia-ofertas; vazio = sem aviso)
"""
import base64
import csv
import gzip
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

AQUI = Path(__file__).resolve().parent
TOPICO_PADRAO = "oroborolabs-vigia-ofertas"
TIMEOUT = 20
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
CAMPOS_CSV = ["data_iso_utc", "nome", "url", "preco_antigo", "preco_novo", "disponibilidade"]


# ---------------------------------------------------------------- extração
class _Coletor(HTMLParser):
    """Junta blocos JSON-LD e metas/links com itemprop."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.jsonld, self.itemprops = [], {}
        self._em_ld, self._buf = False, []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "script" and "ld+json" in a.get("type", "").lower():
            self._em_ld, self._buf = True, []
        elif tag in ("meta", "link") and a.get("itemprop"):
            valor = a.get("content") or a.get("href") or ""
            self.itemprops.setdefault(a["itemprop"].lower(), valor)

    def handle_data(self, data):
        if self._em_ld:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._em_ld:
            self._em_ld = False
            self.jsonld.append("".join(self._buf))


def _tipos(no):
    t = no.get("@type", [])
    t = [t] if isinstance(t, str) else list(t) if isinstance(t, list) else []
    return [str(x).rsplit("/", 1)[-1].lower() for x in t]


def _percorrer(no):
    """Gera todos os dicionários de um JSON-LD (@graph, listas, aninhados)."""
    if isinstance(no, list):
        for item in no:
            yield from _percorrer(item)
    elif isinstance(no, dict):
        yield no
        for v in no.values():
            if isinstance(v, (list, dict)):
                yield from _percorrer(v)


def normaliza_preco(bruto):
    """Converte '1.299,90', '1299.90', 1299.9, 'R$ 49,90' em float. None se não der."""
    if bruto is None or isinstance(bruto, bool):
        return None
    if isinstance(bruto, (int, float)):
        return float(bruto)
    s = re.sub(r"[^\d.,]", "", str(bruto))
    if not re.search(r"\d", s):
        return None
    if "," in s and "." in s:
        # o último separador é o decimal
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".") if s.count(",") == 1 else s.replace(",", "")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def _disp(valor):
    if not valor:
        return ""
    return str(valor).rstrip("/").rsplit("/", 1)[-1]  # https://schema.org/InStock -> InStock


def _oferta_de(no):
    """Devolve (preco, disponibilidade) do primeiro Offer útil de um Product."""
    ofertas = no.get("offers")
    if ofertas is None:
        return None, ""
    for o in _percorrer(ofertas):
        for chave in ("price", "lowPrice"):
            p = normaliza_preco(o.get(chave))
            if p is not None:
                return p, _disp(o.get("availability"))
        for s in _percorrer(o.get("priceSpecification")):
            p = normaliza_preco(s.get("price"))
            if p is not None:
                return p, _disp(o.get("availability"))
    return None, ""


def _blocos(col):
    for bloco in col.jsonld:
        try:
            yield json.loads(bloco.strip())
        except ValueError:
            continue


def extrair(html):
    """(preco, disponibilidade). Levanta ValueError se não achar preço."""
    col = _Coletor()
    col.feed(html)
    for dados in _blocos(col):
        for no in _percorrer(dados):
            if "product" in _tipos(no):
                preco, disp = _oferta_de(no)
                if preco is not None:
                    return preco, disp
    # ofertas soltas (Offer fora de Product)
    for dados in _blocos(col):
        for no in _percorrer(dados):
            if "offer" in _tipos(no) or "aggregateoffer" in _tipos(no):
                for chave in ("price", "lowPrice"):
                    p = normaliza_preco(no.get(chave))
                    if p is not None:
                        return p, _disp(no.get("availability"))
    p = normaliza_preco(col.itemprops.get("price"))
    if p is not None:
        return p, _disp(col.itemprops.get("availability"))
    raise ValueError("preço não encontrado (sem JSON-LD Product/Offer nem meta itemprop=price)")


def baixar(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9",
        "Accept-Encoding": "gzip",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        corpo = r.read()
        if r.headers.get("Content-Encoding", "").lower() == "gzip":
            corpo = gzip.decompress(corpo)
        cs = r.headers.get_content_charset() or "utf-8"
    return corpo.decode(cs, errors="replace")


# ---------------------------------------------------------------- aviso
def _h(texto):
    """Cabeçalhos HTTP só levam ASCII puro; acento vai em RFC 2047, que o ntfy decodifica."""
    texto = texto.replace("\n", " ")
    if texto.isascii():
        return texto
    return "=?UTF-8?B?" + base64.b64encode(texto.encode("utf-8")).decode("ascii") + "?="


def _brl(v):
    if v is None:
        return "sem preço anterior"
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def avisar(topico, nome, url, antigo, novo):
    corpo = f"{nome}: {_brl(antigo)} → {_brl(novo)}"
    req = urllib.request.Request(
        f"https://ntfy.sh/{topico}", data=corpo.encode("utf-8"), method="POST",
        headers={"Title": _h(f"Vigia de Ofertas: {nome}"), "Click": _h(url),
                 "Tags": "shopping_cart", "User-Agent": "vigia-ofertas/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        r.read()


# ---------------------------------------------------------------- principal
def _ler_json(caminho, padrao):
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return padrao


def _iso(dt):
    return dt.isoformat().replace("+00:00", "Z")


def main(argv):
    for fluxo in (sys.stdout, sys.stderr):  # consoles Windows usam cp1252 e não têm a seta
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    alvos_arq = Path(argv[1]) if len(argv) > 1 else AQUI / "alvos.json"
    alvos = json.loads(alvos_arq.read_text(encoding="utf-8"))
    topico = os.environ.get("NTFY_TOPICO", TOPICO_PADRAO).strip()
    estado_arq, hist_arq, check_arq = (AQUI / "estado.json", AQUI / "historico.csv",
                                       AQUI / "ultimo_check.json")
    estado = _ler_json(estado_arq, {})
    agora = datetime.now(timezone.utc).replace(microsecond=0)
    linhas, resultado = [], []

    for alvo in alvos:
        url = alvo["url"]
        nome = alvo.get("nome", url)
        try:
            preco, disp = extrair(baixar(url))
        except Exception as e:  # um alvo com problema não derruba os outros
            erro = f"{type(e).__name__}: {e}"[:300]
            print(f"[ERRO] {nome}: {erro}")
            resultado.append({"nome": nome, "ok": False, "preco": None, "erro": erro})
            continue
        resultado.append({"nome": nome, "ok": True, "preco": preco, "erro": None})
        antes = estado.get(url)
        if antes is None:
            print(f"[1ª leitura] {nome}: {_brl(preco)} ({disp or 'disponibilidade não informada'})")
            linhas.append([_iso(agora), nome, url, "", preco, disp])
        elif antes.get("preco") != preco or antes.get("disponibilidade") != disp:
            print(f"[MUDOU] {nome}: {_brl(antes.get('preco'))} → {_brl(preco)} ({disp})")
            linhas.append([_iso(agora), nome, url, antes.get("preco"), preco, disp])
            if topico and antes.get("preco") != preco:
                try:
                    avisar(topico, nome, url, antes.get("preco"), preco)
                    print(f"  aviso enviado ao tópico {topico}")
                except Exception as e:
                    print(f"  [ERRO] aviso não enviado: {e}")
        else:
            print(f"[igual] {nome}: {_brl(preco)} ({disp})")
        estado[url] = {"nome": nome, "preco": preco, "disponibilidade": disp,
                       "visto_em": _iso(agora)}

    if linhas:
        novo = not hist_arq.exists() or hist_arq.stat().st_size == 0
        with hist_arq.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            if novo:
                w.writerow(CAMPOS_CSV)
            w.writerows(linhas)
    estado_arq.write_text(json.dumps(estado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    check_arq.write_text(json.dumps({"quando": _iso(agora), "alvos": resultado},
                                    ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
