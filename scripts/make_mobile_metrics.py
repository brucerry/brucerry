"""Render mobile profile metrics as native SVG with fixed Safari-safe layout."""

import math
from pathlib import Path
import re
import sys
from xml.dom import Node, minidom
import xml.etree.ElementTree as ET

from progress_numbers import count_styles, final_number, number_frames


SVG = "http://www.w3.org/2000/svg"
HTML = "http://www.w3.org/1999/xhtml"
WIDTH = 390
LEFT = 16
RIGHT = 374
ET.register_namespace("", SVG)


def text_content(node):
    if node.nodeType == Node.TEXT_NODE:
        return node.data
    if node.nodeType == Node.ELEMENT_NODE and "count-step" in node.getAttribute("class").split():
        return ""
    return "".join(text_content(child) for child in node.childNodes)


def text_value(node):
    return " ".join(text_content(node).split())


def children(node, tag=None, class_name=None):
    return [child for child in node.childNodes if child.nodeType == Node.ELEMENT_NODE
            and (tag is None or child.localName == tag)
            and (class_name is None or class_name in child.getAttribute("class").split())]


def descendant(node, tag, class_name=None):
    return next((child for child in node.getElementsByTagNameNS(HTML, tag)
                 if class_name is None or class_name in child.getAttribute("class").split()), None)


def element(parent, tag, **attrs):
    return ET.SubElement(parent, f"{{{SVG}}}{tag}",
                         {name.replace("_", "-"): str(value) for name, value in attrs.items()})


def label(parent, x, y, value, css="body", size=13, **attrs):
    node = element(parent, "text", x=x, y=y, **{"class": css, "font-size": size}, **attrs)
    node.text = value
    return node


def count_label(parent, x, y, value, decimals=0, suffix="", css="body", size=13, **attrs):
    node = label(parent, x, y, "", f"{css} profile-count", size, **attrs)
    final = element(node, "tspan", x=x, y=y, **{"class": "count-final"})
    final.text = final_number(value, decimals, suffix)
    for index, displayed in enumerate(number_frames(value, decimals, suffix)):
        frame = element(node, "tspan", x=x, y=y,
                        **{"class": f"count-step count-step-{index}", "aria-hidden": "true"})
        frame.text = displayed
    return node


def rule(parent, y):
    element(parent, "line", x1=LEFT, x2=RIGHT, y1=y, y2=y, **{"class": "rule"})


def title(parent, y, value):
    label(parent, LEFT, y, value, "title", 18, font_weight=650)
    return y + 24


def fields(section):
    return [text_value(node) for node in section.getElementsByTagNameNS(HTML, "div")
            if "field" in node.getAttribute("class").split() and text_value(node)]


def info(parent, y, heading, values):
    y = title(parent, y, heading)
    for value in values:
        label(parent, LEFT, y, value, "muted")
        y += 21
    return y + 12


def style_value(style, name):
    found = re.search(rf"(?:^|;){re.escape(name)}:([^;]+)", style)
    if found is None:
        raise ValueError(f"Missing {name} in {style}")
    return found.group(1)


def animation_duration(style):
    found = re.search(r"animation:[^;]*?\b([0-9]+(?:\.[0-9]+)?)s\b", style)
    if found is None:
        raise ValueError(f"Missing animation duration in {style}")
    return float(found.group(1))


def draw_languages(parent, y, section):
    y = title(parent, y, "Languages across repositories")
    label(parent, LEFT, y, text_value(descendant(section, "small")), "muted", 11)
    y += 17
    bar, grid = children(section, "div")
    clips = element(parent, "defs")
    clip = element(clips, "clipPath", id="languages-clip")
    element(clip, "rect", x=LEFT, y=y, width=RIGHT - LEFT, height=9, rx=5)
    element(parent, "rect", x=LEFT, y=y, width=RIGHT - LEFT, height=9, rx=5,
            **{"class": "track"})
    group = element(parent, "g", **{"clip-path": "url(#languages-clip)", "class": "bar-grow"})
    x = LEFT
    for segment in children(bar, "span"):
        segment_style = segment.getAttribute("style")
        width = (RIGHT - LEFT) * float(style_value(segment_style, "width").rstrip("%")) / 100
        element(group, "rect", x=f"{x:.4f}", y=y, width=f"{width:.4f}", height=9,
                fill=style_value(segment_style, "background"))
        x += width
    y += 32
    for item in children(grid, "div", "language-item"):
        detail, track = children(item, "div")
        name = text_value(children(detail, "span")[0]).removeprefix("● ")
        amount = text_value(children(detail, "small")[0])
        fill = children(track, "div")[0].getAttribute("style")
        color = style_value(fill, "background")
        width = max(5, (RIGHT - LEFT) * float(style_value(fill, "width").rstrip("%")) / 100)
        element(parent, "circle", cx=LEFT + 5, cy=y - 5, r=5, fill=color)
        label(parent, LEFT + 18, y, name)
        parsed_amount = re.fullmatch(r"([0-9.]+)% · (.+)", amount)
        if parsed_amount:
            count_label(parent, RIGHT, y, float(parsed_amount.group(1)), decimals=2,
                        suffix=f"% · {parsed_amount.group(2)}", css="muted", size=11,
                        text_anchor="end")
        else:
            label(parent, RIGHT, y, amount, "muted", 11, text_anchor="end")
        element(parent, "rect", x=LEFT, y=y + 6, width=RIGHT - LEFT, height=5, rx=3,
                **{"class": "track"})
        element(parent, "rect", x=LEFT, y=y + 6, width=f"{width:.2f}", height=5, rx=3,
                fill=color, **{"class": "bar-grow"})
        y += 28
    return y + 8


def ring_data(section):
    ring = next(node for node in section.getElementsByTagNameNS(SVG, "svg")
                if "leetcode-ring" in node.getAttribute("class"))
    sweep, track, *arcs = ring.getElementsByTagNameNS(SVG, "circle")
    return sweep, track, arcs, ring.getElementsByTagNameNS(SVG, "text")


def draw_leetcode(parent, y, section):
    logo = section.getElementsByTagNameNS(SVG, "path")[0]
    element(parent, "path", d=logo.getAttribute("d"), fill="#ffa116",
            transform=f"translate({LEFT} {y - 17}) scale(.85)")
    label(parent, LEFT + 31, y, "brucerry", "body", 19, font_weight=700)
    y += 18
    sweep, track, arcs, texts = ring_data(section)
    center_x, center_y, radius = 91, y + 80, 68
    length, circumference = sweep.getAttribute("stroke-dasharray").split()
    rotation = sweep.getAttribute("transform").split("(", 1)[1].split()[0]
    stroke_width = sweep.getAttribute("stroke-width")
    defs = element(parent, "defs")
    mask = element(defs, "mask", id="mobile-ring-mask", maskUnits="userSpaceOnUse",
                   x=0, y=y, width=190, height=160)
    element(mask, "circle", cx=center_x, cy=center_y, r=radius, fill="none",
            stroke="white", stroke_width=stroke_width, stroke_dasharray=f"{length} {circumference}",
            stroke_linecap="round",
            transform=f"rotate({rotation} {center_x} {center_y})", **{"class": "ring-sweep"})
    element(parent, "circle", cx=center_x, cy=center_y, r=radius, fill="none",
            stroke_width=track.getAttribute("stroke-width"),
            **{"class": "track-ring"})
    group = element(parent, "g", mask="url(#mobile-ring-mask)")
    for arc in arcs:
        element(group, "circle", cx=center_x, cy=center_y, r=radius, fill="none",
                stroke=arc.getAttribute("stroke"), stroke_width=stroke_width,
                stroke_linecap=arc.getAttribute("stroke-linecap"),
                stroke_dasharray=arc.getAttribute("stroke-dasharray"),
                stroke_dashoffset=arc.getAttribute("stroke-dashoffset"),
                transform=f"rotate({rotation} {center_x} {center_y})")
    count_label(parent, center_x, center_y - 2, float(text_value(texts[0]).rstrip("%")),
                decimals=1, suffix="%", size=27, text_anchor="middle", font_weight=700)
    label(parent, center_x, center_y + 20, "solved", size=14,
          text_anchor="middle", font_weight=600)
    label(parent, 205, center_y - 28, "PROBLEMS SOLVED", "muted", 10,
          font_weight=700, letter_spacing=1)
    solved_count, _, available_count = text_value(descendant(section, "div", "leetcode-count")).partition(" / ")
    count_label(parent, 205, center_y + 6, int(solved_count.replace(",", "")),
                suffix=f" / {available_count}", size=21, font_weight=700)
    y += 180
    stats = [node for node in section.getElementsByTagNameNS(HTML, "div")
             if "leetcode-stat" in node.getAttribute("class").split()]
    for x, stat, color in zip((LEFT, 140, 264), stats, ("#22c55e", "#fbbf24", "#f87171")):
        level, count, percentage = [text_value(node) for node in children(stat, "div")]
        element(parent, "rect", x=x, y=y - 12, width=3, height=52, fill=color)
        label(parent, x + 10, y, level, "muted", 11, font_weight=700)
        solved_count, _, available_count = count.partition(" / ")
        count_label(parent, x + 10, y + 19, int(solved_count.replace(",", "")),
                    suffix=f" / {available_count}", size=12, font_weight=600)
        count_label(parent, x + 10, y + 36, float(percentage.split("%", 1)[0]),
                    decimals=1, suffix="% of total", css="muted", size=10)
    y += 72
    label(parent, LEFT, y, "TOP SKILLS", "muted", 11, font_weight=700)
    y += 22
    tags = [text_value(node) for node in section.getElementsByTagNameNS(HTML, "span")
            if "leetcode-tag" in node.getAttribute("class").split()]
    for index, tag in enumerate(tags):
        label(parent, LEFT + index % 2 * 182, y + index // 2 * 23, tag, "muted", 12)
    return y + math.ceil(len(tags) / 2) * 23 + 18


def make_mobile(document):
    wrapper = next(node for node in document.getElementsByTagNameNS(HTML, "div")
                   if node.getAttribute("class") == "items-wrapper")
    sections = children(wrapper, "section")
    if len(sections) != 5 or sections[3].getAttribute("class") != "all-repository-languages" \
            or sections[4].getAttribute("class") != "custom-leetcode":
        raise ValueError("Unexpected desktop metrics structure")
    sweep = ring_data(sections[4])[0]
    ring_length, ring_circumference = sweep.getAttribute("stroke-dasharray").split()
    bar_duration = animation_duration(children(sections[3], "div")[0].getAttribute("style"))
    ring_duration = animation_duration(sweep.getAttribute("style"))
    if bar_duration != ring_duration:
        raise ValueError("Language and LeetCode progress animations must stay synchronized")
    root = ET.Element(f"{{{SVG}}}svg", width=str(WIDTH), role="img")
    element(root, "title").text = "Bruce Cheung GitHub profile, languages and LeetCode statistics"
    style = element(root, "style", id="profile-mobile-layout")
    style.text = f"""
text {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
.body {{ fill: #24292f; }} .muted {{ fill: #57606a; }} .title {{ fill: #0366d6; }}
.rule {{ stroke: #d8dee4; }} .track {{ fill: #e5e7eb; }} .track-ring {{ stroke: #e5e7eb; }}
@keyframes grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
@keyframes ring {{ from {{ stroke-dasharray: 0 {ring_circumference}; }}
  to {{ stroke-dasharray: {ring_length} {ring_circumference}; }} }}
.bar-grow {{ transform-box: fill-box; transform-origin: left center;
  animation: grow {bar_duration:g}s cubic-bezier(0,0,0.2,1) both; }}
.ring-sweep {{ animation: ring {ring_duration:g}s cubic-bezier(0,0,0.2,1) both; }}
@media (prefers-reduced-motion: reduce) {{
  .bar-grow, .ring-sweep {{ animation: none; }}
}}
@media (prefers-color-scheme: dark) {{
  .body {{ fill: #e6edf3; }} .muted {{ fill: #9da7b3; }} .title {{ fill: #58a6ff; }}
  .rule {{ stroke: #30363d; }} .track {{ fill: #374151; }} .track-ring {{ stroke: #374151; }}
}}
"""
    style.text += "\n" + count_styles(bar_duration)
    y = 30
    label(root, LEFT, y, "Bruce Cheung", size=22, font_weight=700)
    y += 26
    for field in fields(sections[0]):
        label(root, LEFT, y, field, "muted")
        y += 20
    y += 9
    rule(root, y)
    y += 30
    headings = sections[1].getElementsByTagNameNS(HTML, "h2")
    values = fields(sections[1])
    split = len(values) // 2
    y = info(root, y, text_value(headings[0]), values[:split])
    y = info(root, y, text_value(headings[1]), values[split:])
    y = info(root, y, text_value(sections[2].getElementsByTagNameNS(HTML, "h2")[0]),
             fields(sections[2]))
    rule(root, y - 6)
    y += 24
    y = draw_languages(root, y, sections[3])
    rule(root, y - 8)
    y += 25
    y = draw_leetcode(root, y, sections[4])
    root.set("height", str(y))
    root.set("viewBox", f"0 0 {WIDTH} {y}")
    return root


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: make_mobile_metrics.py DESKTOP_SVG MOBILE_SVG")
    output = ET.tostring(make_mobile(minidom.parse(sys.argv[1])), encoding="utf-8",
                         xml_declaration=True)
    ET.fromstring(output)
    Path(sys.argv[2]).write_bytes(output)
    print(f"Wrote native mobile profile metrics to {sys.argv[2]}")


if __name__ == "__main__":
    main()
