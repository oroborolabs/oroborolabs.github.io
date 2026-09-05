# -*- coding: utf-8 -*-
"""j102 — card og/thumbnail do PRODUTO Starter (E-065 r3, gap medido:
og:image publica = generico assets.gumroad.com/images/opengraph_image.png).
Mesmo visual do og-card.py; rodape aponta a vitrine. 1200x630."""
import pathlib
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG, FG = (16, 20, 24), (232, 236, 240)
ACCENT, MUT = (255, 176, 32), (140, 148, 156)
F_BOLD = ImageFont.truetype("arialbd.ttf", 58)
F_MED = ImageFont.truetype("arialbd.ttf", 34)
F_META = ImageFont.truetype("arial.ttf", 30)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)
d.rectangle([0, 0, 14, H], fill=ACCENT)

def wrap(t, f, maxw):
    linhas, cur = [], ""
    for p in t.split():
        cand = (cur + " " + p).strip()
        if d.textlength(cand, font=f) <= maxw:
            cur = cand
        else:
            linhas.append(cur); cur = p
    if cur: linhas.append(cur)
    return linhas

y = 90
d.text((80, y), "SECOND BRAIN STARTER", font=F_BOLD, fill=FG)
y += 84
d.text((80, y), "Obsidian vault + AI agent, ready to run", font=F_MED, fill=(200, 206, 212))
y += 60
for lin in wrap("Your second brain has two readers: you in Obsidian, and the agent that works for you.", F_META, W - 200):
    d.text((80, y), lin, font=F_META, fill=MUT); y += 40
d.text((80, H - 96), "oroborolabs.gumroad.com  ·  US$ 19  ·  entrega digital", font=F_META, fill=MUT)

out = pathlib.Path(__file__).parent / "img" / "og" / "produto-second-brain-starter.png"
out.parent.mkdir(parents=True, exist_ok=True)
img.save(out, "PNG")
print("card:", out, out.stat().st_size, "bytes")
