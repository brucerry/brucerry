"""Pair embedded profile text with its own background, independent of GitHub's theme."""

SVG_NS = "http://www.w3.org/2000/svg"
BACKGROUND_CSS = """
.profile-background { fill: #ffffff; }
@media (prefers-color-scheme: dark) {
  .profile-background { fill: #0d1117; }
  svg { color: #9da7b3; }
  h1, h2 { color: #58a6ff !important; }
  .all-repository-languages small,
  .all-repository-languages .language-item > div > span { color: #9da7b3 !important; }
  .all-repository-languages h2 path { stroke: #58a6ff; }
}
"""


def install_background(document):
    root = document.documentElement
    for node in list(root.childNodes):
        if node.nodeType == node.ELEMENT_NODE and node.getAttribute("id") in (
            "profile-background", "profile-theme"
        ):
            root.removeChild(node)
    style = document.createElementNS(SVG_NS, "style")
    style.setAttribute("id", "profile-theme")
    style.appendChild(document.createTextNode(BACKGROUND_CSS))
    root.appendChild(style)
    background = document.createElementNS(SVG_NS, "rect")
    for name, value in (("id", "profile-background"), ("class", "profile-background"),
                        ("width", "100%"), ("height", "100%"), ("aria-hidden", "true")):
        background.setAttribute(name, value)
    root.insertBefore(background, root.firstChild)
