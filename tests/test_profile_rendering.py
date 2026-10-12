"""Offline regression checks for generated profile presentation."""

from pathlib import Path
import sys
import unittest
from xml.dom import minidom
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from add_leetcode_to_metrics import add_card
from make_mobile_metrics import make_mobile
from profile_theme import install_background
from progress_numbers import count_styles

SVG = 'http://www.w3.org/2000/svg'


class ProfileRenderingTests(unittest.TestCase):
    def test_background_is_idempotent_and_behind_content(self):
        doc = minidom.parse(str(ROOT / 'github-metrics.svg'))
        install_background(doc)
        first = doc.toxml()
        install_background(doc)
        self.assertEqual(first, doc.toxml())
        root = doc.documentElement
        self.assertEqual(root.firstChild.getAttribute('id'), 'profile-background')
        backgrounds = [node for node in root.childNodes if node.nodeType == node.ELEMENT_NODE
                       and node.getAttribute('id') == 'profile-background']
        self.assertEqual(len(backgrounds), 1)
        self.assertEqual(backgrounds[0].getAttribute('height'), '100%')

    def test_future_leetcode_updates_keep_theme_and_motion(self):
        doc = minidom.parse(str(ROOT / 'github-metrics.svg'))
        stats = ({'All': 100, 'Easy': 30, 'Medium': 50, 'Hard': 20},
                 {'All': 60, 'Easy': 20, 'Medium': 30, 'Hard': 10},
                 [{'tagName': 'Array', 'problemsSolved': 50}])
        add_card(doc, stats)
        mobile = make_mobile(doc)
        for output in (doc.toxml(), ET.tostring(mobile, encoding='unicode')):
            self.assertIn('profile-background', output)
            self.assertIn('#ffffff', output)
            self.assertIn('#0d1117', output)
            self.assertNotIn('prefers-reduced-motion', output)
            self.assertIn('count-final-reveal 1.5s', output)
        final_counts = [node.text for node in mobile.iter(f'{{{SVG}}}tspan')
                        if node.get('class') == 'count-final']
        self.assertIn('60 / 100', final_counts)
        self.assertIn('60.0%', final_counts)
        self.assertIn('Array · 50', [node.text for node in mobile.iter(f'{{{SVG}}}text')])

    def test_mobile_artifact_matches_generator(self):
        doc = minidom.parse(str(ROOT / 'github-metrics.svg'))
        generated = ET.tostring(make_mobile(doc), encoding='utf-8', xml_declaration=True)
        checked_in = (ROOT / 'github-metrics-mobile.svg').read_bytes()
        self.assertEqual(ET.tostring(ET.fromstring(generated)),
                         ET.tostring(ET.fromstring(checked_in)))
        self.assertNotIn(b'foreignObject', generated)

    def test_checked_in_artifacts_are_valid_and_animated(self):
        for filename in ('github-metrics.svg', 'github-metrics-mobile.svg'):
            with self.subTest(filename=filename):
                data = (ROOT / filename).read_bytes()
                root = ET.fromstring(data)
                self.assertEqual(root.tag, f'{{{SVG}}}svg')
                self.assertEqual(len([n for n in root if n.get('id') == 'profile-background']), 1)
                self.assertNotIn(b'prefers-reduced-motion', data)
                self.assertIn(b'animation:', data)
        self.assertNotIn('animation: none', count_styles())


if __name__ == '__main__':
    unittest.main()
