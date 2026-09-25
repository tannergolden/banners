# The preview page runs this under Brython once the page has painted.
# It hands the kit the same two glyph tables the kit reads from disk, and
# gives the page one function: the kit's own answer to "draw these".
import json

from browser import window

from bannerkit import live, text

base, extra = window.KIT_FONTS
text.use(json.loads(base), json.loads(extra))
window.kitAnswer = live.answer_json
