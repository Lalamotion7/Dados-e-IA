"""Comportamentos de clique e persistência, sem precisar abrir o navegador."""
import unittest
from src.dashboard_data import (
    load_data, filter_orders, selected_order_id, keep_selected_order,
    occurrence_counts, selected_occurrence_category, filter_occurrences,
)


class TestInteractivity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data()
        cls.orders = cls.data["pedidos"]
        cls.occs = cls.data["ocorrencias"]

    def test_clique_na_celula_sem_checkbox_abre_pedido(self):
        visible = filter_orders(self.orders, search="PED1012")
        self.assertEqual(
            selected_order_id({"selection": {"cells": [[0, "Pedido"]]}}, visible),
            "PED1012",
        )

    def test_clique_em_qualquer_coluna_abre_mesma_linha(self):
        visible = filter_orders(self.orders, search="PED1012")
        for column in ("Cliente", "Pedido", "Último evento", "SLA"):
            with self.subTest(column=column):
                self.assertEqual(
                    selected_order_id({"selection": {"cells": [(0, column)]}}, visible),
                    "PED1012",
                )

    def test_celula_de_outra_linha_respeita_indice_visivel(self):
        visible = filter_orders(self.orders, transportadora="PARCEIRO_C")
        self.assertEqual(
            selected_order_id({"selection": {"cells": [[1, "Cliente"]]}}, visible),
            str(visible.iloc[1]["id_pedido"]),
        )

    def test_celula_invalida_nao_seleciona_pedido(self):
        visible = filter_orders(self.orders, search="PED1012")
        self.assertIsNone(selected_order_id({"selection": {"cells": [[18, "Cliente"]]}}, visible))
        self.assertIsNone(selected_order_id({"selection": {"cells": []}}, visible))
        self.assertIsNone(selected_order_id({"selection": {"cells": [[-1, "Cliente"]]}}, visible))
        self.assertIsNone(selected_order_id({"selection": {"cells": [[True, "Cliente"]]}}, visible))
        self.assertIsNone(selected_order_id({"selection": {"cells": [["0", "Cliente"]]}}, visible))

    def test_clique_em_linha_retorna_pedido_visivel(self):
        visible = filter_orders(self.orders, search="PED1012")
        self.assertEqual(len(visible), 1)
        event = {"selection": {"rows": [0]}}
        self.assertEqual(selected_order_id(event, visible), "PED1012")

    def test_indice_de_linha_e_relativo_ao_filtro(self):
        # Preserve um índice original diferente de zero.
        visible = self.orders[self.orders["id_pedido"] == "PED1008"]
        self.assertEqual(selected_order_id({"selection": {"rows": [0]}}, visible), "PED1008")

    def test_linha_invalida_nao_abre_outro_pedido(self):
        result = filter_orders(self.orders, search="PED1012")
        self.assertIsNone(selected_order_id({"selection": {"rows": [9]}}, result))
        self.assertIsNone(selected_order_id({"selection": {"rows": []}}, result))
        self.assertIsNone(selected_order_id({"selection": {"rows": [-1]}}, result))

    def test_pedido_persiste_enquanto_visivel(self):
        filtered = filter_orders(self.orders, transportadora="PARCEIRO_C")
        self.assertEqual(keep_selected_order("PED1008", filtered), "PED1008")

    def test_pedido_some_ao_trocar_recorte(self):
        filtered = filter_orders(self.orders, transportadora="TRANSP_A")
        self.assertIsNone(keep_selected_order("PED1008", filtered))
        search = filter_orders(self.orders, search="PED1012")
        self.assertIsNone(keep_selected_order("PED1008", search))

    def test_categoria_vem_de_clique_valido_no_grafico(self):
        event = {"selection": {"points": [{"x": 6, "y": "AVARIA"}]}}
        self.assertEqual(selected_occurrence_category(event, ["AVARIA", "RECUSA"]), "AVARIA")
        self.assertIsNone(selected_occurrence_category(event, ["RECUSA"]))

    def test_categoria_multirrotulo_conta_em_ambas(self):
        counts = occurrence_counts(self.occs).set_index("categoria")["quantidade"].to_dict()
        self.assertEqual(counts["AVARIA"], 6)
        self.assertEqual(counts["RECUSA"], 2)
        self.assertEqual(sum(counts.values()), len(self.occs) + 1)

    def test_recusa_inclui_pedido_com_avaria_e_recusa(self):
        filtered = filter_occurrences(self.occs, "RECUSA")
        self.assertEqual(len(filtered), 2)
        self.assertIn("PED1012", filtered["id_pedido"].tolist())

    def test_filtro_usa_categoria_exata(self):
        self.assertEqual(len(filter_occurrences(self.occs, "AVARIA")), 6)
        self.assertTrue(filter_occurrences(self.occs, "INEXISTENTE").empty)
        self.assertEqual(len(filter_occurrences(self.occs, "Todas")), len(self.occs))

    def test_filtro_ocorrencias_respeita_transportadora(self):
        ids = set(filter_orders(self.orders, transportadora="PARCEIRO_C")["id_pedido"])
        scoped = self.occs[self.occs["id_pedido"].isin(ids)]
        filtered = filter_occurrences(scoped, "AVARIA")
        self.assertTrue(set(filtered["id_pedido"]).issubset(ids))


if __name__ == "__main__":
    unittest.main()
