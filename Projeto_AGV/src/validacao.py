"""Validação estrutural dos CSVs ANTES de publicar uma nova execução.

Erros de rastreio (códigos desconhecidos, datas de evento inválidas, órfãos,
duplicatas lógicas) são intencionais e seguem para a trilha de qualidade.
Erros estruturais que impedem interpretar pedidos ou regras de SLA bloqueiam
uma execução e preservam os relatórios da execução anterior.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from src.diagnostico import converter_datas

ROOT = Path(__file__).resolve().parent.parent

COLUNAS = {
    "pedidos.csv": {"id_pedido", "cliente", "cidade_destino", "uf", "data_coleta", "prazo_dias_uteis", "transportadora", "valor_nf"},
    "eventos_rastreio.csv": {"id_evento", "id_pedido", "codigo_evento", "descricao", "data_hora", "fonte", "observacao"},
    "dicionario_codigos.csv": {"codigo", "significado", "ordem_esperada"},
}


class EntradaInvalida(ValueError):
    """Descrição compreensível de um erro que impede o processamento seguro."""


def carregar_csv(path: Path, requeridas: set[str]) -> pd.DataFrame:
    if not path.is_file():
        raise EntradaInvalida(f"Arquivo obrigatório não encontrado: {path.name} (pasta dados/).")
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            cabecalho = next(csv.reader(fh, delimiter=";"), [])
    except (UnicodeError, OSError, csv.Error) as exc:
        raise EntradaInvalida(f"Não foi possível ler {path.name} como CSV UTF-8: {exc}") from exc
    if not cabecalho:
        raise EntradaInvalida(f"{path.name} não possui cabeçalho.")
    if len(cabecalho) != len(set(cabecalho)):
        raise EntradaInvalida(f"{path.name} possui nomes de colunas duplicados.")
    ausentes = requeridas - set(cabecalho)
    if ausentes:
        raise EntradaInvalida(f"{path.name}: faltam colunas obrigatórias: {', '.join(sorted(ausentes))}.")
    try:
        dados = pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str)
    except (UnicodeError, OSError, pd.errors.ParserError, ValueError) as exc:
        raise EntradaInvalida(f"Não foi possível interpretar {path.name}: {exc}") from exc
    return dados


def exigir_preenchimento(df: pd.DataFrame, campos: list[str], nome: str):
    for campo in campos:
        vazios = df[campo].isna() | df[campo].astype(str).str.strip().eq("")
        if vazios.any():
            linhas = (df.index[vazios][:5] + 2).tolist()
            raise EntradaInvalida(f"{nome}: campo '{campo}' vazio na(s) linha(s) {linhas}.")


def validar_entradas(dados_dir: Path = ROOT / "dados") -> dict[str, pd.DataFrame]:
    dados_dir = Path(dados_dir)
    arquivos = {nome: carregar_csv(dados_dir / nome, required) for nome, required in COLUNAS.items()}
    pedidos = arquivos["pedidos.csv"]
    eventos = arquivos["eventos_rastreio.csv"]
    codigos = arquivos["dicionario_codigos.csv"]

    if pedidos.empty:
        raise EntradaInvalida("pedidos.csv está vazio: não é possível gerar indicadores confiáveis.")
    exigir_preenchimento(pedidos, ["id_pedido", "cliente", "data_coleta", "prazo_dias_uteis", "transportadora", "cidade_destino", "uf"], "pedidos.csv")
    ids_normalizados = pedidos["id_pedido"].str.strip()
    if ids_normalizados.duplicated().any():
        repetidos = ids_normalizados.loc[ids_normalizados.duplicated(keep=False)].unique()[:5].tolist()
        raise EntradaInvalida(f"pedidos.csv possui IDs duplicados: {', '.join(repetidos)}.")

    datas = converter_datas(pedidos["data_coleta"])
    if datas.isna().any():
        linhas = (pedidos.index[datas.isna()][:5] + 2).tolist()
        raise EntradaInvalida(f"pedidos.csv: data_coleta inválida na(s) linha(s) {linhas}.")
    prazos = pd.to_numeric(pedidos["prazo_dias_uteis"], errors="coerce")
    invalidos = prazos.isna() | prazos.lt(0) | prazos.mod(1).ne(0)
    if invalidos.any():
        linhas = (pedidos.index[invalidos][:5] + 2).tolist()
        raise EntradaInvalida(f"pedidos.csv: prazo_dias_uteis deve ser inteiro não negativo; linha(s) {linhas}.")

    if not eventos.empty:
        exigir_preenchimento(eventos, ["id_evento", "id_pedido"], "eventos_rastreio.csv")
        if eventos["id_evento"].duplicated().any():
            ids = eventos.loc[eventos["id_evento"].duplicated(keep=False), "id_evento"].unique()[:5].tolist()
            raise EntradaInvalida(f"eventos_rastreio.csv possui IDs de evento duplicados: {', '.join(ids)}.")
    # Evento com código desconhecido, data ausente, pedido órfão ou duplicata lógica
    # NÃO invalida o arquivo: o pipeline audita e isola cada anomalia.

    if codigos.empty:
        raise EntradaInvalida("dicionario_codigos.csv está vazio.")
    exigir_preenchimento(codigos, ["codigo", "ordem_esperada"], "dicionario_codigos.csv")
    nomes = codigos["codigo"].str.strip().str.upper()
    if nomes.duplicated().any():
        raise EntradaInvalida("dicionario_codigos.csv possui códigos repetidos.")
    faltantes = {"COL", "TRF", "ROT", "OCO", "ENT"} - set(nomes)
    if faltantes:
        raise EntradaInvalida(f"dicionario_codigos.csv: códigos oficiais ausentes: {', '.join(sorted(faltantes))}.")
    ordens = pd.to_numeric(codigos["ordem_esperada"], errors="coerce")
    if ordens.isna().any() or ordens.mod(1).ne(0).any() or ordens.duplicated().any():
        raise EntradaInvalida("dicionario_codigos.csv: ordem_esperada deve conter inteiros únicos.")

    return arquivos
