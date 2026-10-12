"""Fixed transparent palettes selected by GitHub's README theme links."""

from pathlib import Path
import sys
from xml.dom import minidom
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
PALETTES = {
    "light": ("#24292f", "#57606a", "#0366d6", "#d8dee4", "#e5e7eb"),
    "dark": ("#e6edf3", "#9da7b3", "#58a6ff", "#30363d", "#374151"),
}


def theme_css(theme):
    primary, muted, accent, border, track = PALETTES[theme]
    return f"""
svg {{ color: {muted}; }}
h1, h2 {{ color: {accent} !important; }}
.body {{ fill: {primary}; }} .muted {{ fill: {muted}; }} .title {{ fill: {accent}; }}
.title-stroke {{ stroke: {accent}; }} .rule {{ stroke: {border}; }}
.track {{ fill: {track}; }} .track-ring {{ stroke: {track}; }}
.all-repository-languages small,
.all-repository-languages .language-item > div > span {{ color: {muted} !important; }}
.all-repository-languages h2 path {{ stroke: {accent}; }}
.profile-language-track {{ background: {track} !important; }}
.custom-leetcode {{ color: {primary}; border-color: {border}; }}
.custom-leetcode .leetcode-muted, .custom-leetcode .leetcode-tag {{ color: {muted}; }}
.custom-leetcode .leetcode-tag {{ border-color: {border}; }}
.custom-leetcode .leetcode-track {{ stroke: {track}; }}
.custom-leetcode .leetcode-primary-svg {{ fill: {primary}; }}
"""


def install_theme(document, theme="light"):
    css = theme_css(theme)
    root = document.documentElement
    # Remove the prior opaque fix as well as a previous palette on repeat updates.
    for node in list(root.childNodes):
        if node.nodeType == node.ELEMENT_NODE and node.getAttribute("id") in (
            "profile-background", "profile-theme"
        ):
            root.removeChild(node)
    root.setAttribute("data-profile-theme", theme)
    style = document.createElementNS(SVG_NS, "style")
    style.setAttribute("id", "profile-theme")
    style.appendChild(document.createTextNode(css))
    root.appendChild(style)


def main():
    if len(sys.argv) != 4:
        raise SystemExit("Usage: profile_theme.py INPUT_SVG OUTPUT_SVG light|dark")
    document = minidom.parse(sys.argv[1])
    install_theme(document, sys.argv[3])
    output = document.toxml(encoding="utf-8")
    ET.fromstring(output)
    Path(sys.argv[2]).write_bytes(output)
    print(f"Wrote transparent {sys.argv[3]} profile metrics to {sys.argv[2]}")


if __name__ == "__main__":
    main()
