import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTCollection

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

W = 846
PAPER = "#F2ECEA"
INK = "#1E1414"
SOFT = "#4A3A3A"
MAROON = "#5A2A2B"
RED = "#C33335"

SERIF = TTCollection("/usr/share/fonts/google-noto-serif-cjk-vf-fonts/NotoSerifCJK-VF.ttc").fonts[0]
MONO = TTCollection("/usr/share/fonts/google-noto-sans-mono-cjk-vf-fonts/NotoSansMonoCJK-VF.ttc").fonts[0]


class Face:
    def __init__(self, font, weight):
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
            self.glyphs[self.cmap[ord(ch)]].draw(TransformPen(pen, (scale, 0, 0, -scale, cx, y)))
            cx += self.advance(ch, size) + tracking
        return pen.getCommands()

    def centered(self, text, size, cx, y, tracking=0.0):
        return self.path(text, size, cx - self.width(text, size, tracking) / 2, y, tracking)


black = Face(SERIF, 900)
serif = Face(SERIF, 500)
label = Face(MONO, 700)
mono = Face(MONO, 500)


def wrap(text, face, size, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and face.width(trial, size) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    lines.append(cur)
    return lines


def balanced(text, face, size, max_w):
    target = len(wrap(text, face, size, max_w))
    lo, hi = 0.0, max_w
    while hi - lo > 1:
        mid = (lo + hi) / 2
        if len(wrap(text, face, size, mid)) <= target:
            hi = mid
        else:
            lo = mid
    return wrap(text, face, size, hi)


def filters(seed):
    return f"""
  <defs>
    <filter id="grain" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.95" numOctaves="2" seed="{seed}" stitchTiles="stitch"/>
      <feColorMatrix type="matrix" values="0 0 0 0 0.2  0 0 0 0 0.12  0 0 0 0 0.12  0 0 0 -1.8 1.1"/>
    </filter>
    <filter id="ink" x="-15%" y="-15%" width="130%" height="130%">
      <feTurbulence type="fractalNoise" baseFrequency="0.05" numOctaves="3" seed="{seed + 2}" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="6" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <filter id="brush" x="-5%" y="-60%" width="110%" height="220%">
      <feTurbulence type="fractalNoise" baseFrequency="0.018 0.35" numOctaves="3" seed="{seed + 5}" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="10" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
  </defs>"""


def sheet(h, body, aria, seed):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-label="{aria}">{filters(seed)}
  <rect width="{W}" height="{h}" rx="16" fill="{PAPER}"/>
  <rect width="{W}" height="{h}" rx="16" filter="url(#grain)" opacity="0.13"/>{body}
  <rect x="0.75" y="0.75" width="{W - 1.5}" height="{h - 1.5}" rx="15.5" fill="none" stroke="{INK}" stroke-opacity="0.14" stroke-width="1.5"/>
</svg>
"""


def hanko(cx, cy, size, glyph, rotate):
    gs = size * (0.58 if len(glyph) == 1 else 0.4)
    d = black.centered(glyph, gs, 0, gs * 0.36)
    inner = size * 0.84
    return f"""
  <g transform="translate({cx},{cy}) rotate({rotate})">
    <g filter="url(#ink)">
      <rect x="{-size / 2}" y="{-size / 2}" width="{size}" height="{size}" rx="{size * 0.1}" fill="{RED}"/>
      <rect x="{-inner / 2}" y="{-inner / 2}" width="{inner}" height="{inner}" rx="{size * 0.06}" fill="none" stroke="{PAPER}" stroke-width="{size * 0.04}"/>
    </g>
    <path d="{d}" fill="{PAPER}"/>
  </g>"""


def tags(items, y, size=13):
    pad, gap, dot = 13, 10, 7
    widths = [label.width(s, size, 0.8) + pad * 2 + dot + 8 for s in items]
    x = 48
    out = []
    for s, tw in zip(items, widths):
        out.append(
            f'<rect x="{x}" y="{y}" width="{tw}" height="32" rx="6" fill="{PAPER}" stroke="{INK}" stroke-opacity="0.55" stroke-width="1.3"/>'
            f'<rect x="{x + pad}" y="{y + 12.5}" width="{dot}" height="{dot}" fill="{RED}"/>'
            f'<path d="{label.path(s, size, x + pad + dot + 8, y + 21, 0.8)}" fill="{INK}"/>'
        )
        x += tw + gap
    return "".join(out)


def hero():
    bio = (
        "Desenvolvedor backend e estudante de Engenharia de Software na PUCPR. "
        "Trabalho principalmente com Node.js e TypeScript. Nos projetos pessoais, "
        "foco em sistemas distribuídos, redes e correção: determinismo, idempotência e testes."
    )
    bio_size, bio_lh = 18, 30
    bio_lines = balanced(bio, serif, bio_size, 470)
    bio_top = 322
    bio_end = bio_top + bio_lh * (len(bio_lines) - 1)
    rule_y = bio_end + 34
    tags_y = rule_y + 22
    h = tags_y + 32 + 40

    bio_paths = "".join(
        f'<path d="{serif.path(l, bio_size, 48, bio_top + i * bio_lh)}" fill="{SOFT}"/>' for i, l in enumerate(bio_lines)
    )
    kanji = "".join(
        f'<path d="{black.centered(ch, 46, 790, 92 + i * 52)}" fill="{RED}"/>' for i, ch in enumerate("七転八起")
    )
    tag_row = tags(["TypeScript", "Node.js", "Go", "Rust", "Zig", "C/C++", "SQL", "Linux"], tags_y)
    ex, ey, er = 650, 178, 92
    body = f"""
  <path d="{label.path("~/gengibrepower", 13, 48, 66, 1.4)}" fill="{RED}"/>
  <path d="{black.path("Felipe", 74, 46, 146)}" fill="{INK}"/>
  <path d="{black.path("Gegembauer", 74, 46, 224)}" fill="{INK}"/>
  <g filter="url(#brush)"><rect x="48" y="242" width="250" height="8" rx="4" fill="{RED}"/></g>
  <path d="{label.path("BACKEND · SISTEMAS DISTRIBUÍDOS · REDES", 14, 48, 284, 1.6)}" fill="{INK}"/>
  {bio_paths}
  <g filter="url(#ink)">
    <circle cx="{ex}" cy="{ey}" r="{er}" fill="none" stroke="{MAROON}" stroke-width="24" stroke-linecap="round"
      stroke-dasharray="{2 * 3.1416 * er * 0.86:.1f} 999" transform="rotate(-60 {ex} {ey})"/>
  </g>
  <circle cx="{ex}" cy="{ey}" r="42" fill="{RED}" filter="url(#ink)"/>
  <g>
    <animateTransform attributeName="transform" type="translate" dur="9s" repeatCount="indefinite"
      values="0 0;0 0;-11 4;-11 4;0 0;0 0;10 -3;10 -3;0 0" keyTimes="0;0.35;0.4;0.52;0.57;0.75;0.8;0.92;1"/>
    <circle cx="{ex}" cy="{ey}" r="17" fill="{INK}"/>
    <circle cx="{ex + 9}" cy="{ey - 9}" r="4.5" fill="{PAPER}"/>
  </g>
  {kanji}
  {hanko(790, 318, 44, "FG", 5)}
  <rect x="48" y="{rule_y}" width="{W - 96}" height="1.2" fill="{INK}" opacity="0.18"/>
  {tag_row}"""
    (OUT / "hero.svg").write_text(sheet(h, body, "Felipe Gegembauer — " + bio, 7))


def divider(kanji, text, filename):
    h = 64
    kw = black.width(kanji, 26)
    tx = 24 + kw + 16
    tw = label.width(text, 14, 2.2)
    lx = tx + tw + 22
    body = f"""
  <path d="{black.path(kanji, 26, 24, 42)}" fill="{RED}"/>
  <path d="{label.path(text, 14, tx, 38, 2.2)}" fill="{INK}"/>
  <g filter="url(#brush)"><rect x="{lx}" y="31" width="{W - lx - 28}" height="3.5" rx="2" fill="{MAROON}" opacity="0.55"/></g>"""
    (OUT / filename).write_text(sheet(h, body, text, len(text) + 3))


def project(numeral, title, tech, desc, filename, seed):
    desc_size, desc_lh = 17, 27
    lines = balanced(desc, serif, desc_size, W - 128 - 34)
    top = 120
    h = top + desc_lh * (len(lines) - 1) + 34
    descs = "".join(
        f'<path d="{serif.path(l, desc_size, 128, top + i * desc_lh)}" fill="{SOFT}"/>' for i, l in enumerate(lines)
    )
    body = f"""
  {hanko(66, 62, 50, numeral, -4)}
  <path d="{black.path(title, 30, 126, 60)}" fill="{INK}"/>
  <path d="{label.path(tech, 12, 128, 84, 1.6)}" fill="{RED}"/>
  <path d="{label.path("↗", 20, W - 52, 52)}" fill="{MAROON}"/>
  {descs}"""
    (OUT / filename).write_text(sheet(h, body, f"{title} — {desc}", seed))


def footer():
    h = 96
    kw = black.width("七転八起", 26)
    btn_label = "LINKEDIN ↗"
    bw = label.width(btn_label, 14, 1.6) + 44
    bx = W - 32 - bw
    body = f"""
  <path d="{black.path("七転八起", 26, 32, 58)}" fill="{RED}"/>
  <path d="{mono.path("cai sete vezes, levanta oito.", 15, 32 + kw + 16, 55, 0.4)}" fill="{SOFT}"/>
  <g filter="url(#ink)"><rect x="{bx}" y="26" width="{bw}" height="44" rx="8" fill="{RED}"/></g>
  <path d="{label.path(btn_label, 14, bx + 22, 53, 1.6)}" fill="{PAPER}"/>"""
    (OUT / "footer.svg").write_text(sheet(h, body, "LinkedIn — 七転八起, cai sete vezes, levanta oito", 5))


hero()
divider("作品", "PROJETOS", "sec-projetos.svg")
project("一", "cross-border-pay", "GO", "Gateway de pagamentos internacionais com ledger de partidas dobradas e idempotência.", "card-cross-border-pay.svg", 21)
project("二", "Exchange", "RUST", "Simulador de exchange com matching determinístico e event sourcing.", "card-exchange.svg", 22)
project("三", "AMPS", "TYPESCRIPT", "Gestão de estacionamentos modelada como um grafo de vagas e vias, com roteamento.", "card-amps.svg", 23)
project("四", "BairdWire", "ZIG · WEBRTC · SVELTE", "Comunicação self-hosted (texto, voz e tela) com SFU próprio e sem servidor central. Em desenvolvimento.", "card-bairdwire.svg", 24)
footer()
print("ok")
