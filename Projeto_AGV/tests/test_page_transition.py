"""Regression: page transitions should not animate inside the sidebar or cover clicks."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class TestPageTransition(unittest.TestCase):
    def test_animation_only_when_page_changes(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('elif previous_page != page:', source)
        self.assertIn('with st.container(key=wrapper_key):', source)
        self.assertIn('"agv_page_initial" if revision == 0', source)

    def test_animation_is_accessible_and_never_blocks_clicks(self):
        css = (ROOT / "assets/theme.css").read_text(encoding="utf-8")
        self.assertIn('agv-page-circle-reveal', css)
        self.assertIn('clip-path: circle(', css)
        self.assertIn('prefers-reduced-motion: reduce', css)
        self.assertNotIn('pointer-events: none;', css.split('/* Etapa 14')[1])

if __name__ == "__main__":
    unittest.main()
