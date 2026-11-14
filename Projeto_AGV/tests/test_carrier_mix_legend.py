"""Proteção contra a duplicação de legendas observada na etapa 14b."""
import unittest
from pathlib import Path
import plotly.graph_objects as go
from src.dashboard_charts import show_carrier_mix_legend


class TestCarrierMixLegend(unittest.TestCase):
    def test_unica_legenda_sem_borda_e_ordem(self):
        fig=go.Figure()
        fig.add_bar(name="No prazo", x=[20], y=["PARCEIRO_C"], orientation="h")
        fig.add_bar(name="Com atraso", x=[1], y=["PARCEIRO_C"], orientation="h")
        fig.update_layout(showlegend=True)
        show_carrier_mix_legend(fig)
        self.assertFalse(fig.layout.showlegend)
        self.assertEqual(len(fig.layout.annotations), 1)
        a=fig.layout.annotations[0]
        self.assertEqual(a.borderwidth, 0)
        self.assertEqual(a.bgcolor, "rgba(0,0,0,0)")
        self.assertEqual(a.xanchor, "right")
        self.assertLess(a.y, 0)
        self.assertLess(a.text.index("No prazo"), a.text.index("Com atraso"))
        self.assertIn("#A3E635",a.text)
        self.assertIn("#FF9F54",a.text)

    def test_sem_legenda_html_externa(self):
        root=Path(__file__).parent.parent
        app=(root/"app.py").read_text(encoding="utf-8")
        css=(root/"assets/theme.css").read_text(encoding="utf-8")
        self.assertNotIn("carrier-mix-legend", app)
        self.assertNotIn("carrier-mix-legend", css)
        self.assertEqual(app.count("show_carrier_mix_legend(fig)"), 1)
        self.assertIn("Interface v14d", app)

if __name__=="__main__":
    unittest.main()
