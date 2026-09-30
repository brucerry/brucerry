"""Render public LeetCode profile stats in the metrics SVG."""

import json
import math
from pathlib import Path
import sys
from urllib.request import Request, urlopen
from xml.dom import Node, minidom
import xml.etree.ElementTree as ET

from progress_numbers import PROGRESS_DURATION, html_counter, install_styles as install_count_styles, svg_counter


USERNAME = "brucerry"
XHTML_NS = "http://www.w3.org/1999/xhtml"
SVG_NS = "http://www.w3.org/2000/svg"
CARD_HEIGHT = 282
RING_CIRCUMFERENCE = 2 * math.pi * 68
RING_START_ANGLE = -90
RING_DURATION_SECONDS = PROGRESS_DURATION
RING_STROKE_WIDTH = 8
RING_TRACK_WIDTH = 3
LEVELS = (("Easy", "#22c55e"), ("Medium", "#fbbf24"), ("Hard", "#f87171"))
# LeetCode symbol from Simple Icons: https://github.com/simple-icons/simple-icons/blob/develop/icons/leetcode.svg
LOGO_PATH = (
    "M13.483 0a1.374 1.374 0 0 0-.961.438L7.116 6.226l-3.854 4.126a5.266 5.266 0 0 0-1.209 2.104"
    " 5.35 5.35 0 0 0-.125.513 5.527 5.527 0 0 0 .062 2.362 5.83 5.83 0 0 0 .349 1.017 5.938 5.938"
    " 0 0 0 1.271 1.818l4.277 4.193.039.038c2.248 2.165 5.852 2.133 8.063-.074l2.396-2.392c.54-.54.54-1.414"
    ".003-1.955a1.378 1.378 0 0 0-1.951-.003l-2.396 2.392a3.021 3.021 0 0 1-4.205.038l-.02-.019-4.276-4.193"
    "c-.652-.64-.972-1.469-.948-2.263a2.68 2.68 0 0 1 .066-.523 2.545 2.545 0 0 1 .619-1.164L9.13 8.114"
    "c1.058-1.134 3.204-1.27 4.43-.278l3.501 2.831c.593.48 1.461.387 1.94-.207a1.384 1.384 0 0 0-.207-1.943"
    "l-3.5-2.831c-.8-.647-1.766-1.045-2.774-1.202l2.015-2.158A1.384 1.384 0 0 0 13.483 0z"
    "m-2.866 12.815a1.38 1.38 0 0 0-1.38 1.382 1.38 1.38 0 0 0 1.38 1.382H20.79a1.38 1.38 0 0 0 1.38-1.382"
    " 1.38 1.38 0 0 0-1.38-1.382z"
)
GRAPHQL = """
query ProfileMetrics($username: String!) {
  allQuestionsCount { difficulty count }
  matchedUser(username: $username) {
    username
    submitStatsGlobal { acSubmissionNum { difficulty count } }
    tagProblemCounts {
      fundamental { tagName problemsSolved }
      intermediate { tagName problemsSolved }
      advanced { tagName problemsSolved }
    }
  }
}
"""


def fetch_stats():
    body = json.dumps({"query": GRAPHQL, "variables": {"username": USERNAME}}).encode()
    request = Request(
        "https://leetcode.com/graphql/",
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; profile-metrics/1.0)",
            "Origin": "https://leetcode.com",
            "Referer": f"https://leetcode.com/u/{USERNAME}/",
        },
        method="POST",
    )
    with urlopen(request, timeout=25) as response:
        result = json.load(response)
    if result.get("errors") or not result.get("data", {}).get("matchedUser"):
        raise ValueError(f"LeetCode profile data is unavailable: {result.get('errors')}")

    data = result["data"]
    user = data["matchedUser"]
    available = {row["difficulty"]: row["count"] for row in data["allQuestionsCount"]}
    solved = {row["difficulty"]: row["count"] for row in user["submitStatsGlobal"]["acSubmissionNum"]}
    for level in ("All", "Easy", "Medium", "Hard"):
        if available[level] <= 0 or not 0 <= solved[level] <= available[level]:
            raise ValueError(f"Invalid LeetCode {level} count")
    if sum(solved[level] for level, _ in LEVELS) != solved["All"]:
        raise ValueError("LeetCode difficulty totals do not match")
    tags = user["tagProblemCounts"]
    top_tags = sorted(
        (tag for group in ("fundamental", "intermediate", "advanced") for tag in tags[group]),
        key=lambda tag: (-tag["problemsSolved"], tag["tagName"]),
    )[:6]
    return available, solved, top_tags


def element(document, tag, value=None, style=None, class_name=None):
    node = document.createElementNS(XHTML_NS, tag)
    if style:
        node.setAttribute("style", style)
    if class_name:
        node.setAttribute("class", class_name)
    if value is not None:
        node.appendChild(document.createTextNode(str(value)))
    return node


def svg_element(document, tag, **attributes):
    node = document.createElementNS(SVG_NS, tag)
    if tag == "svg":
        node.setAttribute("xmlns", SVG_NS)
    for name, value in attributes.items():
        node.setAttribute(name, str(value))
    return node


def install_animation_styles(document, available, solved):
    root = document.documentElement
    for node in list(root.getElementsByTagNameNS(SVG_NS, "style")):
        if node.getAttribute("id") == "profile-leetcode-animations":
            node.parentNode.removeChild(node)

    css = ["""
.custom-leetcode { color: #24292f; border-top: 1px solid #d8dee4; }
.custom-leetcode .leetcode-muted { color: #57606a; }
.custom-leetcode .leetcode-tag { border: 1px solid #d8dee4; color: #57606a; }
.custom-leetcode .leetcode-track { stroke: #e5e7eb; }
.custom-leetcode .leetcode-primary-svg { fill: #24292f; }
@keyframes leetcode-details-in {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
@media (prefers-color-scheme: dark) {
  .custom-leetcode { color: #e6edf3; border-color: #30363d; }
  .custom-leetcode .leetcode-muted, .custom-leetcode .leetcode-tag { color: #9da7b3; }
  .custom-leetcode .leetcode-tag { border-color: #30363d; }
  .custom-leetcode .leetcode-track { stroke: #374151; }
  .custom-leetcode .leetcode-primary-svg { fill: #e6edf3; }
}
@media (prefers-reduced-motion: reduce) {
  .leetcode-animated { animation: none !important; }
}
"""]
    solved_length = RING_CIRCUMFERENCE * solved["All"] / available["All"]
    css.append(
        "@keyframes leetcode-ring-reveal {"
        f"from {{ stroke-dasharray: 0 {RING_CIRCUMFERENCE:.3f}; }}"
        f"to {{ stroke-dasharray: {solved_length:.3f} {RING_CIRCUMFERENCE:.3f}; }}"
        "}"
    )
    style = svg_element(document, "style", id="profile-leetcode-animations")
    style.appendChild(document.createTextNode("\n".join(css)))
    root.insertBefore(style, root.firstChild)


def make_ring(document, available, solved):
    ring = svg_element(document, "svg", viewBox="0 0 180 180", width="174", height="174")
    ring.setAttribute("class", "leetcode-ring")
    ring.setAttribute("style", "display:block;flex:none")
    defs = svg_element(document, "defs")
    mask = svg_element(document, "mask", id="leetcode-progress-mask", maskUnits="userSpaceOnUse", x="0", y="0", width="180", height="180")
    solved_length = RING_CIRCUMFERENCE * solved["All"] / available["All"]
    sweep = svg_element(
        document, "circle", cx="90", cy="90", r="68", fill="none", stroke="#fff",
        transform=f"rotate({RING_START_ANGLE} 90 90)",
        **{"stroke-width": str(RING_STROKE_WIDTH), "stroke-linecap": "round",
           "stroke-dasharray": f"{solved_length:.3f} {RING_CIRCUMFERENCE:.3f}"},
    )
    sweep.setAttribute("class", "leetcode-animated")
    sweep.setAttribute("style", f"animation:leetcode-ring-reveal {RING_DURATION_SECONDS:.1f}s cubic-bezier(0,0,0.2,1) both")
    mask.appendChild(sweep)
    defs.appendChild(mask)
    ring.appendChild(defs)
    track = svg_element(document, "circle", cx="90", cy="90", r="68", fill="none",
                        **{"stroke-width": str(RING_TRACK_WIDTH)})
    track.setAttribute("class", "leetcode-track")
    ring.appendChild(track)

    offset = 0
    arcs = svg_element(document, "g", mask="url(#leetcode-progress-mask)")
    for level, color in LEVELS:
        length = RING_CIRCUMFERENCE * solved[level] / available["All"]
        arc = svg_element(
            document, "circle", cx="90", cy="90", r="68", fill="none", stroke=color,
            transform=f"rotate({RING_START_ANGLE} 90 90)",
            **{"stroke-width": str(RING_STROKE_WIDTH), "stroke-linecap": "round",
               "stroke-dasharray": f"{length:.3f} {RING_CIRCUMFERENCE:.3f}",
               "stroke-dashoffset": f"{-offset:.3f}"},
        )
        arcs.appendChild(arc)
        offset += length
    ring.appendChild(arcs)

    percent = svg_element(document, "text", x="90", y="88", **{"text-anchor": "middle", "font-size": "29", "font-weight": "700"})
    percent.setAttribute("class", "leetcode-primary-svg")
    svg_counter(document, percent, 100 * solved["All"] / available["All"], decimals=1, suffix="%")
    ring.appendChild(percent)
    label = svg_element(document, "text", x="90", y="110", **{"text-anchor": "middle", "font-size": "13", "font-weight": "600"})
    label.setAttribute("class", "leetcode-primary-svg")
    label.appendChild(document.createTextNode("solved"))
    ring.appendChild(label)
    return ring


def make_card(document, available, solved, tags):
    card = element(
        document, "section",
        style="box-sizing:border-box;height:266px;margin:8px 12px 8px;padding:16px 22px 12px;background:transparent",
        class_name="custom-leetcode",
    )
    card.setAttribute("data-added-height", str(CARD_HEIGHT))

    heading = element(document, "div", style="display:flex;align-items:center;gap:10px;height:25px")
    logo = svg_element(document, "svg", viewBox="0 0 24 24", width="24", height="24")
    logo.appendChild(svg_element(document, "path", d=LOGO_PATH, fill="#ffa116"))
    heading.appendChild(logo)
    heading.appendChild(element(document, "h2", USERNAME, "margin:0;font-size:19px;font-weight:700;color:inherit"))
    card.appendChild(heading)

    main = element(document, "div", style="display:flex;align-items:center;gap:28px;margin-top:8px;height:174px", class_name="leetcode-main")
    main.appendChild(make_ring(document, available, solved))
    summary = element(document, "div", style="flex:1;min-width:0", class_name="leetcode-summary")
    summary.appendChild(element(document, "div", "PROBLEMS SOLVED", "font-size:11px;font-weight:700;letter-spacing:1.1px", "leetcode-muted leetcode-summary-label"))
    count = element(document, "div", style="margin:5px 0 19px;white-space:nowrap", class_name="leetcode-count")
    solved_count = element(document, "strong", style="font-size:31px;line-height:1;font-weight:700")
    solved_count.appendChild(html_counter(document, solved["All"]))
    count.appendChild(solved_count)
    count.appendChild(element(document, "span", f" / {available['All']:,}", "font-size:16px", "leetcode-muted"))
    summary.appendChild(count)

    levels = element(document, "div", style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px", class_name="leetcode-levels")
    for index, (level, color) in enumerate(LEVELS):
        stat = element(
            document, "div",
            style=f"padding-left:10px;border-left:3px solid {color};"
                  f"animation:leetcode-details-in .5s ease-out {0.25 + index * 0.2:.2f}s both",
            class_name="leetcode-animated leetcode-stat",
        )
        stat.appendChild(element(document, "div", level.upper(), f"font-size:10px;font-weight:700;letter-spacing:1px;color:{color}"))
        level_count = element(document, "div", style="margin:5px 0 3px;font-size:17px;font-weight:650;white-space:nowrap")
        level_count.appendChild(html_counter(document, solved[level]))
        level_count.appendChild(document.createTextNode(f" / {available[level]:,}"))
        stat.appendChild(level_count)
        level_percent = element(document, "div", style="font-size:11px;white-space:nowrap", class_name="leetcode-muted")
        level_percent.appendChild(html_counter(document, 100 * solved[level] / available["All"], decimals=1, suffix="%"))
        level_percent.appendChild(document.createTextNode(" of total"))
        stat.appendChild(level_percent)
        levels.appendChild(stat)
    summary.appendChild(levels)
    main.appendChild(summary)
    card.appendChild(main)

    footer = element(document, "div", style="display:flex;align-items:center;gap:8px;margin-top:8px;white-space:nowrap", class_name="leetcode-skills")
    footer.appendChild(element(document, "span", "TOP SKILLS", "margin-right:3px;font-size:10px;font-weight:700;letter-spacing:1px", "leetcode-muted"))
    for tag in tags:
        footer.appendChild(element(
            document, "span", f"{tag['tagName']} · {tag['problemsSolved']:,}",
            "padding:4px 8px;border-radius:99px;font-size:10px", "leetcode-tag",
        ))
    card.appendChild(footer)
    return card


def add_card(document, stats):
    wrappers = [node for node in document.getElementsByTagNameNS(XHTML_NS, "div")
                if node.getAttribute("class") == "items-wrapper"]
    if len(wrappers) != 1:
        raise ValueError("Could not identify the metrics content wrapper")
    wrapper = wrappers[0]
    removed_height = 0
    for node in list(wrapper.childNodes):
        if node.nodeType != Node.ELEMENT_NODE or node.localName != "section":
            continue
        if node.getAttribute("class") == "custom-leetcode":
            removed_height += int(node.getAttribute("data-added-height"))
            wrapper.removeChild(node)
    wrapper.appendChild(make_card(document, *stats))
    for node in list(wrapper.childNodes):
        if node.nodeType == Node.TEXT_NODE and not node.data.strip():
            wrapper.removeChild(node)
    for node in list(wrapper.childNodes):
        wrapper.insertBefore(document.createTextNode("\n            "), node)
    wrapper.appendChild(document.createTextNode("\n        "))
    install_animation_styles(document, stats[0], stats[1])
    install_count_styles(document)

    root = document.documentElement
    height = int(float(root.getAttribute("height"))) + CARD_HEIGHT - removed_height
    root.setAttribute("height", str(height))
    view_box = root.getAttribute("viewBox").split()
    if len(view_box) == 4:
        view_box[3] = str(height)
        root.setAttribute("viewBox", " ".join(view_box))


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("github-metrics.svg")
    stats = fetch_stats()
    document = minidom.parse(str(path))
    add_card(document, stats)
    output = document.toxml(encoding="utf-8")
    ET.fromstring(output)
    path.write_bytes(output)
    print(f"Added LeetCode stats for {USERNAME} to {path}")


if __name__ == "__main__":
    main()
