"""Reflow the generated profile SVG for narrow GitHub profile screens."""

import math
from pathlib import Path
import re
import sys
from xml.dom import Node, minidom
import xml.etree.ElementTree as ET


SVG_NS = "http://www.w3.org/2000/svg"
XHTML_NS = "http://www.w3.org/1999/xhtml"
MOBILE_WIDTH = 390
MOBILE_CARD_HEIGHT = 376
BASE_WRAP_ALLOWANCE = 300

MOBILE_CSS = """
svg.mobile { font-size: 13px; }
svg.mobile .items-wrapper { box-sizing: border-box; width: 390px; overflow: hidden; }
svg.mobile .items-wrapper > section { box-sizing: border-box; width: auto !important; display: block !important; margin: 8px 12px !important; }
svg.mobile .largeable, svg.mobile .largeable-inline-flex { width: auto !important; display: block !important; }
svg.mobile .items-wrapper .field { white-space: normal; }
svg.mobile .items-wrapper .row { width: 100%; flex-wrap: wrap; }
svg.mobile .items-wrapper .row > section { min-width: 0; }
svg.mobile .items-wrapper > section:first-of-type .row > section { flex: 1 1 100%; }
svg.mobile .items-wrapper h1 { font-size: 19px; }
svg.mobile .items-wrapper h2 { font-size: 16px; }
svg.mobile .all-repository-languages .language-grid { display: block !important; }
svg.mobile .all-repository-languages .language-item { display: block !important; height: 21px !important; margin-bottom: 4px; }
svg.mobile .custom-leetcode { height: 360px !important; padding: 12px 4px !important; }
svg.mobile .leetcode-main { display: grid !important; grid-template-columns: 150px minmax(0, 1fr); grid-template-rows: 80px 80px auto; column-gap: 12px !important; height: auto !important; align-items: center; }
svg.mobile .leetcode-ring { grid-column: 1; grid-row: 1 / 3; width: 150px; height: 150px; }
svg.mobile .leetcode-summary { display: contents !important; }
svg.mobile .leetcode-summary-label { grid-column: 2; grid-row: 1; align-self: end; }
svg.mobile .leetcode-count { grid-column: 2; grid-row: 2; align-self: start; margin: 3px 0 0 !important; }
svg.mobile .leetcode-count strong { font-size: 24px !important; }
svg.mobile .leetcode-count span { font-size: 12px !important; }
svg.mobile .leetcode-levels { grid-column: 1 / -1; grid-row: 3; grid-template-columns: repeat(3, minmax(0, 1fr)) !important; gap: 5px !important; margin-top: 9px; }
svg.mobile .leetcode-stat { padding-left: 6px !important; }
svg.mobile .leetcode-stat > div:nth-child(2) { font-size: 12px !important; }
svg.mobile .leetcode-stat > div:nth-child(3) { font-size: 9px !important; }
svg.mobile .leetcode-skills { flex-wrap: wrap !important; white-space: normal !important; margin-top: 12px !important; gap: 5px !important; }
"""


def text_content(node):
    if node.nodeType == Node.TEXT_NODE:
        return node.data
    return "".join(text_content(child) for child in node.childNodes)


def make_mobile(document):
    sections = document.getElementsByTagNameNS(XHTML_NS, "section")
    language = next((node for node in sections if node.getAttribute("class") == "all-repository-languages"), None)
    leetcode = next((node for node in sections if node.getAttribute("class") == "custom-leetcode"), None)
    if language is None or leetcode is None:
        raise ValueError("The desktop metrics must include languages and LeetCode")
    match = re.search(r"(\d+) languages in", text_content(language))
    if match is None:
        raise ValueError("Could not determine the language count")
    language_count = int(match.group(1))
    language_extra = 24 * (language_count - math.ceil(language_count / 2))
    desktop_card_height = int(leetcode.getAttribute("data-added-height"))

    root = document.documentElement
    desktop_height = int(float(root.getAttribute("height")))
    mobile_height = desktop_height + language_extra + MOBILE_CARD_HEIGHT - desktop_card_height + BASE_WRAP_ALLOWANCE
    root.setAttribute("class", f"{root.getAttribute('class')} mobile")
    root.setAttribute("width", str(MOBILE_WIDTH))
    root.setAttribute("height", str(mobile_height))
    root.setAttribute("viewBox", f"0 0 {MOBILE_WIDTH} {mobile_height}")

    style = document.createElementNS(SVG_NS, "style")
    style.setAttribute("id", "profile-mobile-layout")
    style.appendChild(document.createTextNode(MOBILE_CSS))
    root.insertBefore(style, root.firstChild)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: make_mobile_metrics.py DESKTOP_SVG MOBILE_SVG")
    document = minidom.parse(sys.argv[1])
    make_mobile(document)
    output = document.toxml(encoding="utf-8")
    ET.fromstring(output)
    Path(sys.argv[2]).write_bytes(output)
    print(f"Wrote mobile profile metrics to {sys.argv[2]}")


if __name__ == "__main__":
    main()
