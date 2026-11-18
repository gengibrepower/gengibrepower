import math
import random
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTCollection

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

W = 846
PAPER = "#EFE9E7"
INK = "#1A1212"
SOFT = "#3A2C2C"
MAROON = "#5A2226"
RED = "#CF3236"
TAPE = "#E8DCC4"

SERIF = TTCollection("/usr/share/fonts/google-noto-serif-cjk-vf-fonts/NotoSerifCJK-VF.ttc").fonts[0]
SANS = TTCollection("/usr/share/fonts/google-noto-sans-cjk-vf-fonts/NotoSansCJK-VF.ttc").fonts[0]
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
brush = Face(SANS, 900)
type_ = Face(MONO, 500)
type_bold = Face(MONO, 700)


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


def torn(x0, y0, x1, y1, rng, amp=4.0, step=(5, 11), side_amp=1.6):
    pts = []
    x = x0
    while x < x1:
        pts.append((x, y0 + rng.uniform(-amp, amp)))
        x += rng.uniform(*step)
    y = y0
    while y < y1:
        pts.append((x1 + rng.uniform(-side_amp, side_amp), y))
        y += rng.uniform(*step)
    x = x1
    while x > x0:
        pts.append((x, y1 + rng.uniform(-amp, amp)))
        x -= rng.uniform(*step)
    y = y1
    while y > y0:
        pts.append((x0 + rng.uniform(-side_amp, side_amp), y))
        y -= rng.uniform(*step)
    return "M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in pts) + " Z"


def speckles(x0, y0, x1, y1, rng, n):
    out = []
    for _ in range(n):
        out.append(
            f'<circle cx="{rng.uniform(x0, x1):.1f}" cy="{rng.uniform(y0, y1):.1f}" r="{rng.uniform(0.3, 0.9):.2f}" fill="{INK}" opacity="{rng.uniform(0.12, 0.35):.2f}"/>'
        )
    return "".join(out)


def tape(cx, cy, w, h, angle):
    return (
        f'<g transform="translate({cx},{cy}) rotate({angle})">'
        f'<rect x="{-w / 2}" y="{-h / 2}" width="{w}" height="{h}" fill="{TAPE}" opacity="0.72" filter="url(#rough)"/>'
        f'<rect x="{-w / 2}" y="{-h / 2}" width="{w}" height="{h}" filter="url(#grain)" opacity="0.25"/>'
        f"</g>"
    )


def halftone(cx, cy, r, rng, color, spacing=7.0, power=0.8):
    dots = []
    n = int(r / spacing) + 1
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            x = cx + i * spacing + (j % 2) * spacing / 2
            y = cy + j * spacing * 0.87
            d = math.hypot(x - cx, y - cy)
            if d > r:
                continue
            t = 1 - d / r
            dr = spacing * 0.56 * (t**power) + rng.uniform(-0.25, 0.25)
            if dr > 0.35:
                dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{dr:.2f}"/>')
    return f'<g fill="{color}">{"".join(dots)}</g>'


def defs(seed):
    return f"""
  <defs>
    <filter id="grain" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="1.1" numOctaves="2" seed="{seed}" stitchTiles="stitch"/>
      <feColorMatrix type="matrix" values="0 0 0 0 0.12  0 0 0 0 0.06  0 0 0 0 0.06  0 0 0 -2.2 1.25"/>
    </filter>
    <filter id="rough" x="-10%" y="-10%" width="120%" height="120%">
      <feTurbulence type="fractalNoise" baseFrequency="0.06" numOctaves="3" seed="{seed + 3}" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="5" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <filter id="bleed" x="-10%" y="-10%" width="120%" height="120%">
      <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="1" seed="{seed + 7}" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="2.2" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <filter id="stroke" x="-5%" y="-80%" width="110%" height="260%">
      <feTurbulence type="fractalNoise" baseFrequency="0.015 0.4" numOctaves="3" seed="{seed + 5}" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="11" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <filter id="shadow" x="-5%" y="-10%" width="110%" height="130%">
      <feDropShadow dx="0" dy="3" stdDeviation="3" flood-color="#000" flood-opacity="0.35"/>
    </filter>
  </defs>"""


def piece(w, h, angle, rng, seed):
    path = torn(10, 10, w - 10, h - 10, rng)
    return path, f"rotate({angle} {w / 2} {h / 2})"


def doc(h, body, aria, seed):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-label="{aria}">{defs(seed)}
{body}
</svg>
"""


def paper(h, angle, rng, seed, content, extra_top=""):
    edge, rot = piece(W, h, angle, rng, seed)
    clip = f"clip{seed}"
    return f"""
  <clipPath id="{clip}"><path d="{edge}"/></clipPath>
  <g transform="{rot}">
    <path d="{edge}" fill="{PAPER}" filter="url(#shadow)"/>
    <g clip-path="url(#{clip})">
      <rect width="{W}" height="{h}" filter="url(#grain)" opacity="0.3"/>
      {speckles(10, 10, W - 10, h - 10, rng, 55)}
      {content}
    </g>
    {extra_top}
  </g>"""


def misreg(d, color_front, color_back, dx=2.6, dy=1.8, filt="bleed"):
    return (
        f'<path d="{d}" fill="{color_back}" transform="translate({dx},{dy})" opacity="0.85" filter="url(#{filt})"/>'
        f'<path d="{d}" fill="{color_front}" filter="url(#{filt})"/>'
    )


def stamp(cx, cy, text, size, angle, color=RED):
    tw = type_bold.width(text, size, size * 0.18)
    w, h = tw + size * 1.6, size * 2.1
    d = type_bold.path(text, size, -tw / 2, size * 0.36, size * 0.18)
    return f"""
  <g transform="translate({cx},{cy}) rotate({angle})" opacity="0.9" filter="url(#rough)">
    <rect x="{-w / 2}" y="{-h / 2}" width="{w}" height="{h}" rx="3" fill="none" stroke="{color}" stroke-width="{size * 0.16}"/>
    <path d="{d}" fill="{color}"/>
  </g>"""


def hero():
    rng = random.Random(7)
    bio = "Dev backend e estudante de Engenharia de Software na PUCPR. Trabalho com Node.js e TypeScript e, nos projetos pessoais, mexo com sistemas distribuídos e redes."
    bio_lines = balanced(bio, serif, 19, 440)
    bio_top = 330
    bio_paths = "".join(
        f'<path d="{serif.path(l, 19, 52, bio_top + i * 31)}" fill="{SOFT}"/>' for i, l in enumerate(bio_lines)
    )
    stack_y = bio_top + 31 * (len(bio_lines) - 1) + 54
    stack = "typescript  node  go  rust  zig  c  sql  linux"
    h = stack_y + 56
    ex, ey, er = 640, 176, 128
    kanji = "".join(misreg(brush.centered(ch, 60, 784, 102 + i * 70), RED, MAROON, 3, 2) for i, ch in enumerate("七転八起"))
    content = f"""
      {halftone(ex, ey, er, rng, RED)}
      <circle cx="{ex}" cy="{ey}" r="52" fill="{MAROON}" filter="url(#rough)" opacity="0.95"/>
      <g>
        <animateTransform attributeName="transform" type="translate" dur="9s" repeatCount="indefinite"
          values="0 0;0 0;-12 5;-12 5;0 0;0 0;11 -4;11 -4;0 0" keyTimes="0;0.35;0.4;0.52;0.57;0.75;0.8;0.92;1"/>
        <circle cx="{ex}" cy="{ey}" r="26" fill="{INK}" filter="url(#rough)"/>
        <circle cx="{ex + 11}" cy="{ey - 11}" r="6" fill="{PAPER}"/>
      </g>
      {kanji}
      <path d="{type_bold.path("~/gengibrepower", 14, 52, 70, 1.2)}" fill="{RED}"/>
      {misreg(black.path("Felipe", 76, 48, 150), INK, RED, 2.2, 1.4)}
      {misreg(black.path("Gegembauer", 76, 48, 230), INK, RED, 2.2, 1.4)}
      <g filter="url(#stroke)"><rect x="50" y="250" width="270" height="10" rx="5" fill="{RED}"/></g>
      <path d="{type_bold.path("backend / sistemas distribuídos / redes", 15, 52, 296, 0.6)}" fill="{INK}"/>
      {bio_paths}
      <path d="{type_bold.path("stack:", 15, 52, stack_y, 0.6)}" fill="{RED}"/>
      <path d="{type_.path(stack, 15, 52 + type_bold.width("stack: ", 15, 0.6), stack_y, 0.6)}" fill="{INK}"/>"""
    extra = tape(120, 14, 110, 26, -6) + tape(W - 130, 16, 96, 24, 7) + stamp(760, h - 64, "FG", 22, -8)
    body = paper(h, -0.6, rng, 7, content, extra)
    (OUT / "hero.svg").write_text(doc(h, body, "Felipe Gegembauer — " + bio, 7))


def label_strip(kanji, text, filename, seed):
    rng = random.Random(seed)
    h = 74
    tw = type_bold.width(text, 17, 3)
    kw = brush.width(kanji, 30)
    sw = 40 + kw + 16 + tw + 40
    edge = torn(14, 14, 14 + sw, h - 14, rng, amp=2.5)
    body = f"""
  <g transform="rotate(-1.5 {sw / 2} {h / 2})">
    <path d="{edge}" fill="{RED}" filter="url(#shadow)"/>
    <clipPath id="c{seed}"><path d="{edge}"/></clipPath>
    <g clip-path="url(#c{seed})"><rect width="{W}" height="{h}" filter="url(#grain)" opacity="0.35"/></g>
    <path d="{brush.path(kanji, 30, 54, 49)}" fill="{PAPER}" filter="url(#bleed)"/>
    <path d="{type_bold.path(text, 17, 54 + kw + 16, 46, 3)}" fill="{PAPER}"/>
  </g>"""
    (OUT / filename).write_text(doc(h, body, text, seed))


def project(numeral, title, tech, desc, filename, seed, angle, wip=False):
    rng = random.Random(seed)
    lines = balanced(desc, serif, 18, W - 150 - 56)
    top = 122
    h = top + 29 * (len(lines) - 1) + 44
    descs = "".join(f'<path d="{serif.path(l, 18, 150, top + i * 29)}" fill="{SOFT}"/>' for i, l in enumerate(lines))
    content = f"""
      {misreg(brush.centered(numeral, 62, 86, 104), RED, MAROON, 2.5, 2)}
      {misreg(black.path(title, 34, 148, 70), INK, RED, 1.6, 1)}
      <path d="{type_bold.path(tech, 14, 150, 94, 1.2)}" fill="{RED}"/>
      {descs}"""
    extra = tape(W / 2 + rng.uniform(-120, 120), 14, 92, 22, rng.uniform(-8, 8))
    if wip:
        extra += stamp(W - 150, 66, "EM CONSTRUÇÃO", 15, -7)
    body = paper(h, angle, rng, seed, content, extra)
    (OUT / filename).write_text(doc(h, body, f"{title} — {desc}", seed))


def footer():
    rng = random.Random(5)
    h = 120
    kw = brush.width("七転八起", 34)
    content = f"""
      {misreg(brush.path("七転八起", 34, 44, 72), RED, MAROON, 2.4, 1.8)}
      <path d="{type_.path("cai sete vezes, levanta oito.", 16, 44 + kw + 20, 68, 0.4)}" fill="{INK}"/>"""
    extra = stamp(W - 140, h / 2, "LINKEDIN", 18, 6) + tape(70, 14, 80, 22, -10)
    body = paper(h, 0.5, rng, 5, content, extra)
    (OUT / "footer.svg").write_text(doc(h, body, "LinkedIn — 七転八起, cai sete vezes, levanta oito", 5))


hero()
label_strip("作品", "PROJETOS", "sec-projetos.svg", 41)
project("一", "cross-border-pay", "GO", "Gateway de pagamentos internacionais, com ledger de partidas dobradas e idempotência.", "card-cross-border-pay.svg", 21, 0.5)
project("二", "Exchange", "RUST", "Simulador de exchange com matching determinístico e event sourcing.", "card-exchange.svg", 22, -0.7)
project("三", "AMPS", "TYPESCRIPT", "Estacionamento modelado como grafo de vagas e vias, com roteamento.", "card-amps.svg", 23, 0.4)
project("四", "BairdWire", "ZIG · WEBRTC · SVELTE", "Um Discord sem dono: cada comunidade roda o próprio servidor.", "card-bairdwire.svg", 24, -0.5, wip=True)
footer()
print("ok")
