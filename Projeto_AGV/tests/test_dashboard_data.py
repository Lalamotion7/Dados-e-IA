"""Garantias para os cálculos e filtros exibidos no dashboard."""
import unittest
from src.dashboard_data import load_data, filter_orders, scoped_metrics, carriers_kpis

class TestDashboardData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()
        cls.pedidos = cls.data["pedidos"]

    def test_total_e_otd_da_base(self):
        m = scoped_metrics(self.pedidos)
        self.assertEqual((m["pedidos"], m["entregues"], m["alertas"]), (60, 48, 8))
        self.assertEqual(m["otd"], 81.25)

    def test_filtro_nao_remove_nem_muda_base(self):
        n = len(self.pedidos)
        filtered = filter_orders(self.pedidos, transportadora="TRANSP_A")
        self.assertTrue((filtered["transportadora"] == "TRANSP_A").all())
        self.assertEqual(len(self.pedidos), n)

    def test_busca_literal_insensivel_a_caixa(self):
        filtered = filter_orders(self.pedidos, search="ped1008")
        self.assertEqual(filtered["id_pedido"].tolist(), ["PED1008"])
        self.assertEqual(len(filter_orders(self.pedidos, search="[")), 0)

    def test_otd_por_transportadora_recalculado(self):
        transportadoras = carriers_kpis(self.pedidos)
        self.assertEqual(len(transportadoras), 3)
        self.assertAlmostEqual(float(transportadoras[transportadoras["transportadora"] == "PARCEIRO_C"]["otd_pct"].iloc[0]), 95.24)

    def test_prioritarios_filtro(self):
        df = filter_orders(self.pedidos, situacoes=["ATRASADO_EM_ABERTO", "EM_RISCO"])
        self.assertEqual(len(df), 8)

if __name__ == "__main__":
    unittest.main()
