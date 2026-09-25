# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The 64 color tokens and the 64 icons, copied verbatim from badges.

Every color a banner uses is one of these tokens, and every icon is one of
these glyphs, so a README drawn by all three kits reads as one family.
Nothing here is mixed, tinted or invented: a lighter or darker shade is the
same token at a lower opacity, and a color that is not a token is a bug the
lint in `canvas.py` refuses to write.

Both registries are copied from `src/badge-kit.py` in tannergolden/badges,
comments and all, and a test compares them with a badges checkout when one
is present, so they cannot drift apart unnoticed.
"""
from __future__ import annotations

PALETTE = {
    # --- Role anchors (brand-fixed; the doc-style color roles) --------------
    "black": "#000000",   # static label (doc-style: labelColor 000000)
    "gold": "#C0A062",    # dynamic-health label (doc-style: C0A062)
    "green": "#2EA043",   # success / active / healthy
    "pink": "#FE5196",    # roles / community
    "purple": "#9C27B0",  # context / technology
    "yellow": "#F1E05A",  # license / legal / degraded
    "red": "#D73A49",     # security / critical / failing
    "blue": "#3366FF",    # navigation / info
    "violet": "#8B6CFF",  # docs-site accent
    "olive": "#8A8B2C",   # muted score
    "slate": "#57606A",   # neutral / unknown
    "teal": "#1F9E8F",    # metrics
    "orange": "#E36209",  # warning
    "white": "#FFFFFF",
    # --- Extended spectrum (rainbow order; harmonized S/L) ------------------
    "crimson": "#CB2A4A",  # deep red
    "ruby": "#AB2B5A",     # wine red
    "rose": "#E7557C",     # soft red-pink
    "magenta": "#CF3095",  # hot pink-purple
    "fuchsia": "#E147C2",  # bright magenta
    "plum": "#9D47AE",     # muted purple
    "indigo": "#534DCB",   # blue-violet
    "azure": "#3687E2",    # strong blue
    "sky": "#3E9CE0",      # light blue
    "cyan": "#2FADC6",     # blue-green
    "aqua": "#36C9C5",     # bright teal
    "mint": "#4DCBA5",     # light green-teal
    "emerald": "#2BB675",  # rich green
    "lime": "#6FBE37",     # yellow-green
    "amber": "#DFAD3A",    # deep yellow
    "coral": "#EC7051",    # red-orange
    # --- Earth & neutral tones ---------------------------------------------
    "peach": "#EFA980",    # warm light orange
    "sand": "#D0BD8B",     # pale tan
    "tan": "#CAA472",      # warm neutral
    "brown": "#8D5A35",    # earthy brown
    "maroon": "#7E303D",   # deep brownish red
    "navy": "#253D7E",     # deep blue
    "forest": "#22773E",   # deep green
    "lavender": "#AC94E6",  # pale violet
    "steel": "#5B758F",    # blue-grey
    "gray": "#7A8390",     # neutral grey
    # --- Second spectrum: one token per icon, same S/L family --------------
    # Added so the palette and the icon registry are the same size, and so
    # every family has a light, a mid and a deep option rather than one pick.
    # Each was checked against every other token and clears the palette's own
    # minimum spacing (gold vs tan), so no two read as the same color.
    "cherry": "#C32837",    # vivid true red
    "brick": "#A6503A",     # muted red-brown
    "salmon": "#DC796A",    # light warm pink-orange
    "tangerine": "#DD732C", # vivid orange
    "apricot": "#E0A367",   # light orange
    "honey": "#CE8B27",     # deep golden orange
    "mustard": "#B1932F",   # dark yellow
    "ivory": "#ECE3CB",     # warm off-white
    "moss": "#6E883A",      # dark yellow-green
    "sage": "#7AA465",      # muted grey-green
    "jade": "#389F79",      # green with blue in it
    "turquoise": "#2FB1A9", # bright blue-green
    "ocean": "#277C9B",     # deep blue-cyan
    "cobalt": "#2F66C6",    # strong blue
    "denim": "#4977AB",     # muted mid blue
    "iris": "#6C54C9",      # blue-violet
    "amethyst": "#884CBD",  # mid purple
    "mauve": "#A564AF",     # muted purple
    "orchid": "#CE64BC",    # light purple-pink
    "clay": "#A0644B",      # earthy red-brown
    "taupe": "#8E7967",     # warm grey-brown
    "stone": "#A19687",     # pale warm grey
    "ash": "#ABB3BA",       # light cool grey
    "charcoal": "#3A414A",  # near-black neutral
}


ICONS = {
    "pulse": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "shield": '<path d="M12 2l8 3v6c0 5-3.5 8.6-8 10-4.5-1.4-8-5-8-10V5z"/>',
    "book": '<path d="M5 4h11a1 1 0 0 1 1 1v15H6a1 1 0 0 1-1-1z"/><path d="M17 5h2v15h-2"/>',
    "layers": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
    "scale": '<path d="M12 3v18M7 21h10M12 6l-7 2 3 6a3 3 0 0 1-6 0l3-6M12 6l7 2-3 6a3 3 0 0 0 6 0l-3-6"/>',
    "commit": '<circle cx="12" cy="12" r="3.2"/><path d="M3 12h5.8M15.2 12H21"/>',
    "branch": '<circle cx="6" cy="6" r="2.4"/><circle cx="6" cy="18" r="2.4"/><circle cx="18" cy="7" r="2.4"/><path d="M6 8.4v7.2M6 12a6 6 0 0 0 6-6h3.6"/>',
    "check": '<path d="M20 6L9 17l-5-5"/>',
    "check-circle": '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
    "cross": '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
    "gear": '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l1.8 1.8M17.2 17.2L19 19M19 5l-1.8 1.8M6.8 17.2L5 19"/>',
    "star": '<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 17l-5.2 2.6 1-5.8L3.5 9.7l5.9-.9z"/>',
    "grid": '<path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z"/>',
    "arrow": '<path d="M4 12h15M13 6l6 6-6 6"/>',
    "bolt": '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
    "lock": '<rect x="5" y="11" width="14" height="9" rx="1.5"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "search": '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.2-4.2"/>',
    "heart": '<path d="M12 20s-7-4.5-9.5-9C1 8 3 4 6.5 4 9 4 12 7.5 12 7.5S15 4 17.5 4C21 4 23 8 21.5 11c-2.5 4.5-9.5 9-9.5 9z"/>',
    "package": '<path d="M21 8l-9-5-9 5v8l9 5 9-5z"/><path d="M3 8l9 5 9-5M12 13v10"/>',
    "tag": '<path d="M11 3H4v7l10 10 7-7z"/><circle cx="7.5" cy="6.5" r="1.3"/>',
    "download": '<path d="M12 3v12M7 11l5 5 5-5M4 20h16"/>',
    "upload": '<path d="M12 21V9M7 13l5-5 5 5M4 4h16"/>',
    "cloud": '<path d="M7 18a4 4 0 0 1-.5-7.97A5.5 5.5 0 0 1 17 9.5a3.5 3.5 0 0 1 .5 6.98z"/>',
    "terminal": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3M13 15h4"/>',
    "code": '<path d="M8 6l-5 6 5 6M16 6l5 6-5 6"/>',
    "bug": '<rect x="8" y="8" width="8" height="11" rx="4"/><path d="M8 12H3M16 12h5M8 16H4M16 16h4M9 8L7 5M15 8l2-3M12 8V5"/>',
    "flask": '<path d="M9 3h6M10 3v6l-5.2 9.2A2 2 0 0 0 6.5 21h11a2 2 0 0 0 1.7-2.8L14 9V3"/><path d="M7.5 15h9"/>',
    "rocket": '<path d="M5 15c-1.5 1.5-2 6-2 6s4.5-.5 6-2M9 15a10 10 0 0 1 9-12s1 .1 1.9.2c.1.9.1 1.9.1 1.9A10 10 0 0 1 9 15z"/><circle cx="14.5" cy="8.5" r="1.5"/>',
    "flame": '<path d="M12 3s5 4 5 9a5 5 0 0 1-10 0c0-2 1-3.2 1-3.2s.2 1.7 1.6 1.7C13 10.5 12 3 12 3z"/>',
    "eye": '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="2.5"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 9h18M8 3v4M16 3v4"/>',
    "chart": '<path d="M4 4v16h16M8 16v-4M12 16V8M16 16v-7"/>',
    "database": '<ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v12c0 1.66 3.58 3 8 3s8-1.34 8-3V6M4 12c0 1.66 3.58 3 8 3s8-1.34 8-3"/>',
    "key": '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M17 6l3 3M14 9l2 2"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18 14 14 0 0 1 0-18z"/>',
    "users": '<circle cx="9" cy="8" r="3.2"/><path d="M3 20a6 6 0 0 1 12 0M16 5.2a3.2 3.2 0 0 1 0 5.6M18 20a6 6 0 0 0-4-5.6"/>',
    "chat": '<path d="M4 5h16v11H9l-4 4V5z"/><path d="M8 10h8M8 13h5"/>',
    "flag": '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
    "trophy": '<path d="M8 4h8v5a4 4 0 0 1-8 0zM8 6H5a2 2 0 0 0 2 4M16 6h3a2 2 0 0 1-2 4M9 21h6M12 15v3M10 15h4"/>',
    "sparkle": '<path d="M12 3l2.2 6.8L21 12l-6.8 2.2L12 21l-2.2-6.8L3 12l6.8-2.2z"/>',
    "medal": '<circle cx="12" cy="10" r="5"/><path d="M9 14l-2 7 5-3 5 3-2-7"/>',
    "chip": '<rect x="7" y="7" width="10" height="10" rx="1.5"/><path d="M10 2v3M14 2v3M10 19v3M14 19v3M2 10h3M2 14h3M19 10h3M19 14h3"/>',
    "link": '<path d="M9 15l6-6M8.5 11l-2 2a3 3 0 0 0 4 4l2-2M15.5 13l2-2a3 3 0 0 0-4-4l-2 2"/>',
    "folder": '<path d="M3 6a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/>',
    "sync": '<path d="M4 12a8 8 0 0 1 13.9-5.4L20 9M20 12a8 8 0 0 1-13.9 5.4L4 15M17 4v5h-5M7 20v-5h5"/>',
    "alert": '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18h.01"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    "play": '<path d="M7 4l13 8-13 8z"/>',
    "home": '<path d="M4 11l8-7 8 7M6 9.5V20h12V9.5M10 20v-6h4v6"/>',
    "server": '<rect x="3" y="4" width="18" height="7" rx="1.5"/><rect x="3" y="13" width="18" height="7" rx="1.5"/><path d="M7 7.5h.01M7 16.5h.01"/>',
    "bell": '<path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6"/><path d="M10 19a2.2 2.2 0 0 0 4 0"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="1.5"/><path d="M3 7l9 6 9-6"/>',
    "pin": '<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2"/>',
    "compass": '<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/>',
    "wrench": '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    "trash": '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/><path d="M10 11v6M14 11v6"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "minus": '<path d="M5 12h14"/>',
    "question": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.8 2.1c-.8.5-1.3 1-1.3 1.9v.5"/><path d="M12 17h.01"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/>',
    "moon": '<path d="M20 14.5A8 8 0 1 1 9.5 4 6.5 6.5 0 0 0 20 14.5z"/>',
    "infinity": '<path d="M7 9c-4 0-4 6 0 6 4 0 6-6 10-6 4 0 4 6 0 6-4 0-6-6-10-6z"/>',
}


# Uppercase, so the lint can compare what a file says with what a token is.
HEXES = frozenset(v.upper() for v in PALETTE.values())


def hexof(token: str) -> str:
    """The hex a token stands for. An unknown token is a design bug, so it raises."""
    return PALETTE[token]
