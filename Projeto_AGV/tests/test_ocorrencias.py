"""Testes das classificacoes e dos alertas, partindo somente dos CSVs de entrada."""
import unittest

import pandas as pd

from src.rastreamento import carregar_dados, consolidar_pedidos, tratar_eventos
from src.sla import calcular_sla, ATRASADO_EM_ABERTO, EM_RISCO
from src.ocorrencias import (
    normalizar_texto, classificar_observacao, classificar_ocorrencias,
    frequencia_categorias, gerar_alertas, mensagem_alerta,
)


class TestOcorrencias(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pedidos, eventos, dicionario = carregar_dados()
        cls.validos, _ = tratar_eventos(pedidos, eventos, dicionario)
        cls.ocorrencias = classificar_ocorrencias(cls.validos)
        cls.pedidos_sla = calcular_sla(consolidar_pedidos(pedidos, cls.validos))
        cls.alertas = gerar_alertas(cls.pedidos_sla, cls.ocorrencias)

    def test_remove_acentos_e_normaliza(self):
        self.assertEqual(normalizar_texto("  Cliente AUSÊNTE  "), "cliente ausente")

    def test_classifica_ausencia(self):
        self.assertEqual(classificar_observacao("Cliente ausente, ninguém atendeu"), ["AUSENCIA"])

    def test_classifica_endereco(self):
        self.assertEqual(classificar_observacao("Endereço não localizado, número inexistente"), ["ENDERECO"])

    def test_classifica_acesso_impedido(self):
        self.assertEqual(classificar_observacao("portaria fechada"), ["ACESSO_IMPEDIDO"])

    def test_classifica_chuva_como_avaria(self):
        self.assertEqual(classificar_observacao("mercadoria molhada pela chuva"), ["AVARIA"])

    def test_multiplas_categorias(self):
        self.assertEqual(classificar_observacao("avaria na embalagem, cliente recusou parcialmente"), ["AVARIA", "RECUSA"])

    def test_texto_ausente_e_nao_reconhecido(self):
        self.assertEqual(classificar_observacao(None), ["SEM_DESCRICAO"])
        self.assertEqual(classificar_observacao("Outra situacao incomum"), ["OUTROS"])

    def test_dez_ocorrencias_validas(self):
        self.assertEqual(len(self.ocorrencias), 10)
        self.assertTrue((self.ocorrencias["metodo"] == "REGRAS_PALAVRAS_CHAVE").all())
        self.assertEqual(self.ocorrencias["categoria_principal"].eq("OUTROS").sum(), 0)

    def test_exemplo_ocorrencia_multirrotulo(self):
        linha = self.ocorrencias.set_index("id_pedido").loc["PED1012"]
        self.assertEqual(linha["categorias"], "AVARIA|RECUSA")

    def test_total_categoria_supera_ocorrencias_em_multirrotulo(self):
        frequencias = frequencia_categorias(self.ocorrencias)
        self.assertEqual(int(frequencias["quantidade"].sum()), len(self.ocorrencias) + 1)

    def test_alertas_total_e_classificacao(self):
        self.assertEqual(len(self.alertas), 8)
        situacoes = self.alertas["situacao_sla"].value_counts()
        self.assertEqual(int(situacoes[ATRASADO_EM_ABERTO]), 5)
        self.assertEqual(int(situacoes[EM_RISCO]), 3)
        self.assertEqual(self.alertas["id_pedido"].nunique(), 8)

    def test_sem_rastreio_tem_acao(self):
        linha = self.alertas.set_index("id_pedido").loc["PED1008"]
        self.assertEqual(linha["status_atual"], "SEM_RASTREIO")
        self.assertIn("localizar pedido", linha["acao_sugerida"])

    def test_ocorrencia_relevante_e_incluida_no_alerta(self):
        linha = self.alertas.set_index("id_pedido").loc["PED1022"]
        self.assertEqual(linha["categoria_ocorrencia"], "AVARIA")
        self.assertIn("transportadora", linha["acao_sugerida"])

    def test_entregue_com_ocorrencia_nao_gera_alerta_de_sla(self):
        self.assertIn("PED1012", set(self.ocorrencias["id_pedido"]))
        self.assertNotIn("PED1012", set(self.alertas["id_pedido"]))

    def test_alerta_e_simulado_sem_envio_real(self):
        texto = mensagem_alerta(self.alertas)
        self.assertIn("[SIMULACAO]", texto)
        self.assertIn("Pedidos que exigem acao: 8", texto)
        self.assertIn("24/09/2026", texto)
        self.assertIn("PED1034", texto)
        self.assertIn("nenhum e-mail", texto)


if __name__ == "__main__":
    unittest.main()
