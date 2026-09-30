"""Render public LeetCode profile stats in the metrics SVG."""

import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen
from xml.dom import Node, minidom
import xml.etree.ElementTree as ET


USERNAME = "brucerry"
XHTML_NS = "http://www.w3.org/1999/xhtml"
CARD_HEIGHT = 252
GRAPHQL = """
query ProfileMetrics($username: String!) {
  allQuestionsCount { difficulty count }
  matchedUser(username: $username) {
    username
    profile { ranking }
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
    tags = user["tagProblemCounts"]
    top_tags = sorted(
        (tag for group in ("fundamental", "intermediate", "advanced") for tag in tags[group]),
        key=lambda tag: (-tag["problemsSolved"], tag["tagName"]),
    )[:6]
    return available, solved, user["profile"]["ranking"], top_tags


def element(document, tag, value=None, style=None, class_name=None):
    node = document.createElementNS(XHTML_NS, tag)
    if style:
        node.setAttribute("style", style)
    if class_name:
        node.setAttribute("class", class_name)
    if value is not None:
        node.appendChild(document.createTextNode(str(value)))
    return node


def progress(document, solved, available, color, height=7):
    track = element(document, "div", style=f"height:{height}px;background:#334155;border-radius:99px;overflow:hidden")
    track.appendChild(element(
        document,
        "div",
        style=f"width:{100 * solved / available:.2f}%;height:100%;background:{color};border-radius:99px",
    ))
    return track


def make_card(document, available, solved, ranking, tags):
    card = element(
        document, "section",
        style="box-sizing:border-box;height:236px;margin:8px 12px 8px;padding:20px 22px;"
              "background:#0f172a;border:1px solid #334155;border-radius:16px;color:#f8fafc",
        class_name="custom-leetcode",
    )
    card.setAttribute("data-added-height", str(CARD_HEIGHT))

    heading = element(document, "div", style="display:flex;align-items:center;justify-content:space-between")
    title = element(document, "div", style="display:flex;align-items:center;gap:10px")
    title.appendChild(element(document, "span", "◆", "font-size:18px;color:#ffa116"))
    title.appendChild(element(document, "h2", "LeetCode", "margin:0;color:#f8fafc;font-size:18px;font-weight:700"))
    heading.appendChild(title)
    rank_text = f"GLOBAL RANK  #{ranking:,}" if ranking else f"@{USERNAME}"
    heading.appendChild(element(document, "span", rank_text, "font-size:11px;font-weight:700;letter-spacing:1px;color:#94a3b8"))
    card.appendChild(heading)

    main = element(document, "div", style="display:flex;gap:22px;align-items:stretch;margin-top:18px")
    summary = element(document, "div", style="box-sizing:border-box;width:29%;padding:2px 8px 0 0")
    summary.appendChild(element(document, "div", "PROBLEMS SOLVED", "font-size:11px;font-weight:700;letter-spacing:1.3px;color:#94a3b8"))
    count = element(document, "div", style="margin:4px 0 1px;white-space:nowrap")
    count.appendChild(element(document, "strong", f"{solved['All']:,}", "font-size:38px;line-height:1;font-weight:750;color:#f8fafc"))
    count.appendChild(element(document, "span", f" / {available['All']:,}", "font-size:15px;color:#94a3b8"))
    summary.appendChild(count)
    summary.appendChild(element(document, "div", f"{100 * solved['All'] / available['All']:.1f}% complete", "margin:3px 0 9px;font-size:12px;color:#cbd5e1"))
    summary.appendChild(progress(document, solved["All"], available["All"], "#ffa116", 8))
    main.appendChild(summary)

    difficulty = element(document, "div", style="display:flex;flex:1;gap:10px")
    for level, color in (("Easy", "#22c55e"), ("Medium", "#fbbf24"), ("Hard", "#f87171")):
        tile = element(document, "div", style="box-sizing:border-box;flex:1;min-width:0;padding:12px 13px;"
                       "background:#1e293b;border:1px solid #334155;border-radius:11px")
        tile.appendChild(element(document, "div", level.upper(), f"font-size:10px;font-weight:700;letter-spacing:1px;color:{color}"))
        tile.appendChild(element(document, "div", f"{solved[level]:,}", "margin:5px 0 1px;font-size:24px;font-weight:700;color:#f8fafc"))
        tile.appendChild(element(document, "div", f"of {available[level]:,} solved", "margin-bottom:9px;font-size:11px;color:#94a3b8"))
        tile.appendChild(progress(document, solved[level], available[level], color))
        difficulty.appendChild(tile)
    main.appendChild(difficulty)
    card.appendChild(main)

    footer = element(document, "div", style="display:flex;align-items:center;gap:8px;margin-top:15px;white-space:nowrap")
    footer.appendChild(element(document, "span", "TOP SKILLS", "margin-right:3px;font-size:10px;font-weight:700;letter-spacing:1px;color:#94a3b8"))
    for tag in tags:
        footer.appendChild(element(
            document, "span", f"{tag['tagName']} · {tag['problemsSolved']:,}",
            "padding:5px 8px;background:#1e293b;border:1px solid #334155;"
            "border-radius:99px;font-size:10px;color:#cbd5e1",
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
