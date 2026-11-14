"""Etapa 4: classificar OCOs e gerar alertas operacionais simulados.

Uso: python -m src.ocorrencias

Todas as decisoes usam apenas eventos validados; nenhuma mensagem e enviada
para fora do computador. A referencia do desafio permanece fixa em 24/09/2026.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

from src.diagnostico import REFERENCIA
from src.rastreamento import carregar_dados, consolidar_pedidos, tratar_eventos
from src.sla import ATRASADO_EM_ABERTO, EM_RISCO, calcular_sla

SAIDAS = Path(__file__).resolve().parent.parent / "output"

# Palavras e expressoes audiveis e ajustaveis em vez de uma IA externa. A
# ordem define a categoria principal caso haja mais de uma classificacao.
REGRAS = {
    "AVARIA": (
        r"\bavari", r"\bamassad", r"\bdanificad", r"\bquebrad",
        r"\bmolhad", r"\bchuva\b", r"\brasgad", r"\bvazament",
    ),
    "RECUSA": (r"\brecus", r"\brejeitad"),
    "AUSENCIA": (r"\bausent", r"\bninguem\b", r"\bnao\s+atendeu"),
    "ENDERECO": (r"\benderec", r"\bnumero\s+inexistent", r"\bcep\b"),
    "ACESSO_IMPEDIDO": (
        r"\bportaria\b", r"\bacesso\s+(?:negad|impedid)",
        r"\bportao\s+fechad", r"\bcondominio\s+fechad",
    ),
}


def normalizar_texto(valor: object) -> str:
    """Remove acentos e normaliza espacos para classificar sem case/acentos."""
    if valor is None or pd.isna(valor):
        return ""
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto.casefold().strip())


def classificar_observacao(observacao: object) -> list[str]:
    texto = normalizar_texto(observacao)
    if not texto:
        return ["SEM_DESCRICAO"]
    categorias = [
        categoria for categoria, padroes in REGRAS.items()
        if any(re.search(padrao, texto) for padrao in padroes)
    ]
    return categorias or ["OUTROS"]


def classificar_ocorrencias(eventos_validos: pd.DataFrame) -> pd.DataFrame:
    """Classifica apenas OCOs aceitas pelo processo de qualidade."""
    selecionadas = eventos_validos.loc[
        eventos_validos["codigo_normalizado"] == "OCO",
        ["id_evento", "id_pedido", "data_hora_dt", "fonte", "observacao"],
    ].copy()
    categorias = selecionadas["observacao"].apply(classificar_observacao)
    selecionadas["categoria_principal"] = categorias.apply(lambda c: c[0])
    selecionadas["categorias"] = categorias.apply(lambda c: "|".join(c))
    selecionadas["metodo"] = "REGRAS_PALAVRAS_CHAVE"
    return selecionadas.sort_values(
        ["data_hora_dt", "id_evento"], kind="stable"
    ).reset_index(drop=True)


def frequencia_categorias(ocorrencias: pd.DataFrame) -> pd.DataFrame:
    """Uma OCO multirrotulo conta uma vez em cada categoria identificada."""
    if ocorrencias.empty:
        return pd.DataFrame(columns=["categoria", "quantidade"])
    valores = ocorrencias["categorias"].str.split("|").explode()
    tabela = valores.value_counts().rename_axis("categoria").reset_index(name="quantidade")
    return tabela.sort_values(["quantidade", "categoria"], ascending=[False, True]).reset_index(drop=True)


def sugerir_acao(status: str, categorias: str) -> str:
    """Sinaliza uma proxima acao, sem presumir que a entrega foi reagendada."""
    if status == "SEM_RASTREIO":
        return "Solicitar rastreamento e localizar pedido junto a transportadora/origem."
    rotulos = set(categorias.split("|")) if categorias else set()
    if "AVARIA" in rotulos:
        return "Acionar transportadora e qualidade para apurar avaria e orientar tratativa."
    if "RECUSA" in rotulos:
        return "Confirmar motivo da recusa com cliente e transportadora e definir tratativa."
    if "AUSENCIA" in rotulos:
        return "Contatar destinatario e transportadora para verificar nova tentativa."
    if "ENDERECO" in rotulos:
        return "Validar endereco com o cliente e alinhar nova tentativa de entrega."
    if "ACESSO_IMPEDIDO" in rotulos:
        return "Validar regras de acesso e horario de recebimento antes de nova tentativa."
    if status == "TRF":
        return "Solicitar a transportadora localizacao e nova previsao de entrega."
    return "Verificar rastreamento com o responsavel pela operacao e atualizar previsao."


def gerar_alertas(pedidos_sla: pd.DataFrame, ocorrencias: pd.DataFrame) -> pd.DataFrame:
    """Gera uma linha por pedido aberto atrasado ou com vencimento nas proximas 24h."""
    prioritarios = pedidos_sla.loc[
        pedidos_sla["situacao_sla"].isin([ATRASADO_EM_ABERTO, EM_RISCO])
    ].copy()

    if not ocorrencias.empty:
        ultimas = ocorrencias.sort_values(
            ["data_hora_dt", "id_evento"], kind="stable"
        ).drop_duplicates("id_pedido", keep="last")[[
            "id_pedido", "observacao", "categoria_principal", "categorias"
        ]].rename(columns={
            "observacao": "ultima_ocorrencia",
            "categoria_principal": "categoria_ocorrencia",
            "categorias": "categorias_ocorrencia",
        })
    else:
        ultimas = pd.DataFrame(columns=[
            "id_pedido", "ultima_ocorrencia", "categoria_ocorrencia", "categorias_ocorrencia"
        ])

    resultado = prioritarios.merge(ultimas, on="id_pedido", how="left", validate="one_to_one")
    for coluna in ["ultima_ocorrencia", "categoria_ocorrencia", "categorias_ocorrencia"]:
        resultado[coluna] = resultado[coluna].fillna("")
    resultado["prioridade"] = resultado["situacao_sla"].map({
        ATRASADO_EM_ABERTO: "ALTA", EM_RISCO: "ATENCAO",
    })
    resultado["ordem_prioridade"] = resultado["prioridade"].map({"ALTA": 0, "ATENCAO": 1})
    resultado["acao_sugerida"] = resultado.apply(
        lambda linha: sugerir_acao(
            str(linha["status_atual"]), str(linha["categorias_ocorrencia"])
        ), axis=1,
    )
    resultado = resultado.sort_values(
        ["ordem_prioridade", "data_limite_sla", "id_pedido"], kind="stable"
    )
    colunas = [
        "id_pedido", "cliente", "transportadora", "cidade_destino", "uf",
        "status_atual", "situacao_sla", "prioridade", "data_limite_sla",
        "horas_ate_vencimento", "data_hora_ultimo_evento", "ultima_ocorrencia",
        "categoria_ocorrencia", "categorias_ocorrencia", "acao_sugerida",
    ]
    return resultado[colunas].reset_index(drop=True)


def mensagem_alerta(alertas: pd.DataFrame, referencia: pd.Timestamp = REFERENCIA) -> str:
    """Simula a mensagem que poderia seguir por e-mail, Teams ou webhook."""
    atrasados = int((alertas["situacao_sla"] == ATRASADO_EM_ABERTO).sum())
    em_risco = int((alertas["situacao_sla"] == EM_RISCO).sum())
    linhas = [
        "[SIMULACAO] ALERTA OPERACIONAL — AGV Tracking Intelligence",
        f"Data de referencia do desafio: {pd.Timestamp(referencia):%d/%m/%Y %H:%M}",
        f"Pedidos que exigem acao: {len(alertas)} | Atrasados: {atrasados} | Em risco: {em_risco}",
        "",
    ]
    for linha in alertas.itertuples(index=False):
        prazo = pd.Timestamp(linha.data_limite_sla).strftime("%d/%m/%Y %H:%M")
        linhas.extend([
            f"[{linha.prioridade}] {linha.id_pedido} | {linha.transportadora} | {linha.situacao_sla}",
            f"  Status: {linha.status_atual} | Limite: {prazo}",
        ])
        if linha.ultima_ocorrencia:
            linhas.append(f"  Ocorrencia: {linha.ultima_ocorrencia} ({linha.categorias_ocorrencia})")
        linhas.extend([f"  Acao sugerida: {linha.acao_sugerida}", ""])
    linhas.extend([
        "Observacao: alerta gerado localmente; nenhum e-mail, mensagem ou API foi acionado.",
        "SLA e prioridades definidos por premissas do desafio, sujeitos a validacao operacional.",
    ])
    return "\n".join(linhas) + "\n"


def executar(dados_dir: Path = Path(__file__).resolve().parent.parent / "dados", saidas_dir: Path = SAIDAS):
    """Executa todas as dependencias em memoria, direto dos CSVs de origem."""
    SAIDAS.mkdir(exist_ok=True)
    pedidos, eventos, dicionario = carregar_dados(dados_dir)
    validos, _auditoria = tratar_eventos(pedidos, eventos, dicionario)
    consolidados = consolidar_pedidos(pedidos, validos)
    pedidos_sla = calcular_sla(consolidados)
    ocorrencias = classificar_ocorrencias(validos)
    frequencias = frequencia_categorias(ocorrencias)
    alertas = gerar_alertas(pedidos_sla, ocorrencias)

    for nome, tabela in [
        ("ocorrencias_classificadas.csv", ocorrencias),
        ("frequencia_categorias.csv", frequencias),
        ("alertas_operacionais.csv", alertas),
    ]:
        tabela.to_csv(saidas_dir / nome, sep=";", index=False, encoding="utf-8-sig")
    texto_alerta = mensagem_alerta(alertas)
    (saidas_dir / "alerta_operacional.txt").write_text(texto_alerta, encoding="utf-8")

    resumo = [
        "# Etapa 4 — Ocorrencias e alertas (AGV TechLab)",
        "",
        f"- Data de referencia: {REFERENCIA:%d/%m/%Y %H:%M}",
        f"- Eventos OCO validos classificados: {len(ocorrencias)}",
        "- Classificador: palavras-chave deterministicas, sem APIs ou LLM; multirrotulo possivel.",
        "- Uma observacao pode entrar em mais de uma categoria; totais por categoria podem superar o numero de OCOs.",
        "- OCOs em pedidos ja entregues entram no historico, mas nao geram alertas de SLA.",
        f"- Pedidos que exigem acao: {len(alertas)}",
        f"- Atrasados em aberto: {(alertas['situacao_sla'] == ATRASADO_EM_ABERTO).sum()}",
        f"- Em risco: {(alertas['situacao_sla'] == EM_RISCO).sum()}",
        "",
        "## Frequencia de categorias",
        "",
    ]
    resumo.extend(f"- {r.categoria}: {r.quantidade}" for r in frequencias.itertuples(index=False))
    resumo.extend([
        "", "## Limites e decisoes pendentes", "",
        "- As regras usam palavras-chave; sinonimos nao previstos podem ser classificados como OUTROS.",
        "- Acoes sugeridas sao orientacoes, nao confirmacao de contato ou reentrega.",
        "- Os oito alertas cobrem somente pedidos abertos atrasados ou em risco nas 24h da referencia.",
        "- Uma ocorrencia historica nao prova que ainda esta pendente; sua presenca deve ser validada.",
        "- Confirmar com a operacao criterios de prioridade e prazos de SLA.",
    ])
    (saidas_dir / "resumo_ocorrencias_alertas.md").write_text("\n".join(map(str, resumo)) + "\n", encoding="utf-8")

    print(f"Eventos OCO classificados: {len(ocorrencias)}")
    print("Categorias (multirrotulo):")
    print(frequencias.to_string(index=False))
    print(f"\nPedidos com alerta: {len(alertas)} | Atrasados: {(alertas['situacao_sla'] == ATRASADO_EM_ABERTO).sum()} | Em risco: {(alertas['situacao_sla'] == EM_RISCO).sum()}")
    print("Saidas: ocorrencias_classificadas.csv, frequencia_categorias.csv, alertas_operacionais.csv, alerta_operacional.txt e resumo_ocorrencias_alertas.md")
    return ocorrencias, alertas


if __name__ == "__main__":
    executar()
