"""Offline regression checks for transparent, theme-specific profile metrics."""

from html.parser import HTMLParser
import os
from pathlib import Path
import sys
import unittest
from xml.dom import minidom
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(os.environ.get('PROFILE_METRICS_DIR', ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

from add_leetcode_to_metrics import add_card
from make_mobile_metrics import make_mobile
from profile_theme import install_theme, PALETTES, theme_css
from progress_numbers import count_styles

SVG = 'http://www.w3.org/2000/svg'


def assert_transparent(test, root):
    test.assertFalse(any(node.get('id') == 'profile-background' for node in root))
    for node in root:
        if node.tag == f'{{{SVG}}}rect':
            test.assertFalse(node.get('width') in ('100%', root.get('width'))
                             and node.get('height') in ('100%', root.get('height')))


class ProfileRenderingTests(unittest.TestCase):
    def test_palette_is_idempotent_and_removes_old_opaque_background(self):
        doc = minidom.parse(str(ASSETS / 'github-metrics.svg'))
        background = doc.createElementNS(SVG, 'rect')
        background.setAttribute('id', 'profile-background')
        background.setAttribute('width', '100%')
        background.setAttribute('height', '100%')
        doc.documentElement.insertBefore(background, doc.documentElement.firstChild)
        for theme in PALETTES:
            install_theme(doc, theme)
            first = doc.toxml()
            install_theme(doc, theme)
            self.assertEqual(first, doc.toxml())
            root = ET.fromstring(first)
            assert_transparent(self, root)
            self.assertEqual(root.get('data-profile-theme'), theme)
            self.assertEqual(len([node for node in root if node.get('id') == 'profile-theme']), 1)

    def test_future_updates_keep_transparency_theme_and_motion(self):
        doc = minidom.parse(str(ASSETS / 'github-metrics.svg'))
        stats = ({'All': 100, 'Easy': 30, 'Medium': 50, 'Hard': 20},
                 {'All': 60, 'Easy': 20, 'Medium': 30, 'Hard': 10},
                 [{'tagName': 'Array', 'problemsSolved': 50}])
        add_card(doc, stats)
        for theme in PALETTES:
            install_theme(doc, theme)
            mobile = make_mobile(doc, theme)
            for output in (doc.toxml(), ET.tostring(mobile, encoding='unicode')):
                assert_transparent(self, ET.fromstring(output))
                styles = '\n'.join(node.text or '' for node in ET.fromstring(output).iter(f'{{{SVG}}}style'))
                self.assertIn(theme_css(theme).strip(), styles)
                self.assertNotIn('prefers-reduced-motion', output)
                self.assertNotIn('prefers-color-scheme', output)
                self.assertIn('count-final-reveal 1.5s', output)
            final_counts = [node.text for node in mobile.iter(f'{{{SVG}}}tspan')
                            if node.get('class') == 'count-final']
            self.assertIn('60 / 100', final_counts)
            self.assertIn('60.0%', final_counts)
            self.assertIn('Array \u00b7 50', [node.text for node in mobile.iter(f'{{{SVG}}}text')])

    def test_mobile_artifacts_match_generator(self):
        for theme, suffix in (('light', ''), ('dark', '-dark')):
            doc = minidom.parse(str(ASSETS / f'github-metrics{suffix}.svg'))
            generated = ET.tostring(make_mobile(doc, theme), encoding='utf-8')
            checked_in = (ASSETS / f'github-metrics-mobile{suffix}.svg').read_bytes()
            self.assertEqual(ET.tostring(ET.fromstring(generated)),
                             ET.tostring(ET.fromstring(checked_in)))
            self.assertNotIn(b'foreignObject', generated)

    def test_desktop_dark_artifact_matches_palette_conversion(self):
        doc = minidom.parse(str(ASSETS / 'github-metrics.svg'))
        install_theme(doc, 'dark')
        actual = ET.parse(ASSETS / 'github-metrics-dark.svg').getroot()
        self.assertEqual(ET.tostring(ET.fromstring(doc.toxml())), ET.tostring(actual))

    def test_artifacts_are_transparent_and_animated(self):
        for suffix in ('', '-dark'):
            for mobile in ('', '-mobile'):
                filename = f'github-metrics{mobile}{suffix}.svg'
                with self.subTest(filename=filename):
                    data = (ASSETS / filename).read_bytes()
                    root = ET.fromstring(data)
                    self.assertEqual(root.tag, f'{{{SVG}}}svg')
                    assert_transparent(self, root)
                    self.assertEqual(root.get('data-profile-theme'), 'dark' if suffix else 'light')
                    self.assertNotIn(b'prefers-reduced-motion', data)
                    self.assertNotIn(b'prefers-color-scheme', data)
                    self.assertIn(b'animation:', data)
        self.assertNotIn('animation: none', count_styles())

    def test_readme_uses_github_theme_links_with_mobile_sources(self):
        class Images(HTMLParser):
            def __init__(self):
                super().__init__()
                self.links = []
                self.current = None

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'a':
                    self.current = {'href': attrs['href']}
                    self.links.append(self.current)
                elif tag in ('source', 'img') and self.current is not None:
                    self.current[tag] = attrs

            def handle_endtag(self, tag):
                if tag == 'a':
                    self.current = None

        parser = Images()
        parser.feed((ROOT / 'README.md').read_text(encoding='utf-8'))
        self.assertEqual(len(parser.links), 2)
        for link, theme, suffix in zip(parser.links, ('light', 'dark'), ('', '-dark')):
            self.assertTrue(link['href'].endswith(f'github-metrics{suffix}.svg#gh-{theme}-mode-only'))
            self.assertEqual(link['source']['media'], '(max-width: 600px)')
            self.assertTrue(link['source']['srcset'].endswith(f'github-metrics-mobile{suffix}.svg'))
            self.assertTrue(link['img']['src'].endswith(f'github-metrics{suffix}.svg'))


if __name__ == '__main__':
    unittest.main()
