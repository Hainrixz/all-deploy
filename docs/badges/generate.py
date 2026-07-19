#!/usr/bin/env python3
"""Generate self-contained flat badge SVGs in the project's brand palette.

Written because shields.io is an external dependency that intermittently times
out; when it does, the README shows a broken image. These badges are committed
to the repo and served from github.com like every other asset here.

Palette is the mascot's own four colours. The message segment deliberately uses
black-on-coral — the same pairing as the mascot's eyes on its body — which also
happens to be far more legible than the usual white-on-colour (6.8:1 vs 3.1:1).
"""
import sys

# Verdana advance widths, units per 1000 em. Verdana is the font shields.io
# uses and is metrically what browsers land on for this stack; anything close
# is fine because the text is centred inside a padded segment.
W = {
    ' ': 351, '!': 394, '"': 460, '#': 818, '$': 636, '%': 1076, '&': 726,
    "'": 268, '(': 454, ')': 454, '*': 636, '+': 818, ',': 318, '-': 411,
    '.': 318, '/': 454, ':': 454, ';': 454, '<': 818, '=': 818, '>': 818,
    '?': 545, '@': 1000, '[': 454, ']': 454, '_': 636, '`': 636,
    'A': 683, 'B': 685, 'C': 698, 'D': 770, 'E': 632, 'F': 575, 'G': 775,
    'H': 751, 'I': 421, 'J': 455, 'K': 693, 'L': 557, 'M': 843, 'N': 748,
    'O': 787, 'P': 603, 'Q': 787, 'R': 695, 'S': 684, 'T': 616, 'U': 732,
    'V': 683, 'W': 989, 'X': 685, 'Y': 613, 'Z': 685,
    'a': 600, 'b': 623, 'c': 521, 'd': 623, 'e': 596, 'f': 351, 'g': 623,
    'h': 633, 'i': 274, 'j': 344, 'k': 591, 'l': 274, 'm': 973, 'n': 633,
    'o': 607, 'p': 623, 'q': 623, 'r': 427, 's': 521, 't': 394, 'u': 633,
    'v': 592, 'w': 818, 'x': 592, 'y': 592, 'z': 525,
    '0': 636, '1': 636, '2': 636, '3': 636, '4': 636, '5': 636, '6': 636,
    '7': 636, '8': 636, '9': 636,
}
FONT_PX = 11
PAD = 7          # horizontal padding inside each segment
HEIGHT = 20
RADIUS = 3

CREAM = '#F2F3EE'   # mascot background
CORAL = '#DA7758'   # mascot body
INK = '#000000'     # mascot eyes
SLATE = '#3D3733'   # warm dark for the label segment


def text_width(s):
    return sum(W.get(c, 636) for c in s) * FONT_PX / 1000.0


def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
             .replace('"', '&quot;'))


def badge(label, message, message_bg=CORAL, message_fg=INK):
    lw = round(text_width(label) + PAD * 2)
    mw = round(text_width(message) + PAD * 2)
    total = lw + mw
    # Coordinates are doubled and scaled down 10x so text lands on crisp
    # half-pixel positions, the same trick shields.io uses.
    lx = lw * 10 / 2
    mx = (lw + mw / 2) * 10
    alt = f'{label}: {message}'
    # An SVG used as an image cannot load a webfont, so the text renders in
    # whatever the *viewer* has installed. Segment widths here are computed
    # from Verdana metrics, so a wider fallback (Courier, say) overflows the
    # pill. textLength pins each run to the width we reserved for it, which
    # makes the badge render correctly regardless of the font that resolves.
    ltl = round(text_width(label) * 10)
    mtl = round(text_width(message) * 10)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total}" \
height="{HEIGHT}" role="img" aria-label="{esc(alt)}">
  <title>{esc(alt)}</title>
  <clipPath id="r">
    <rect width="{total}" height="{HEIGHT}" rx="{RADIUS}" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{lw}" height="{HEIGHT}" fill="{SLATE}"/>
    <rect x="{lw}" width="{mw}" height="{HEIGHT}" fill="{message_bg}"/>
  </g>
  <g fill="{CREAM}" text-anchor="middle" \
font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="110" \
transform="scale(.1)">
    <text x="{lx:.0f}" y="140" textLength="{ltl}" \
lengthAdjust="spacingAndGlyphs">{esc(label)}</text>
  </g>
  <g fill="{message_fg}" text-anchor="middle" \
font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="110" \
font-weight="bold" transform="scale(.1)">
    <text x="{mx:.0f}" y="140" textLength="{mtl}" \
lengthAdjust="spacingAndGlyphs">{esc(message)}</text>
  </g>
</svg>
'''


def contrast(hex1, hex2):
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
             for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    a, b = sorted((lum(hex1), lum(hex2)), reverse=True)
    return (a + 0.05) / (b + 0.05)


BADGES = [
    ('license', 'MIT', 'docs/badges/license.svg'),
    ('Claude Code', 'skill', 'docs/badges/claude-code-skill.svg'),
]

if __name__ == '__main__':
    print(f'contrast  cream on slate : {contrast(CREAM, SLATE):.2f}:1')
    print(f'contrast  ink   on coral : {contrast(INK, CORAL):.2f}:1')
    print()
    for label, message, path in BADGES:
        svg = badge(label, message)
        open(path, 'w').write(svg)
        print(f'{path}  ({len(svg)}B)  "{label}" | "{message}"')
