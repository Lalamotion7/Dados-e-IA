"""Teste da Etapa 3 sem serviços externos e sem depender de resultados pré-gerados."""
import unittest
import pandas as pd
from src.diagnostico import REFERENCIA
from src.rastreamento import carregar_dados, tratar_eventos, consolidar_pedidos
from src.sla import (
    calcular_vencimento, calcular_sla, produzir_indicadores,
    ENTREGUE_NO_PRAZO, ENTREGUE_COM_ATRASO, ATRASADO_EM_ABERTO,
    EM_RISCO, NO_PRAZO_EM_ABERTO,
)

class TestSLA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pedidos, eventos, dicionario = carregar_dados()
        validos, _ = tratar_eventos(pedidos, eventos, dicionario)
        cls.pedidos = calcular_sla(consolidar_pedidos(pedidos, validos))
        cls.geral, cls.transportadoras, cls.contagem = produzir_indicadores(cls.pedidos)

    def test_vencimento_ignora_fim_de_semana(self):
        self.assertEqual(
            calcular_vencimento(pd.Timestamp('2026-09-11 09:30'), 2),
            pd.Timestamp('2026-09-15 09:30')
        )

    def test_vencimento_mantem_hora_da_coleta(self):
        self.assertEqual(
            calcular_vencimento(pd.Timestamp('2026-09-10 17:00'), 3),
            pd.Timestamp('2026-09-15 17:00')
        )

    def test_preserva_60_pedidos_e_classifica_todos(self):
        self.assertEqual(len(self.pedidos), 60)
        self.assertEqual(self.pedidos['situacao_sla'].isna().sum(), 0)
        self.assertEqual(self.contagem['quantidade'].sum(), 60)

    def test_otd_geral(self):
        r = self.geral.iloc[0]
        self.assertEqual(int(r['total_entregues']), 48)
        self.assertEqual(int(r['entregues_no_prazo']), 39)
        self.assertAlmostEqual(float(r['otd_pct']), 81.25)

    def test_contagens(self):
        n = self.contagem.set_index('situacao_sla')['quantidade']
        self.assertEqual(int(n[ENTREGUE_NO_PRAZO]), 39)
        self.assertEqual(int(n[ENTREGUE_COM_ATRASO]), 9)
        self.assertEqual(int(n[ATRASADO_EM_ABERTO]), 5)
        self.assertEqual(int(n[EM_RISCO]), 3)
        self.assertEqual(int(n[NO_PRAZO_EM_ABERTO]), 4)

    def test_pedidos_sem_eventos_entraram_no_sla(self):
        r = self.pedidos.set_index('id_pedido')
        self.assertEqual(r.loc['PED1008', 'situacao_sla'], ATRASADO_EM_ABERTO)
        self.assertEqual(r.loc['PED1034', 'situacao_sla'], EM_RISCO)

    def test_entrega_invalidada_nao_contamina_otd(self):
        r = self.pedidos.set_index('id_pedido').loc['PED1012']
        self.assertEqual(pd.Timestamp(r['data_entrega']), pd.Timestamp('2026-09-21 10:00'))
        self.assertIn(r['situacao_sla'], [ENTREGUE_NO_PRAZO, ENTREGUE_COM_ATRASO])

    def test_otd_por_transportadora(self):
        t = self.transportadoras.set_index('transportadora')
        self.assertAlmostEqual(t.loc['TRANSP_A', 'otd_pct'], 72.22)
        self.assertAlmostEqual(t.loc['TRANSP_B', 'otd_pct'], 66.67)
        self.assertAlmostEqual(t.loc['PARCEIRO_C', 'otd_pct'], 95.24)

    def test_entrega_exatamente_no_vencimento_e_pontual(self):
        c = pd.DataFrame([{
            'id_pedido':'T', 'data_coleta':'2026-09-21 10:00:00',
            'prazo_dias_uteis':2, 'data_entrega':pd.Timestamp('2026-09-23 10:00')
        }])
        self.assertEqual(calcular_sla(c).loc[0,'situacao_sla'], ENTREGUE_NO_PRAZO)

    def test_em_risco_exatamente_24h_antes(self):
        c = pd.DataFrame([{
            'id_pedido':'T', 'data_coleta':'2026-09-21 18:00:00',
            'prazo_dias_uteis':4, 'data_entrega':pd.NaT
        }])
        # 25/09/2026 18h, exatamente 24h depois da referência
        self.assertEqual(calcular_sla(c, REFERENCIA).loc[0,'situacao_sla'], EM_RISCO)

    def test_atrasado_se_prazo_passou(self):
        c = pd.DataFrame([{
            'id_pedido':'T', 'data_coleta':'2026-09-21 10:00:00',
            'prazo_dias_uteis':2, 'data_entrega':pd.NaT
        }])
        self.assertEqual(calcular_sla(c).loc[0, 'situacao_sla'], ATRASADO_EM_ABERTO)

if __name__ == '__main__':
    unittest.main()
