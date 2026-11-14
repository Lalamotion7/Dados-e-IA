import unittest
import pandas as pd
from src.ui_helpers import history_table_html, visible_text, bar_fill_percent, toggle_choice


class TestUIHelpers(unittest.TestCase):
    def test_preserva_observacao_longa_integral(self):
        texto = "Avaria na embalagem: o cliente recusou parcialmente; solicitar nova visita e reposição do lote."
        dados = pd.DataFrame([{"data_hora_dt": "19/09/2026 11:00", "codigo_normalizado": "OCO",
                               "fonte": "APP_AGV_GO", "observacao": texto}])
        html = history_table_html(dados)
        self.assertIn(texto, html)
        self.assertIn("history-observation", html)
        self.assertIn("data-label='Observação'", html)
        self.assertIn("<table", html)

    def test_escapa_html_de_texto_livre(self):
        dados = pd.DataFrame([{"data_hora_dt": "x", "codigo_normalizado": "OCO",
                               "fonte": "x", "observacao": '<script>alert("x")</script>'}])
        html = history_table_html(dados)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)

    def test_vazios_tem_traco(self):
        self.assertEqual(visible_text(None), "—")
        self.assertEqual(visible_text(float("nan")), "—")
        self.assertEqual(visible_text(" "), "—")

    def test_colunas_obrigatorias(self):
        with self.assertRaises(ValueError):
            history_table_html(pd.DataFrame([{"observacao": "teste"}]))

    def test_valores_das_barras(self):
        self.assertAlmostEqual(bar_fill_percent(72.22, 100), 72.22)
        self.assertEqual(bar_fill_percent(10, 5), 100.0)
        self.assertEqual(bar_fill_percent(1, 0), 0.0)

    def test_toggle_filtro(self):
        self.assertEqual(toggle_choice("Todas", "TRANSP_A"), "TRANSP_A")
        self.assertEqual(toggle_choice("TRANSP_A", "TRANSP_A"), "Todas")
        self.assertEqual(toggle_choice("AVARIA", "RECUSA"), "RECUSA")


if __name__ == "__main__":
    unittest.main()
