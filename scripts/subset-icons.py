#!/usr/bin/env python3
"""Builds the Material Symbols subset the pages serve.

    scripts/subset-icons.py FULL.woff2 src/assets/fonts/material-symbols-icons.txt OUT.woff2

FULL.woff2 is the variable font Google Fonts serves for
`family=Material+Symbols+Outlined:wght,FILL@100..700,0..1` (axes FILL and
wght). The subset keeps exactly the icons named in the list, as ligatures
(`<span class="icon">badge</span>`), with both axes. Needs fontTools and
brotli (`python3 -m pip install fonttools brotli`). It checks the result:
every listed name is there and no icon beyond those (and their aliases).
"""
import sys

from fontTools import subset
from fontTools.ttLib import TTFont


def ligatures(font):
    """name -> ligature glyph, for every icon the font spells by ligature."""
    cmap = font.getBestCmap()
    letters = {glyph: chr(code) for code, glyph in cmap.items()}
    found = {}
    for lookup in font["GSUB"].table.LookupList.Lookup:
        for table in lookup.SubTable:
            table = getattr(table, "ExtSubTable", table)
            for first, ligs in getattr(table, "ligatures", {}).items():
                for lig in ligs:
                    parts = [first, *lig.Component]
                    if all(part in letters for part in parts):
                        found["".join(letters[part] for part in parts)] = lig.LigGlyph
    return found


def main(full, names_file, out):
    names = sorted({line.strip() for line in open(names_file) if line.strip() and not line.startswith("#")})
    font = TTFont(full)
    available = ligatures(font)
    missing = [name for name in names if name not in available]
    if missing:
        sys.exit(f"not in the font: {missing}")
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_closure = False  # keep only the listed ligatures, not every icon the letters could spell
    options.layout_features = ["rlig", "rclt", "liga", "calt"]
    options.name_IDs = [1, 2, 3, 4, 6]
    options.notdef_outline = True
    options.hinting = False
    subsetter = subset.Subsetter(options)
    letters = sorted({ord(char) for name in names for char in name})
    subsetter.populate(unicodes=letters, glyphs=[available[name] for name in names])
    subsetter.subset(font)
    subset.save_font(font, out, options)
    kept = TTFont(out)
    got = ligatures(kept)
    lost = [name for name in names if name not in got]
    # The font spells some icons by several names (`error_outline` is
    # `error`); an alias costs nothing, but a different glyph would.
    shapes = len(set(got.values()))
    wanted = len({available[name] for name in names})
    if lost or shapes != wanted:
        sys.exit(f"subset lost {lost} or has {shapes} icon shapes, expected {wanted}")
    axes = [(a.axisTag, a.minValue, a.maxValue) for a in kept["fvar"].axes]
    print(f"{len(names)} names, {shapes} icon shapes, axes {axes}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
