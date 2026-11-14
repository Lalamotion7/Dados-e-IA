"""Etapa 12: segurança e apresentação das tabelas não editáveis."""
import unittest
from pathlib import Path
import pandas as pd
from src.ui_helpers import readonly_table_html


class TestReadonlyTable(unittest.TestCase):
    def test_celulas_e_cabecalhos_sao_escapados(self):
        df = pd.DataFrame({'<script>': ['<img src=x onerror=alert(1)>']})
        html = readonly_table_html(df, 'Auditoria <alert>')
        self.assertNotIn('<script>', html)
        self.assertNotIn('<img src=', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('&lt;img src=x onerror=alert(1)&gt;', html)
        self.assertIn('Auditoria &lt;alert&gt;', html)

    def test_valores_nulos_sao_legiveis(self):
        df = pd.DataFrame({'Pedido':['PED1008'], 'Observação':[None]})
        html = readonly_table_html(df, 'Alertas')
        self.assertIn('<td>—</td>', html)
        self.assertNotIn('>None<', html)

    def test_preserva_todas_as_linhas_em_ordem(self):
        df = pd.DataFrame({'Pedido':['PED1022','PED1008','PED1034']})
        html = readonly_table_html(df, 'Pedidos em alerta')
        self.assertEqual(html.count('<tbody><tr>') + html.count('</tr><tr>'), 3)
        self.assertLess(html.index('PED1022'), html.index('PED1008'))
        self.assertLess(html.index('PED1008'), html.index('PED1034'))

    def test_sem_elementos_editaveis_ou_selecao_de_celula(self):
        html = readonly_table_html(pd.DataFrame({'A':['x']}), 'Teste')
        for s in ['contenteditable', 'input ', 'onclick', 'selection_mode', 'stDataFrame']:
            self.assertNotIn(s, html)
        self.assertIn("role='region'", html)
        self.assertIn("tabindex='0'", html)

    def test_tabela_vazia_retorna_mensagem(self):
        html = readonly_table_html(pd.DataFrame(columns=['Pedido']), 'Pedidos')
        self.assertIn('Nenhum registro neste filtro.', html)
        self.assertEqual(html.count('<thead>'), 1)

    def test_altura_limitada_e_escapada(self):
        h = readonly_table_html(pd.DataFrame({'A':[1]}), 'D', max_height=9000)
        self.assertIn('720px',h)
        h2 = readonly_table_html(pd.DataFrame({'A':[1]}), 'D', max_height=10)
        self.assertIn('120px',h2)

    def test_aplicacao_nao_usa_dataframe_nativo_em_consultas(self):
        source = (Path(__file__).resolve().parents[1] / 'app.py').read_text(encoding='utf-8')
        self.assertNotIn('st.dataframe(', source)
        self.assertIn('selected_order_from_grid', source)

    def test_animacao_apenas_visao_geral(self):
        source = (Path(__file__).resolve().parents[1] / 'app.py').read_text(encoding='utf-8')
        self.assertEqual(source.count('animated=True'),1)
        self.assertIn('title("Tracking Intelligence"',source)
        css = (Path(__file__).resolve().parents[1] / 'assets' / 'theme.css').read_text(encoding='utf-8')
        self.assertIn('prefers-reduced-motion:reduce',css)

if __name__ == '__main__':
    unittest.main()
