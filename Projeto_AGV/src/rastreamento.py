"""Etapa 2: normalizacao, trilha de auditoria e visao consolidada por pedido.

Execucao (na raiz do projeto): python -m src.rastreamento

Nao altera os arquivos originais. A data de referencia eh fixa pelo desafio.
"""
from pathlib import Path

import pandas as pd

from src.diagnostico import converter_datas, REFERENCIA

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
SAIDAS = RAIZ / "output"


def carregar_dados(dados_dir: Path = DADOS):
    """Le CSVs com IDs sempre tratados como texto."""
    dados_dir = Path(dados_dir)
    pedidos = pd.read_csv(dados_dir / "pedidos.csv", sep=";", encoding="utf-8-sig", dtype=str)
    eventos = pd.read_csv(dados_dir / "eventos_rastreio.csv", sep=";", encoding="utf-8-sig", dtype=str)
    dicionario = pd.read_csv(dados_dir / "dicionario_codigos.csv", sep=";", encoding="utf-8-sig", dtype=str)
    return pedidos, eventos, dicionario


def tratar_eventos(pedidos: pd.DataFrame, eventos: pd.DataFrame, dicionario: pd.DataFrame):
    """Devolve eventos validos e auditoria de TODOS os eventos com seus tratamentos.

    Registros inconsistentes ficam na auditoria, mas nao determinam status.
    Nao confundir linhas descartadas da visao operacional com dados apagados.
    """
    pedidos = pedidos.copy()
    ev = eventos.copy()

    pedidos["data_coleta_dt"] = converter_datas(pedidos["data_coleta"])
    ev["codigo_normalizado"] = (
        ev["codigo_evento"].fillna("").str.strip().str.upper().replace({"ENTREGUE": "ENT"})
    )
    ev["data_hora_dt"] = converter_datas(ev["data_hora"])
    ev["fonte_chave"] = ev["fonte"].fillna("").str.strip().str.upper()
    ev["observacao_chave"] = ev["observacao"].fillna("").str.strip().str.lower()
    ev["id_evento_numerico"] = pd.to_numeric(ev["id_evento"], errors="coerce")
    ev["prioridade_codigo"] = ev["codigo_normalizado"].map(
        dicionario.assign(
            codigo=dicionario["codigo"].str.strip().str.upper(),
            ordem_esperada=pd.to_numeric(dicionario["ordem_esperada"], errors="coerce"),
        ).set_index("codigo")["ordem_esperada"]
    )

    # Vincula a coleta; todos os eventos permanecem na auditoria, inclusive orfaos.
    ev = ev.merge(pedidos[["id_pedido", "data_coleta_dt"]], on="id_pedido", how="left", validate="many_to_one")

    # A mesma chave logica pode aparecer em IDs diferentes.
    # O menor ID fica como representante quando os registros sao equivalentes.
    ev = ev.sort_values(["id_evento_numerico", "id_evento"], kind="stable", na_position="last")
    chave = ["id_pedido", "codigo_normalizado", "data_hora_dt", "fonte_chave", "observacao_chave"]
    duplicado = ev.duplicated(subset=chave, keep="first")

    codigos_validos = set(dicionario["codigo"].str.strip().str.upper())
    ids_validos = set(pedidos["id_pedido"])

    # Regras com prioridade clara: uma linha recebe um motivo principal de exclusao.
    ev["decisao"] = "UTILIZADO"
    ev["motivo"] = ""

    def quarentena(mascara: pd.Series, motivo: str):
        alvo = mascara & (ev["decisao"] == "UTILIZADO")
        ev.loc[alvo, "decisao"] = "QUARENTENA"
        ev.loc[alvo, "motivo"] = motivo

    quarentena(~ev["id_pedido"].isin(ids_validos), "pedido_inexistente")
    quarentena(~ev["codigo_normalizado"].isin(codigos_validos), "codigo_nao_reconhecido")
    quarentena(ev["data_hora_dt"].isna(), "data_hora_ausente_ou_invalida")
    quarentena(ev["data_hora_dt"] > REFERENCIA, "evento_posterior_referencia")
    quarentena(ev["data_hora_dt"] < ev["data_coleta_dt"], "evento_anterior_coleta")
    quarentena(ev["data_coleta_dt"].isna(), "data_coleta_ausente_ou_invalida")
    quarentena(duplicado, "evento_duplicado")

    validos = ev.loc[ev["decisao"] == "UTILIZADO"].copy()
    auditoria = ev[[
        "id_evento", "id_pedido", "codigo_evento", "codigo_normalizado", "data_hora",
        "data_hora_dt", "fonte", "observacao", "decisao", "motivo",
    ]].copy()
    return validos, auditoria


def consolidar_pedidos(pedidos: pd.DataFrame, eventos_validos: pd.DataFrame):
    """Uma linha por pedido, com status temporal e entrega valida quando houver."""
    base = pedidos.copy()
    base["data_coleta_dt"] = converter_datas(base["data_coleta"])

    # Desempate: timestamp, ordem oficial e ID (sempre deterministico).
    ordenados = eventos_validos.sort_values(
        ["data_hora_dt", "prioridade_codigo", "id_evento_numerico", "id_evento"],
        kind="stable", na_position="last"
    )
    ultimos = ordenados.drop_duplicates(subset=["id_pedido"], keep="last")[[
        "id_pedido", "codigo_normalizado", "data_hora_dt", "fonte"
    ]].rename(columns={
        "codigo_normalizado": "status_ultimo_evento",
        "data_hora_dt": "data_hora_ultimo_evento",
        "fonte": "fonte_ultimo_evento",
    })

    # ENT eh um evento terminal; a PRIMEIRA entrega valida e a data efetiva de entrega.
    entregas = (
        eventos_validos.loc[eventos_validos["codigo_normalizado"] == "ENT"]
        .groupby("id_pedido", as_index=False)["data_hora_dt"].min()
        .rename(columns={"data_hora_dt": "data_entrega"})
    )
    contagem = eventos_validos.groupby("id_pedido").size().rename("quantidade_eventos_validos")

    resultado = base.merge(ultimos, on="id_pedido", how="left", validate="one_to_one")
    resultado = resultado.merge(entregas, on="id_pedido", how="left", validate="one_to_one")
    resultado = resultado.merge(contagem, on="id_pedido", how="left", validate="one_to_one")
    resultado["quantidade_eventos_validos"] = resultado["quantidade_eventos_validos"].fillna(0).astype(int)

    resultado["status_atual"] = resultado["status_ultimo_evento"].fillna("SEM_RASTREIO")
    resultado.loc[resultado["data_entrega"].notna(), "status_atual"] = "ENT"

    # Datas ISO padronizadas nas exportacoes (nunca alteram os arquivos de entrada).
    resultado["data_coleta"] = resultado["data_coleta_dt"].dt.strftime("%Y-%m-%d %H:%M:%S")
    resultado = resultado.drop(columns="data_coleta_dt")

    colunas = [
        "id_pedido", "cliente", "cidade_destino", "uf", "data_coleta",
        "prazo_dias_uteis", "transportadora", "valor_nf", "status_atual",
        "status_ultimo_evento", "data_hora_ultimo_evento", "fonte_ultimo_evento",
        "data_entrega", "quantidade_eventos_validos",
    ]
    return resultado[colunas].sort_values("id_pedido").reset_index(drop=True)


def executar(dados_dir: Path = DADOS, saidas_dir: Path = SAIDAS):
    saidas_dir = Path(saidas_dir)
    saidas_dir.mkdir(parents=True, exist_ok=True)
    pedidos, eventos, dicionario = carregar_dados(dados_dir)
    validos, auditoria = tratar_eventos(pedidos, eventos, dicionario)
    consolidado = consolidar_pedidos(pedidos, validos)

    # Preserva o diagnostico da etapa 1 e gera novas saidas.
    consolidado.to_csv(saidas_dir / "pedidos_consolidados.csv", sep=";", index=False, encoding="utf-8-sig")
    auditoria.to_csv(saidas_dir / "auditoria_eventos.csv", sep=";", index=False, encoding="utf-8-sig")
    validos[[
        "id_evento", "id_pedido", "codigo_evento", "codigo_normalizado",
        "data_hora_dt", "fonte", "observacao",
    ]].to_csv(saidas_dir / "eventos_validos.csv", sep=";", index=False, encoding="utf-8-sig")

    print(f"Pedidos consolidados: {len(consolidado)}")
    print(f"Eventos utilizados: {len(validos)} / {len(eventos)}")
    print(f"Eventos em quarentena: {(auditoria['decisao'] == 'QUARENTENA').sum()}")
    print("\nMotivos de quarentena:")
    print(auditoria.loc[auditoria["decisao"] == "QUARENTENA", "motivo"].value_counts().to_string())
    print("\nStatus atuais:")
    print(consolidado["status_atual"].value_counts().to_string())
    print("\nArquivos novos: output/pedidos_consolidados.csv, auditoria_eventos.csv e eventos_validos.csv")
    return consolidado, auditoria


if __name__ == "__main__":
    executar()
