"""Testes de regressao da etapa 2 usando os arquivos ficticios do desafio.

Executar na raiz do projeto: python -m unittest discover -s tests -v
"""
import unittest

import pandas as pd

from src.rastreamento import carregar_dados, tratar_eventos, consolidar_pedidos


class TestRastreamento(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pedidos, cls.eventos, cls.dicionario = carregar_dados()
        cls.validos, cls.auditoria = tratar_eventos(cls.pedidos, cls.eventos, cls.dicionario)
        cls.consolidado = consolidar_pedidos(cls.pedidos, cls.validos)

    def test_preserva_todos_os_pedidos(self):
        self.assertEqual(len(self.consolidado), 60)
        self.assertEqual(self.consolidado["id_pedido"].nunique(), 60)

    def test_auditoria_nao_apaga_eventos(self):
        self.assertEqual(len(self.auditoria), 232)
        self.assertEqual(len(self.validos), 225)
        self.assertEqual((self.auditoria["decisao"] == "QUARENTENA").sum(), 7)

    def test_duplicados_nao_contam_duas_vezes(self):
        self.assertEqual((self.auditoria["motivo"] == "evento_duplicado").sum(), 4)

    def test_pedido_sem_rastreio_continua_na_base(self):
        sem_rastreio = self.consolidado.set_index("id_pedido").loc[["PED1008", "PED1034"]]
        self.assertTrue((sem_rastreio["status_atual"] == "SEM_RASTREIO").all())
        self.assertTrue(sem_rastreio["data_hora_ultimo_evento"].isna().all())

    def test_entrega_anterior_coleta_e_desconsiderada(self):
        anomalia = self.auditoria.loc[self.auditoria["id_evento"] == "231"].iloc[0]
        self.assertEqual(anomalia["motivo"], "evento_anterior_coleta")
        pedido = self.consolidado.set_index("id_pedido").loc["PED1012"]
        self.assertEqual(pd.Timestamp(pedido["data_entrega"]), pd.Timestamp("2026-09-21 10:00:00"))
        self.assertEqual(pedido["status_atual"], "ENT")

    def test_normaliza_entregue(self):
        normalizados = self.validos.loc[self.validos["codigo_evento"] == "ENTREGUE"]
        self.assertEqual(len(normalizados), 5)
        self.assertTrue((normalizados["codigo_normalizado"] == "ENT").all())

    def test_evento_sem_data_nao_sobrescreve_ultima_entrega(self):
        pedido = self.consolidado.set_index("id_pedido").loc["PED1020"]
        self.assertEqual(pedido["status_atual"], "ENT")
        self.assertEqual(pd.Timestamp(pedido["data_hora_ultimo_evento"]), pd.Timestamp("2026-09-12 23:00:00"))


if __name__ == "__main__":
    unittest.main()
