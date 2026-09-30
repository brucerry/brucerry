"""Add every owned public repository language to the generated metrics SVG."""

import json
import math
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.dom import Node, minidom
import xml.etree.ElementTree as ET


USER = "brucerry"
SVG_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("github-metrics.svg")
OUTPUT_PATH = Path(sys.argv[2]) if len(sys.argv) > 2 else SVG_PATH
TOKEN = os.environ.get("GITHUB_TOKEN", "")
XHTML_NS = "http://www.w3.org/1999/xhtml"
SVG_NS = "http://www.w3.org/2000/svg"

ANIMATION_CSS = """
@keyframes profile-language-grow {
  from { transform: scaleX(0); }
  to { transform: scaleX(1); }
}
@keyframes profile-language-enter {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
@media (prefers-reduced-motion: reduce) {
  .profile-language-animation { animation: none !important; }
}
"""


def get_json(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "brucerry-profile-languages",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def owned_public_repositories():
    page = 1
    while True:
        query = urlencode({"type": "owner", "per_page": 100, "page": page})
        batch = get_json(f"https://api.github.com/users/{USER}/repos?{query}")
        for repo in batch:
            if repo["owner"]["login"].lower() == USER and not repo["fork"]:
                yield repo
        if len(batch) < 100:
            break
        page += 1


def size_label(size):
    if size >= 1_000_000:
        return f"{size / 1_000_000:.1f} MB"
    if size >= 1_000:
        return f"{size / 1_000:.1f} KB"
    return f"{size} B"


def text_content(node):
    if node.nodeType == Node.TEXT_NODE:
        return node.data
    return "".join(text_content(child) for child in node.childNodes)


def html_element(document, tag, text=None, style=None):
    node = document.createElementNS(XHTML_NS, tag)
    if style:
        node.setAttribute("style", style)
    if text is not None:
        node.appendChild(document.createTextNode(text))
    return node


def install_animation_styles(document):
    root = document.documentElement
    for node in list(root.getElementsByTagNameNS(SVG_NS, "style")):
        if node.getAttribute("id") == "profile-language-animations":
            node.parentNode.removeChild(node)
    style = document.createElementNS(SVG_NS, "style")
    style.setAttribute("id", "profile-language-animations")
    style.appendChild(document.createTextNode(ANIMATION_CSS))
    root.insertBefore(style, root.firstChild)


def add_section(document, repositories, languages):
    wrappers = [
        node for node in document.getElementsByTagNameNS(XHTML_NS, "div")
        if node.getAttribute("class") == "items-wrapper"
    ]
    if len(wrappers) != 1:
        raise ValueError("Could not identify the metrics content wrapper")
    wrapper = wrappers[0]

    removed_height = 0

    def remove_with_spacing(node):
        previous = node.previousSibling
        if previous is not None and previous.nodeType == Node.TEXT_NODE and not previous.data.strip():
            wrapper.removeChild(previous)
        wrapper.removeChild(node)

    for section in list(wrapper.childNodes):
        if section.nodeType != Node.ELEMENT_NODE or section.localName != "section":
            continue
        if section.getAttribute("class") == "all-repository-languages":
            prior_height = section.getAttribute("data-added-height")
            if not prior_height:
                prior_count = re.search(r"(\d+) languages in", text_content(section))
                if prior_count is None:
                    raise ValueError("Could not determine the previous language section height")
                prior_height = str(92 + 24 * math.ceil(int(prior_count.group(1)) / 2))
            removed_height += int(prior_height)
            remove_with_spacing(section)
            continue
        if "Most used languages" not in text_content(section):
            continue
        previous = section.previousSibling
        while previous is not None and previous.nodeType != Node.ELEMENT_NODE:
            previous = previous.previousSibling
        if previous is not None and re.search(r"\b\d+ Languages\b", text_content(previous)):
            remove_with_spacing(previous)
        remove_with_spacing(section)
        removed_height += 110

    ordered = sorted(languages.items(), key=lambda item: (-item[1], item[0].casefold()))
    rows = math.ceil(len(ordered) / 2)
    section = html_element(document, "section", style="margin:8px 12px 12px")
    section.setAttribute("class", "all-repository-languages")
    added_height = 74 + 24 * rows
    section.setAttribute("data-added-height", str(added_height))
    section.appendChild(html_element(document, "h2", "Languages across repositories", "margin:8px 0 4px;font-size:16px;color:#0366d6"))
    section.appendChild(html_element(
        document, "small",
        f"{len(ordered)} languages in {len(repositories)} owned public repositories (forks excluded)",
        "display:block;margin-bottom:8px;color:#666",
    ))

    total = sum(languages.values())
    palette = ("#0969da", "#bf8700", "#1a7f37", "#8250df", "#cf222e", "#0550ae", "#9a6700", "#116329", "#6f42c1", "#a40e26")
    bar = html_element(
        document, "div",
        style="display:flex;width:100%;height:10px;margin:8px 0;border-radius:5px;overflow:hidden;"
              "transform-origin:left center;animation:profile-language-grow 1.5s ease-out both",
    )
    bar.setAttribute("class", "profile-language-animation")
    for index, (_, byte_count) in enumerate(ordered):
        segment = html_element(document, "span", style=f"width:{100 * byte_count / total:.8f}%;background:{palette[index % len(palette)]}")
        bar.appendChild(segment)
    section.appendChild(bar)

    grid = html_element(document, "div", style="display:grid;grid-template-columns:1fr 1fr;column-gap:32px;row-gap:4px")
    grid.setAttribute("class", "language-grid")
    for index, (name, byte_count) in enumerate(ordered):
        column, row = divmod(index, rows)
        item = html_element(
            document, "div",
            style=f"grid-column:{column + 1};grid-row:{row + 1};height:20px;white-space:nowrap;"
                  f"animation:profile-language-enter .5s ease-out {0.12 + index * 0.04:.2f}s both",
        )
        item.setAttribute("class", "profile-language-animation language-item")
        detail = html_element(document, "div", style="display:flex;align-items:center;justify-content:space-between;gap:8px;height:16px")
        label = html_element(document, "span", style="color:#777")
        label.appendChild(html_element(document, "span", "● ", f"color:{palette[index % len(palette)]}"))
        label.appendChild(document.createTextNode(name))
        detail.appendChild(label)
        percent = 100 * byte_count / total
        percent_label = "<0.01%" if 0 < percent < 0.01 else f"{percent:.2f}%"
        detail.appendChild(html_element(document, "small", f"{percent_label} · {size_label(byte_count)}", "color:#666;text-align:right"))
        item.appendChild(detail)
        track = html_element(document, "div", style="height:2px;margin-top:2px;background:#eaeef2;border-radius:2px;overflow:hidden")
        fill = html_element(
            document, "div",
            style=f"width:{100 * byte_count / ordered[0][1]:.2f}%;min-width:2px;height:2px;"
                  f"background:{palette[index % len(palette)]};transform-origin:left center;"
                  f"animation:profile-language-grow 1.1s ease-out {0.16 + index * 0.04:.2f}s both",
        )
        fill.setAttribute("class", "profile-language-animation")
        track.appendChild(fill)
        item.appendChild(track)
        grid.appendChild(item)
    section.appendChild(grid)

    leetcode = next((node for node in wrapper.childNodes if node.nodeType == Node.ELEMENT_NODE
                     and (node.getAttribute("class") == "custom-leetcode"
                          or "LeetCode statistics for brucerry" in text_content(node))), None)
    wrapper.insertBefore(section, leetcode)
    for node in list(wrapper.childNodes):
        if node.nodeType == Node.TEXT_NODE and not node.data.strip():
            wrapper.removeChild(node)
    for node in list(wrapper.childNodes):
        wrapper.insertBefore(document.createTextNode("\n            "), node)
    wrapper.appendChild(document.createTextNode("\n        "))

    install_animation_styles(document)

    root = document.documentElement
    height = int(float(root.getAttribute("height"))) + added_height - removed_height
    root.setAttribute("height", str(height))
    view_box = root.getAttribute("viewBox").split()
    if len(view_box) == 4:
        view_box[3] = str(height)
        root.setAttribute("viewBox", " ".join(view_box))


def main():
    repositories = list(owned_public_repositories())
    if not repositories:
        raise SystemExit("No owned public repositories found; keeping the previous SVG.")
    languages = {}
    for repo in repositories:
        for name, byte_count in get_json(repo["languages_url"]).items():
            languages[name] = languages.get(name, 0) + byte_count
    if not languages:
        raise SystemExit("No language data found; keeping the previous SVG.")

    document = minidom.parse(str(SVG_PATH))
    add_section(document, repositories, languages)
    output = document.toxml(encoding="utf-8")
    ET.fromstring(output)
    OUTPUT_PATH.write_bytes(output)
    print(f"Added {len(languages)} languages from {len(repositories)} owned public repositories to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
