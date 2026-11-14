"""Leitura e métricas da interface: não altera o pipeline nem acessa rede."""
from __future__ import annotations

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
FILES = {
    "pedidos": "pedidos_sla.csv",
    "transportadoras": "otd_transportadoras.csv",
    "situacoes": "contagem_situacoes.csv",
    "ocorrencias": "ocorrencias_classificadas.csv",
    "categorias": "frequencia_categorias.csv",
    "qualidade": "diagnostico_qualidade.csv",
    "auditoria": "auditoria_eventos.csv",
    "eventos": "eventos_validos.csv",
    "alertas": "alertas_operacionais.csv",
}

LABELS = {
    "ENTREGUE_NO_PRAZO": "Entregue no prazo",
    "ENTREGUE_COM_ATRASO": "Entregue com atraso",
    "ATRASADO_EM_ABERTO": "Atrasado em aberto",
    "EM_RISCO": "Em risco",
    "NO_PRAZO_EM_ABERTO": "No prazo em aberto",
}
COLORS = {
    "ENTREGUE_NO_PRAZO": "#a3e635",
    "ENTREGUE_COM_ATRASO": "#ff6b72",
    "ATRASADO_EM_ABERTO": "#ff9f54",
    "EM_RISCO": "#f9cd54",
    "NO_PRAZO_EM_ABERTO": "#8aa6a8",
}
ORDER = list(LABELS)


def load_data(output: Path = OUTPUT) -> dict[str, pd.DataFrame]:
    """Carrega apenas arquivos gerados; preserva IDs como texto."""
    result = {}
    for key, filename in FILES.items():
        result[key] = pd.read_csv(output / filename, sep=";", encoding="utf-8-sig", dtype={"id_pedido": "string", "id_evento": "string"})
    return result


def filter_orders(df: pd.DataFrame, transportadora: str = "Todas", situacoes: list[str] | None = None,
                  status: list[str] | None = None, search: str = "") -> pd.DataFrame:
    result = df.copy()
    if transportadora and transportadora != "Todas":
        result = result[result["transportadora"] == transportadora]
    if situacoes:
        result = result[result["situacao_sla"].isin(situacoes)]
    if status:
        result = result[result["status_atual"].isin(status)]
    if search.strip():
        columns = ["id_pedido", "cliente", "cidade_destino", "uf"]
        query = search.strip()
        mask = pd.Series(False, index=result.index)
        for col in columns:
            mask |= result[col].fillna("").astype("string").str.contains(query, case=False, regex=False)
        result = result.loc[mask]
    return result


def scoped_metrics(df: pd.DataFrame) -> dict[str, int | float]:
    counts = df["situacao_sla"].value_counts()
    timely = int(counts.get("ENTREGUE_NO_PRAZO", 0))
    late = int(counts.get("ENTREGUE_COM_ATRASO", 0))
    delivered = timely + late
    risk = int(counts.get("EM_RISCO", 0))
    overdue = int(counts.get("ATRASADO_EM_ABERTO", 0))
    return {
        "pedidos": len(df), "entregues": delivered, "pontuais": timely,
        "atrasados_entregues": late, "em_risco": risk, "atrasados_abertos": overdue,
        "alertas": risk + overdue, "otd": round(100 * timely / delivered, 2) if delivered else 0.,
    }


def carriers_kpis(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for carrier, group in df.groupby("transportadora"):
        m = scoped_metrics(group)
        rows.append({
            "transportadora": carrier,
            "total_pedidos": m["pedidos"],
            "total_entregues": m["entregues"],
            "entregues_no_prazo": m["pontuais"],
            "entregues_com_atraso": m["atrasados_entregues"],
            "otd_pct": m["otd"],
            "alertas": m["alertas"],
        })
    return pd.DataFrame(rows).sort_values("otd_pct", ascending=True) if rows else pd.DataFrame(
        columns=["transportadora", "total_pedidos", "total_entregues", "entregues_no_prazo", "entregues_com_atraso", "otd_pct", "alertas"]
    )


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(sep=";", index=False).encode("utf-8-sig")


def selected_carrier(event: dict | None, valid_carriers: list[str]) -> str | None:
    """Converte um evento de seleção Plotly em transportadora conhecida.

    Segurança: nomes vêm da base gerada, nunca de uma string arbitrária.
    """
    if not event:
        return None
    selection = event.get("selection", {})
    points = selection.get("points", []) if selection else []
    for point in reversed(points):
        candidate = point.get("y")
        if candidate in valid_carriers:
            return candidate
        custom = point.get("customdata", [])
        if isinstance(custom, (list, tuple)) and custom and custom[0] in valid_carriers:
            return custom[0]
    return None


def filter_quality_by_orders(
    diagnostic: pd.DataFrame, auditoria: pd.DataFrame,
    orders: pd.DataFrame, carrier: str = "Todas",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Auditoria por escopo: registros órfãos não recebem transportadora inventada."""
    if carrier == "Todas":
        return diagnostic.copy(), auditoria.copy()
    ids = set(orders["id_pedido"].dropna().astype(str))
    diag = diagnostic[diagnostic["id_pedido"].astype(str).isin(ids)].copy()
    audit = auditoria[auditoria["id_pedido"].astype(str).isin(ids)].copy()
    return diag, audit


def selected_order_id(event: dict | None, visible_orders: pd.DataFrame) -> str | None:
    """Devolve o ID do pedido quando se clica numa célula da tabela.

    ``single-cell`` não cria os checkboxes da seleção de linha. O Streamlit
    retorna ``cells=[(posição_original_da_linha, coluna)]``. Mantemos
    compatibilidade com eventos ``rows`` antigos dos testes anteriores.
    A posição é relativa ao DataFrame renderizado, não ao índice do Pandas.
    """
    if not event or visible_orders.empty:
        return None
    selection = event.get("selection") or {}
    cells = selection.get("cells") or []
    position = None
    if len(cells) == 1 and isinstance(cells[0], (list, tuple)) and len(cells[0]) == 2:
        position = cells[0][0]
    else:
        rows = selection.get("rows") or []
        if len(rows) == 1:
            position = rows[0]
    if isinstance(position, bool) or not isinstance(position, int):
        return None
    if position < 0 or position >= len(visible_orders):
        return None
    return str(visible_orders.iloc[position]["id_pedido"])


def keep_selected_order(selected_id: str | None, visible_orders: pd.DataFrame) -> str | None:
    """Preserva uma seleção somente enquanto ela existir no recorte consultado."""
    if not selected_id or visible_orders.empty:
        return None
    valid = set(visible_orders["id_pedido"].dropna().astype(str).tolist())
    return selected_id if selected_id in valid else None


def occurrence_counts(occurrences: pd.DataFrame) -> pd.DataFrame:
    """Conta todas as categorias de cada OCO (inclusive múltiplos rótulos)."""
    categories = (occurrences["categorias"].fillna("").astype(str)
                  .str.split("|").explode().str.strip())
    categories = categories[categories.ne("")]
    result = categories.value_counts().rename_axis("categoria").reset_index(name="quantidade")
    return result


def selected_occurrence_category(event: dict | None, valid_categories: list[str]) -> str | None:
    """Categoria selecionada no Plotly: somente valores presentes no gráfico."""
    if not event:
        return None
    points = (event.get("selection") or {}).get("points") or []
    for point in reversed(points):
        category = point.get("y")
        if category in valid_categories:
            return category
    return None


def filter_occurrences(occurrences: pd.DataFrame, category: str | None) -> pd.DataFrame:
    """Filtra por categoria EXATA, incluindo rótulos secundários.

    Não usar str.contains simples: por exemplo, 'RECUSA' não pode combinar
    com um texto maior por substring nem excluir AVARIA|RECUSA.
    """
    if not category or category == "Todas":
        return occurrences.copy()
    return occurrences[occurrences["categorias"].fillna("").astype(str).apply(
        lambda value: category in (tag.strip() for tag in value.split("|"))
    )].copy()


def selected_order_from_grid(response, visible_orders: pd.DataFrame) -> str | None:
    """Obtém o ID diretamente da linha selecionada no AG Grid.

    Não depende da posição da linha ou do scroll (evita o efeito de
    célula flutuante do seletor nativo). A saída varia entre versões da
    biblioteca (DataFrame, lista de dicionários ou None).
    """
    if response is None or visible_orders.empty:
        return None
    if isinstance(response, dict):
        rows = response.get("selected_rows")
    else:
        try:
            rows = response["selected_rows"]
        except (TypeError, KeyError, AttributeError):
            return None
    if rows is None:
        return None
    if isinstance(rows, pd.DataFrame):
        if rows.empty or "Pedido" not in rows.columns:
            return None
        selected = rows.iloc[0]["Pedido"]
    elif isinstance(rows, list):
        if not rows or not isinstance(rows[0], dict):
            return None
        selected = rows[0].get("Pedido")
    else:
        return None
    if pd.isna(selected):
        return None
    return keep_selected_order(str(selected), visible_orders)
