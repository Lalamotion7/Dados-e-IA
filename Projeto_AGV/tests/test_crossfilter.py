"""Garante que o clique no gráfico aplica um recorte válido ao restante do dashboard."""
import unittest
from src.dashboard_data import (load_data, filter_orders, scoped_metrics,
                                 selected_carrier, filter_quality_by_orders,
                                 carriers_kpis)


class TestCrossfilter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()
        cls.carriers = sorted(cls.data["pedidos"]["transportadora"].unique().tolist())

    def test_clique_na_barra_retorna_transportadora(self):
        event = {"selection": {"points": [{"point_index": 1, "x": 72.22, "y": "TRANSP_A"}]}}
        self.assertEqual(selected_carrier(event, self.carriers), "TRANSP_A")

    def test_nao_confia_em_identificador_inexistente(self):
        event = {"selection": {"points": [{"y": "TRANSP_FALSA"}]}}
        self.assertIsNone(selected_carrier(event, self.carriers))

    def test_deselecao_nao_retorna_transportadora(self):
        self.assertIsNone(selected_carrier({"selection": {"points": []}}, self.carriers))

    def test_indicadores_seguem_recorte_da_barra(self):
        event = {"selection": {"points": [{"y": "TRANSP_A"}]}}
        carrier = selected_carrier(event, self.carriers)
        scoped = filter_orders(self.data["pedidos"], carrier)
        metrics = scoped_metrics(scoped)
        self.assertEqual(metrics["entregues"], 18)
        self.assertEqual(metrics["pontuais"], 13)
        self.assertEqual(metrics["otd"], 72.22)
        self.assertEqual(set(scoped["transportadora"]), {"TRANSP_A"})

    def test_grafico_permanece_com_todas_as_transportadoras(self):
        carriers = carriers_kpis(self.data["pedidos"])
        self.assertEqual(len(carriers), 3)

    def test_qualidade_obedece_recorte_sem_atribuir_orfaos(self):
        orders = filter_orders(self.data["pedidos"], "TRANSP_A")
        diag, audit = filter_quality_by_orders(self.data["qualidade"], self.data["auditoria"], orders, "TRANSP_A")
        ids = set(orders["id_pedido"])
        self.assertTrue(set(diag["id_pedido"]).issubset(ids))
        self.assertTrue(set(audit["id_pedido"]).issubset(ids))
        self.assertTrue(len(audit) > 0)

    def test_global_mantem_eventos_orfaos(self):
        diag, audit = filter_quality_by_orders(self.data["qualidade"], self.data["auditoria"],
                                                self.data["pedidos"], "Todas")
        self.assertEqual(len(audit), 232)
        self.assertIn("evento_sem_pedido", diag["problema"].tolist())


if __name__ == "__main__":
    unittest.main()
