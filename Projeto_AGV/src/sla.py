"""Etapa 3 — cálculo de prazo, SLA e OTD para os pedidos da AGV.

Execute na raiz: python -m src.sla

Premissas do desafio (precisam ser validadas pelo negócio):
- Data de referência: 24/09/2026 18:00 (não usa o relógio do sistema).
- Dias úteis: segunda a sexta, sem feriados; o dia da coleta não é contado.
- Prazo final: mesmo horário da coleta no último dia útil.
- Entregue no prazo: data_entrega <= vencimento.
- Pedido em aberto: atraso quando agora > vencimento; em risco se vence em até 24h.
- OTD: entregas pontuais / todas as entregas válidas (pedidos abertos excluídos).
"""
from pathlib import Path
import pandas as pd
from pandas.tseries.offsets import BDay

from src.diagnostico import REFERENCIA, converter_datas
from src.rastreamento import carregar_dados, tratar_eventos, consolidar_pedidos

RAIZ = Path(__file__).resolve().parent.parent
SAIDAS = RAIZ / "output"

ENTREGUE_NO_PRAZO = "ENTREGUE_NO_PRAZO"
ENTREGUE_COM_ATRASO = "ENTREGUE_COM_ATRASO"
ATRASADO_EM_ABERTO = "ATRASADO_EM_ABERTO"
EM_RISCO = "EM_RISCO"
NO_PRAZO_EM_ABERTO = "NO_PRAZO_EM_ABERTO"

SITUACOES = [ENTREGUE_NO_PRAZO, ENTREGUE_COM_ATRASO,
             ATRASADO_EM_ABERTO, EM_RISCO, NO_PRAZO_EM_ABERTO]


def calcular_vencimento(data_coleta: pd.Timestamp, dias_uteis: int) -> pd.Timestamp:
    """Soma N dias úteis após a coleta, preservando o horário de origem."""
    if pd.isna(data_coleta) or pd.isna(dias_uteis):
        return pd.NaT
    dias_uteis = int(dias_uteis)
    if dias_uteis < 0:
        raise ValueError("Prazo em dias úteis não pode ser negativo")
    return pd.Timestamp(data_coleta) + BDay(dias_uteis)


def calcular_sla(consolidado: pd.DataFrame, referencia: pd.Timestamp = REFERENCIA) -> pd.DataFrame:
    """Acrescenta o vencimento, SLA, atraso e horas restantes sem alterar os dados recebidos."""
    resultado = consolidado.copy()
    referencia = pd.Timestamp(referencia)
    resultado["data_coleta_dt"] = converter_datas(resultado["data_coleta"])
    resultado["data_entrega_dt"] = pd.to_datetime(resultado["data_entrega"], errors="coerce")
    resultado["prazo_dias_uteis_num"] = pd.to_numeric(resultado["prazo_dias_uteis"], errors="coerce")
    if resultado["data_coleta_dt"].isna().any():
        raise ValueError("Há pedidos com data de coleta inválida; revisar antes de calcular SLA")
    if resultado["prazo_dias_uteis_num"].isna().any():
        raise ValueError("Há pedidos com prazo inválido; revisar antes de calcular SLA")
    if (resultado["prazo_dias_uteis_num"] < 0).any():
        raise ValueError("Há pedidos com prazo negativo")
    if (resultado["prazo_dias_uteis_num"] % 1 != 0).any():
        raise ValueError("Há prazo fracionário; o desafio espera dias úteis inteiros")

    resultado["data_limite_sla"] = [
        calcular_vencimento(dt, int(dias))
        for dt, dias in zip(resultado["data_coleta_dt"], resultado["prazo_dias_uteis_num"])
    ]
    entregue = resultado["data_entrega_dt"].notna()
    pontual = entregue & (resultado["data_entrega_dt"] <= resultado["data_limite_sla"])
    atrasado_entregue = entregue & ~pontual
    aberto = ~entregue
    # Compara horas numericas em vez de comparar uma Serie de timestamps com
    # um Timedelta. Isso evita avisos de compatibilidade em algumas versoes
    # de NumPy/Pandas e deixa a fronteira de 24 horas explicita.
    horas_restantes = (
        (resultado["data_limite_sla"] - referencia).dt.total_seconds() / 3600
    )
    atrasado_aberto = aberto & (horas_restantes < 0)
    em_risco = aberto & horas_restantes.between(0, 24, inclusive="both")

    resultado["situacao_sla"] = NO_PRAZO_EM_ABERTO
    resultado.loc[em_risco, "situacao_sla"] = EM_RISCO
    resultado.loc[atrasado_aberto, "situacao_sla"] = ATRASADO_EM_ABERTO
    resultado.loc[atrasado_entregue, "situacao_sla"] = ENTREGUE_COM_ATRASO
    resultado.loc[pontual, "situacao_sla"] = ENTREGUE_NO_PRAZO

    resultado["entregue"] = entregue
    resultado["entregue_no_prazo"] = pontual
    # Horas calculadas apenas para entregas em aberto: positivo = ainda resta prazo.
    resultado["horas_ate_vencimento"] = horas_restantes.where(aberto).round(2)

    resultado = resultado.drop(columns=["data_coleta_dt", "data_entrega_dt", "prazo_dias_uteis_num"])
    return resultado


def produzir_indicadores(pedidos_sla: pd.DataFrame):
    """Retorna indicadores gerais, OTD por transportadora e contagem por situação."""
    entregues = pedidos_sla.loc[pedidos_sla["entregue"]].copy()
    total_entregues = len(entregues)
    no_prazo = int(entregues["entregue_no_prazo"].sum())
    geral = pd.DataFrame([{
        "total_pedidos": len(pedidos_sla),
        "total_entregues": total_entregues,
        "entregues_no_prazo": no_prazo,
        "entregues_com_atraso": total_entregues - no_prazo,
        "otd_pct": round(no_prazo / total_entregues * 100, 2) if total_entregues else None,
        "pedidos_abertos": int((~pedidos_sla["entregue"]).sum()),
        "pedidos_atrasados_em_aberto": int((pedidos_sla["situacao_sla"] == ATRASADO_EM_ABERTO).sum()),
        "pedidos_em_risco": int((pedidos_sla["situacao_sla"] == EM_RISCO).sum()),
    }])

    # Usar todos os nomes de transportadoras para preservar mesmo as que não tenham entregas.
    grupo = entregues.groupby("transportadora").agg(
        total_entregues=("id_pedido", "count"),
        entregues_no_prazo=("entregue_no_prazo", "sum"),
    ).reset_index()
    transportadoras = pd.DataFrame({
        "transportadora": sorted(pedidos_sla["transportadora"].dropna().unique())
    }).merge(grupo, how="left", on="transportadora")
    transportadoras[["total_entregues", "entregues_no_prazo"]] = (
        transportadoras[["total_entregues", "entregues_no_prazo"]].fillna(0).astype(int)
    )
    transportadoras["entregues_com_atraso"] = (
        transportadoras["total_entregues"] - transportadoras["entregues_no_prazo"]
    )
    transportadoras["otd_pct"] = (
        100 * transportadoras["entregues_no_prazo"] /
        transportadoras["total_entregues"].replace({0: float("nan")})
    ).round(2)

    contagem = (
        pedidos_sla["situacao_sla"].value_counts().reindex(SITUACOES, fill_value=0)
        .rename_axis("situacao_sla").reset_index(name="quantidade")
    )
    return geral, transportadoras, contagem


def executar(dados_dir: Path = Path(__file__).resolve().parent.parent / "dados", saidas_dir: Path = SAIDAS):
    """Reprocessa os CSVs originais: nunca depende de output antigo."""
    saidas_dir = Path(saidas_dir)
    saidas_dir.mkdir(parents=True, exist_ok=True)
    pedidos, eventos, dicionario = carregar_dados(dados_dir)
    validos, _auditoria = tratar_eventos(pedidos, eventos, dicionario)
    consolidado = consolidar_pedidos(pedidos, validos)
    pedidos_sla = calcular_sla(consolidado)
    geral, transportadoras, contagem = produzir_indicadores(pedidos_sla)

    pedidos_sla.to_csv(saidas_dir / "pedidos_sla.csv", sep=";", index=False, encoding="utf-8-sig")
    geral.to_csv(saidas_dir / "indicadores_gerais.csv", sep=";", index=False, encoding="utf-8-sig")
    transportadoras.to_csv(saidas_dir / "otd_transportadoras.csv", sep=";", index=False, encoding="utf-8-sig")
    contagem.to_csv(saidas_dir / "contagem_situacoes.csv", sep=";", index=False, encoding="utf-8-sig")

    relatorio = [
        "# SLA e OTD — AGV TechLab",
        "",
        f"- Referência: {REFERENCIA:%d/%m/%Y %H:%M}",
        "- Dias úteis: segunda a sexta, sem feriados; mantém horário da coleta.",
        "- Dia da coleta não é contado para o prazo em dias úteis.",
        "- OTD: entregues no prazo / total de entregas válidas; pedidos abertos ficam fora.",
        "- Vencimentos no intervalo [agora, agora + 24h] são considerados em risco.",
        "",
        "## Indicadores gerais",
        f"- Pedidos: {int(geral.iloc[0]['total_pedidos'])}",
        f"- Entregues: {int(geral.iloc[0]['total_entregues'])}",
        f"- Entregues no prazo: {int(geral.iloc[0]['entregues_no_prazo'])}",
        f"- OTD: {geral.iloc[0]['otd_pct']:.2f}%",
        "",
        "## Situações de prazo",
    ]
    relatorio.extend(f"- {r.situacao_sla}: {r.quantidade}" for r in contagem.itertuples())
    relatorio.extend(["", "## Questões para validar com o negócio", "",
       "- Quais feriados nacionais/estaduais/municipais e quais calendários por rota?",
       "- O prazo é contado com a mesma hora da coleta ou até o fim do dia?",
       "- OTD deve considerar todas as entregas ou todos os pedidos previstos no período?",
       "- Devoluções, reentregas e alterações de prazo mudam a data efetiva da entrega?",
       ""])
    (saidas_dir / "resumo_sla.md").write_text("\n".join(relatorio), encoding="utf-8")

    print(f"Pedidos: {len(pedidos_sla)} | Entregues: {int(geral.iloc[0]['total_entregues'])}")
    print(f"OTD geral: {geral.iloc[0]['otd_pct']:.2f}% ({int(geral.iloc[0]['entregues_no_prazo'])}/{int(geral.iloc[0]['total_entregues'])})")
    print("\nSituacoes:")
    print(contagem.to_string(index=False))
    print("\nOTD por transportadora:")
    print(transportadoras.to_string(index=False))
    print("\nGerados: pedidos_sla.csv, indicadores_gerais.csv, otd_transportadoras.csv, contagem_situacoes.csv e resumo_sla.md")
    return pedidos_sla, geral, transportadoras, contagem


if __name__ == "__main__":
    executar()
