"""Testes com entradas alteradas; não modificam os CSVs originais da AGV."""
from __future__ import annotations

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src import main as pipeline
from src.validacao import validar_entradas, EntradaInvalida
from src.dashboard_data import selected_order_from_grid

ROOT = Path(__file__).resolve().parent.parent


class TestReprocessamento(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.dados = self.root / "dados"
        self.dados.mkdir()
        for csv in (ROOT / "dados").glob("*.csv"):
            shutil.copy2(csv, self.dados / csv.name)
        self.output = self.root / "output"

    def tearDown(self):
        self.temp.cleanup()

    def orders(self):
        return pd.read_csv(self.dados / "pedidos.csv", sep=";", dtype=str)

    def save_orders(self, df):
        df.to_csv(self.dados / "pedidos.csv", sep=";", index=False)

    def test_entrada_original_preserva_eventos_com_anomalias(self):
        arquivos = validar_entradas(self.dados)
        self.assertEqual(len(arquivos["pedidos.csv"]), 60)
        self.assertEqual(len(arquivos["eventos_rastreio.csv"]), 232)

    def test_coluna_ausente_da_erro_claro(self):
        df = self.orders().drop(columns="id_pedido")
        self.save_orders(df)
        with self.assertRaisesRegex(EntradaInvalida, "id_pedido"):
            pipeline.main(self.dados, self.output)
        self.assertFalse(self.output.exists())

    def test_pedido_repetido_impede_publicacao(self):
        df = self.orders()
        self.save_orders(pd.concat([df, df.iloc[[0]]], ignore_index=True))
        with self.assertRaisesRegex(EntradaInvalida, "IDs duplicados"):
            pipeline.main(self.dados, self.output)

    def test_prazo_invalido_impede_publicacao(self):
        df = self.orders()
        df.loc[0, "prazo_dias_uteis"] = "-2"
        self.save_orders(df)
        with self.assertRaisesRegex(EntradaInvalida, "prazo_dias_uteis"):
            pipeline.main(self.dados, self.output)

    def test_novo_pedido_sem_rastreio_entra_na_base_e_manifesto(self):
        primeira = pipeline.main(self.dados, self.output)
        self.assertFalse(primeira["alteracoes"]["comparacao_disponivel"])
        df = self.orders()
        novo = df.iloc[[-1]].copy()
        novo["id_pedido"] = "PED1061"
        novo["data_coleta"] = "2026-09-23 09:00:00"
        self.save_orders(pd.concat([df, novo], ignore_index=True))
        result = pipeline.main(self.dados, self.output)
        self.assertEqual(result["metricas"]["pedidos"], 61)
        self.assertEqual(result["alteracoes"]["novos_pedidos"], 1)
        self.assertEqual(result["metricas"]["eventos"], 232)
        consolidado = pd.read_csv(self.output / "pedidos_sla.csv", sep=";")
        self.assertEqual(consolidado[consolidado.id_pedido == "PED1061"].iloc[0].status_atual, "SEM_RASTREIO")

    def test_reprocessar_sem_alteracoes_nao_cria_novos_pedidos(self):
        pipeline.main(self.dados, self.output)
        again = pipeline.main(self.dados, self.output)
        self.assertEqual(again["alteracoes"]["novos_pedidos"], 0)
        self.assertEqual(again["alteracoes"]["novos_eventos"], 0)
        self.assertEqual(again["metricas"]["otd_pct"], 81.25)

    def test_erro_estrutural_depois_de_sucesso_preserva_todos_relatorios(self):
        pipeline.main(self.dados, self.output)
        antes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.output.iterdir() if p.is_file()}
        df = self.orders()
        df.loc[0, "data_coleta"] = "nunca"
        self.save_orders(df)
        with self.assertRaises(EntradaInvalida):
            pipeline.main(self.dados, self.output)
        depois = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.output.iterdir() if p.is_file()}
        self.assertEqual(antes, depois)
        self.assertFalse((self.root / "output_backup_publicacao").exists())

    def test_falha_terceira_etapa_preserva_publicacao_anterior(self):
        pipeline.main(self.dados, self.output)
        anterior = (self.output / "pedidos_sla.csv").read_bytes()
        original = pipeline.executar_sla
        with patch.object(pipeline, "executar_sla", side_effect=RuntimeError("Falha simulada do SLA")):
            with self.assertRaisesRegex(RuntimeError, "Falha simulada"):
                pipeline.main(self.dados, self.output)
        self.assertEqual((self.output / "pedidos_sla.csv").read_bytes(), anterior)
        self.assertEqual(len(list(self.root.glob(".agv_staging_*"))), 0)

    def test_publicacao_reverte_se_staging_nao_puder_ser_renomeado(self):
        pipeline.main(self.dados, self.output)
        anterior = (self.output / "pedidos_sla.csv").read_bytes()
        folder = self.root / "novo_stage"
        folder.mkdir()
        (folder / "teste").write_text("novo")
        original_rename = Path.rename
        def falhar_so_staging(path, target):
            if Path(path) == folder:
                raise OSError("Falha de publicação simulada")
            return original_rename(path, target)
        with patch.object(Path, "rename", falhar_so_staging):
            with self.assertRaisesRegex(OSError, "simulada"):
                pipeline.publicar(folder, self.output)
        self.assertEqual((self.output / "pedidos_sla.csv").read_bytes(), anterior)
        self.assertFalse((self.root / "output_backup_publicacao").exists())


class TestSelecaoGrid(unittest.TestCase):
    def setUp(self):
        self.orders = pd.DataFrame({"id_pedido": ["PED1001", "PED1002"]})

    def test_retorna_pedido_em_vez_de_posicao_da_celula(self):
        response = {"selected_rows": [{"Pedido": "PED1002", "Cliente": "Teste"}]}
        self.assertEqual(selected_order_from_grid(response, self.orders), "PED1002")

    def test_aceita_dataframe_de_retorno(self):
        response = {"selected_rows": pd.DataFrame([{"Pedido": "PED1001"}])}
        self.assertEqual(selected_order_from_grid(response, self.orders), "PED1001")

    def test_nao_seleciona_pedido_de_outro_filtro(self):
        self.assertIsNone(selected_order_from_grid({"selected_rows": [{"Pedido": "PED1061"}]}, self.orders))
        self.assertIsNone(selected_order_from_grid({"selected_rows": []}, self.orders))
