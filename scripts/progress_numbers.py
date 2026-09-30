"""Discrete number frames that animate inside self-contained SVG images."""

PROGRESS_DURATION = 1.5
FRAME_COUNT = 30
XHTML_NS = "http://www.w3.org/1999/xhtml"
SVG_NS = "http://www.w3.org/2000/svg"


def eased(fraction):
    """The value of cubic-bezier(0, 0, .2, 1) at a time fraction."""
    low, high = 0.0, 1.0
    for _ in range(24):
        position = (low + high) / 2
        inverse = 1 - position
        x = 0.6 * inverse * position * position + position**3
        if x < fraction:
            low = position
        else:
            high = position
    position = (low + high) / 2
    return 3 * (1 - position) * position * position + position**3


def number_frames(value, decimals=0, suffix=""):
    return [
        f"{value * eased(index / FRAME_COUNT):,.{decimals}f}{suffix}"
        for index in range(FRAME_COUNT)
    ]


def final_number(value, decimals=0, suffix=""):
    return f"{value:,.{decimals}f}{suffix}"


def count_styles(duration=PROGRESS_DURATION):
    css = [
        ".count-step { opacity: 0; }",
        "span.profile-count { position: relative; display: inline-block; white-space: nowrap;"
        " font-variant-numeric: tabular-nums; }",
        "span.profile-count > span.count-step { position: absolute; top: 0; left: 0; }",
        "text.profile-count { font-variant-numeric: tabular-nums; }",
        "@keyframes count-final-reveal { 0%, 99.9% { opacity: 0; } 100% { opacity: 1; } }",
        f".count-final {{ animation: count-final-reveal {duration:g}s linear both; }}",
    ]
    for index in range(FRAME_COUNT):
        start = 100 * index / FRAME_COUNT
        end = 100 * (index + 1) / FRAME_COUNT
        if index == 0:
            frames = f"0%, {end - .001:.4f}% {{ opacity: 1; }} {end:.4f}%, 100% {{ opacity: 0; }}"
        else:
            frames = (f"0%, {start - .001:.4f}% {{ opacity: 0; }} "
                      f"{start:.4f}%, {end - .001:.4f}% {{ opacity: 1; }} "
                      f"{end:.4f}%, 100% {{ opacity: 0; }}")
        css.append(f"@keyframes count-frame-{index} {{ {frames} }}")
        css.append(f".count-step-{index} {{ animation: count-frame-{index} {duration:g}s linear both; }}")
    css.append("@media (prefers-reduced-motion: reduce) {"
               " .count-final, .count-step { animation: none !important; }"
               " .count-step { opacity: 0 !important; } }")
    return "\n".join(css)


def install_styles(document):
    root = document.documentElement
    for node in list(root.getElementsByTagNameNS(SVG_NS, "style")):
        if node.getAttribute("id") == "profile-count-animations":
            root.removeChild(node)
    style = document.createElementNS(SVG_NS, "style")
    style.setAttribute("id", "profile-count-animations")
    style.appendChild(document.createTextNode(count_styles()))
    root.insertBefore(style, root.firstChild)


def html_counter(document, value, decimals=0, suffix=""):
    wrapper = document.createElementNS(XHTML_NS, "span")
    wrapper.setAttribute("class", "profile-count")
    final = document.createElementNS(XHTML_NS, "span")
    final.setAttribute("class", "count-final")
    final.appendChild(document.createTextNode(final_number(value, decimals, suffix)))
    wrapper.appendChild(final)
    for index, displayed in enumerate(number_frames(value, decimals, suffix)):
        frame = document.createElementNS(XHTML_NS, "span")
        frame.setAttribute("class", f"count-step count-step-{index}")
        frame.setAttribute("aria-hidden", "true")
        frame.appendChild(document.createTextNode(displayed))
        wrapper.appendChild(frame)
    return wrapper


def svg_counter(document, parent, value, decimals=0, suffix=""):
    parent.setAttribute("class", f"{parent.getAttribute('class')} profile-count".strip())
    x, y = parent.getAttribute("x"), parent.getAttribute("y")
    final = document.createElementNS(SVG_NS, "tspan")
    final.setAttribute("class", "count-final")
    final.setAttribute("x", x)
    final.setAttribute("y", y)
    final.appendChild(document.createTextNode(final_number(value, decimals, suffix)))
    parent.appendChild(final)
    for index, displayed in enumerate(number_frames(value, decimals, suffix)):
        frame = document.createElementNS(SVG_NS, "tspan")
        frame.setAttribute("class", f"count-step count-step-{index}")
        frame.setAttribute("x", x)
        frame.setAttribute("y", y)
        frame.setAttribute("aria-hidden", "true")
        frame.appendChild(document.createTextNode(displayed))
        parent.appendChild(frame)
