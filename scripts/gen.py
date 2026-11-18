import math
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTCollection

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

PAPER = "#ECE5E4"
INK = "#291C1C"
MAROON = "#5A2A2B"
RED = "#C83A3C"
ROSE = "#D7A2A3"

SERIF = TTCollection("/usr/share/fonts/google-noto-serif-cjk-vf-fonts/NotoSerifCJK-VF.ttc").fonts[0]
MONO = TTCollection("/usr/share/fonts/google-noto-sans-mono-cjk-vf-fonts/NotoSansMonoCJK-VF.ttc").fonts[0]


class Face:
    def __init__(self, font, weight):
        self.font = font
        self.glyphs = font.getGlyphSet(location={"wght": weight})
        self.cmap = font.getBestCmap()
        self.upem = font["head"].unitsPerEm
        self.hmtx = font["hmtx"]

    def advance(self, ch, size):
        return self.hmtx[self.cmap[ord(ch)]][0] * size / self.upem

    def width(self, text, size, tracking=0.0):
        return sum(self.advance(c, size) + tracking for c in text) - tracking

    def path(self, text, size, x, y, tracking=0.0):
        pen = SVGPathPen(self.glyphs)
        scale = size / self.upem
        cx = x
        for ch in text:
            name = self.cmap[ord(ch)]
            self.glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, cx, y)))
            cx += self.advance(ch, size) + tracking
        return pen.getCommands()

    def vpath(self, text, size, x, y, gap=1.0):
        pen = SVGPathPen(self.glyphs)
        scale = size / self.upem
        cy = y
        for ch in text:
            name = self.cmap[ord(ch)]
            w = self.advance(ch, size)
            self.glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x - w / 2, cy)))
            cy += size * gap
        return pen.getCommands()


serif_black = Face(SERIF, 900)
serif_bold = Face(SERIF, 700)
mono = Face(MONO, 400)
mono_bold = Face(MONO, 700)


def defs(w, h, seed=7, animate=True):
    flicker = (
        f'<animate attributeName="seed" values="{seed};{seed + 4};{seed + 9};{seed + 13}" dur="0.6s" repeatCount="indefinite" calcMode="discrete"/>'
        if animate
        else ""
    )
    return f"""
  <defs>
    <filter id="grain" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="{seed}" stitchTiles="stitch">{flicker}</feTurbulence>
      <feColorMatrix type="matrix" values="0 0 0 0 0.16  0 0 0 0 0.10  0 0 0 0 0.10  0 0 0 -1.6 1.05"/>
    </filter>
    <filter id="ink" x="-10%" y="-10%" width="120%" height="120%">
      <feTurbulence type="fractalNoise" baseFrequency="0.045" numOctaves="3" seed="{seed + 2}" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="7" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <filter id="brush" x="-10%" y="-30%" width="120%" height="160%">
      <feTurbulence type="fractalNoise" baseFrequency="0.02 0.3" numOctaves="3" seed="{seed + 5}" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="12" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <pattern id="seigaiha" width="40" height="20" patternUnits="userSpaceOnUse">
      {seigaiha_tile()}
    </pattern>
  </defs>"""


def seigaiha_tile():
    arcs = []
    for cx, cy in ((0, 20), (40, 20), (20, 10), (0, 0), (40, 0)):
        for r in (19, 14, 9, 4):
            arcs.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{RED}" stroke-width="1.1"/>')
    return "".join(arcs)


def grain_layer(w, h, opacity=0.5):
    return f'<rect width="{w}" height="{h}" filter="url(#grain)" opacity="{opacity}"/>'


def hanko(x, y, size, text_path_d, rotate=-4):
    return f"""
  <g transform="translate({x},{y}) rotate({rotate})" filter="url(#ink)">
    <rect x="{-size / 2}" y="{-size / 2}" width="{size}" height="{size}" rx="{size * 0.08}" fill="{RED}"/>
    <rect x="{-size / 2 + size * 0.08}" y="{-size / 2 + size * 0.08}" width="{size * 0.84}" height="{size * 0.84}" rx="{size * 0.05}" fill="none" stroke="{PAPER}" stroke-width="{size * 0.035}"/>
    <path d="{text_path_d}" fill="{PAPER}"/>
  </g>"""


def svg(w, h, body, label, seed=7, animate=True, kanji_css=""):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{label}">{defs(w, h, seed, animate)}
  <style>{kanji_css}</style>
  <rect width="{w}" height="{h}" rx="14" fill="{PAPER}"/>
  <g clip-path="inset(0 round 14px)">{body}
  {grain_layer(w, h)}
  </g>
</svg>
"""


def banner():
    w, h = 1000, 360
    first = serif_black.path("Felipe", 84, 56, 168)
    last = serif_black.path("Gegembauer", 84, 56, 254)
    handle = mono_bold.path("~/gengibrepower", 15, 60, 70, tracking=1.2)
    sub = mono.path("backend · sistemas distribuídos · redes", 17, 60, 320, tracking=0.4)
    kanji = [serif_black.vpath(ch, 56, 930, 84 + i * 60) for i, ch in enumerate("七転八起")]
    kanji_g = "".join(
        f'<path d="{d}" fill="{RED}"/>'
        for i, d in enumerate(kanji)
    )
    seal_text = serif_black.path("FG", 30, 0, 0)
    seal_w = serif_black.width("FG", 30)
    seal_text = serif_black.path("FG", 30, -seal_w / 2, 11)
    caption = mono.path("cai sete vezes, levanta oito", 12, 735 - mono.width("cai sete vezes, levanta oito", 12, 0.6) / 2, 336, tracking=0.6)
    body = f"""
  <rect x="0" y="{h - 78}" width="{w}" height="78" fill="url(#seigaiha)" opacity="0.16"/>
  <rect x="0" y="{h - 78}" width="{w}" height="2" fill="{RED}" opacity="0.25"/>
  <g filter="url(#ink)" opacity="0.92">
    <circle cx="735" cy="160" r="104" fill="none" stroke="{MAROON}" stroke-width="30" stroke-linecap="round"
      stroke-dasharray="565 89" transform="rotate(-62 735 160)" opacity="0.88"/>
  </g>
  <circle cx="735" cy="160" r="48" fill="{RED}" opacity="0.9" filter="url(#ink)"/>
  <g>
    <animateTransform attributeName="transform" type="translate" dur="9s" repeatCount="indefinite"
      values="0 0;0 0;-13 4;-13 4;0 0;0 0;11 -3;11 -3;0 0" keyTimes="0;0.35;0.4;0.52;0.57;0.75;0.8;0.92;1"/>
    <circle cx="735" cy="160" r="20" fill="{INK}" opacity="0.85"/>
    <circle cx="746" cy="149" r="5.5" fill="{PAPER}" opacity="0.9"/>
  </g>
  {kanji_g}
  <path d="{handle}" fill="{RED}"/>
  <path d="{first}" fill="{INK}"/>
  <path d="{last}" fill="{INK}"/>
  <g filter="url(#brush)">
    <rect x="58" y="276" width="300" height="9" rx="4" fill="{RED}"/>
  </g>
  <path d="{sub}" fill="{MAROON}"/>
  <path d="{caption}" fill="{MAROON}" opacity="0.8"/>
  {hanko(930, 318, 46, seal_text)}"""
    (OUT / "banner.svg").write_text(svg(w, h, body, "Felipe Gegembauer — backend, sistemas distribuídos e redes", seed=7))


def section(name, kanji, filename):
    w, h = 1000, 64
    k = serif_black.path(kanji, 30, 24, 43)
    kw = serif_black.width(kanji, 30)
    t = mono_bold.path(name, 16, 24 + kw + 18, 40, tracking=2.0)
    tw = mono_bold.width(name, 16, 2.0)
    line_x = 24 + kw + 18 + tw + 20
    body = f"""
  <path d="{k}" fill="{RED}"/>
  <path d="{t}" fill="{INK}"/>
  <g filter="url(#brush)"><rect x="{line_x}" y="31" width="{w - line_x - 24}" height="4" rx="2" fill="{MAROON}" opacity="0.7"/></g>"""
    (OUT / filename).write_text(svg(w, h, body, name, seed=len(name), animate=False))


def stack():
    items = ["TypeScript", "Node.js", "Go", "Rust", "Zig", "C/C++", "SQL", "Linux"]
    size, pad, gap = 15, 16, 12
    widths = [mono_bold.width(s, size, 0.6) + pad * 2 + 14 for s in items]
    total = sum(widths) + gap * (len(items) - 1)
    w, h = 1000, 70
    x = (w - total) / 2
    parts = []
    for s, tw in zip(items, widths):
        d = mono_bold.path(s, size, x + pad + 14, 41, tracking=0.6)
        parts.append(
            f'<rect x="{x}" y="17" width="{tw}" height="36" rx="4" fill="none" stroke="{INK}" stroke-width="1.6"/>'
            f'<rect x="{x + pad - 2}" y="31" width="8" height="8" fill="{RED}"/>'
            f'<path d="{d}" fill="{INK}"/>'
        )
        x += tw + gap
    (OUT / "stack.svg").write_text(svg(w, h, "".join(parts), "Stack: " + ", ".join(items), seed=11, animate=False))


def wrap(text, face, size, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if face.width(trial, size) > max_w and cur:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    lines.append(cur)
    return lines


def card(idx_kanji, title, tech, desc, filename, seed):
    w, h = 490, 190
    t = serif_black.path(title, 30, 34, 58)
    k = mono_bold.path(tech, 13, 36, 86, tracking=1.0)
    lines = wrap(desc, mono, 14, w - 70 - 70)
    descs = "".join(f'<path d="{mono.path(l, 14, 36, 120 + i * 22)}" fill="{MAROON}"/>' for i, l in enumerate(lines))
    kw = serif_black.width(idx_kanji, 26)
    seal = serif_black.path(idx_kanji, 26, -kw / 2, 10)
    body = f"""
  <rect x="{w - 150}" y="{h - 46}" width="150" height="46" fill="url(#seigaiha)" opacity="0.14"/>
  <g filter="url(#brush)"><rect x="16" y="26" width="6" height="{h - 52}" rx="3" fill="{RED}"/></g>
  <path d="{t}" fill="{INK}"/>
  <path d="{k}" fill="{RED}"/>
  {descs}
  {hanko(w - 46, 46, 44, seal, rotate=5)}
  <rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="13" fill="none" stroke="{INK}" stroke-opacity="0.18" stroke-width="2"/>"""
    (OUT / filename).write_text(svg(w, h, body, f"{title} — {desc}", seed=seed, animate=False))


def button(label, filename):
    size = 15
    tw = mono_bold.width(label, size, 1.0)
    w, h = int(tw + 64), 46
    d = mono_bold.path(label, size, 32, 29, tracking=1.0)
    body = f"""
  <g filter="url(#ink)"><rect x="6" y="6" width="{w - 12}" height="{h - 12}" rx="5" fill="{RED}"/></g>
  <path d="{d}" fill="{PAPER}"/>"""
    (OUT / filename).write_text(svg(w, h, body, label, seed=3, animate=False))


def footer():
    w, h = 1000, 70
    k = serif_black.path("七転八起", 22, 24, 44)
    kw = serif_black.width("七転八起", 22)
    t = mono.path("cai sete vezes, levanta oito.", 14, 24 + kw + 16, 42, tracking=0.6)
    body = f"""
  <path d="{k}" fill="{RED}"/>
  <path d="{t}" fill="{MAROON}"/>"""
    (OUT / "footer.svg").write_text(svg(w, h, body, "七転八起 — cai sete vezes, levanta oito", seed=5, animate=False))


banner()
section("STACK", "技術", "sec-stack.svg")
section("PROJETOS", "作品", "sec-projetos.svg")
section("CONTATO", "連絡", "sec-contato.svg")
stack()
card("一", "cross-border-pay", "GO", "Gateway de pagamentos internacionais com ledger de partidas dobradas e idempotência.", "card-cross-border-pay.svg", 21)
card("二", "Exchange", "RUST", "Simulador de exchange com matching determinístico e event sourcing.", "card-exchange.svg", 22)
card("三", "AMPS", "TYPESCRIPT", "Gestão de estacionamentos modelada como grafo de vagas e vias, com roteamento.", "card-amps.svg", 23)
card("四", "BairdWire", "ZIG · WEBRTC · SVELTE", "Comunicação self-hosted (texto, voz e tela) com SFU próprio e sem servidor central. Em desenvolvimento.", "card-bairdwire.svg", 24)
button("LINKEDIN ↗", "btn-linkedin.svg")
footer()
print("ok")
