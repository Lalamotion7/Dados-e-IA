"""Utilitários de apresentação sem dependências do Streamlit.

Mantém a construção do histórico HTML testável e protege a interface
contra texto livre que contenha caracteres de marcação.
"""
from __future__ import annotations

from html import escape
from math import isfinite
import pandas as pd


EVENT_COLS = (
    ("data_hora_dt", "Data/hora"),
    ("codigo_normalizado", "Evento"),
    ("fonte", "Fonte"),
    ("observacao", "Observação"),
)


def visible_text(value: object) -> str:
    """Representação consistente de valores vazios, sem perder texto longo."""
    if value is None:
        return "—"
    try:
        if bool(pd.isna(value)):
            return "—"
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text if text and text.lower() not in {"none", "nan", "nat"} else "—"


def history_table_html(events: pd.DataFrame) -> str:
    """Tabela semântica com texto integral e layout adaptável por CSS.

    Recebe as datas já formatadas pelo app. Nenhum valor de origem é
    interpolado como HTML executável.
    """
    required = {col for col, _ in EVENT_COLS}
    missing = required - set(events.columns)
    if missing:
        raise ValueError("Colunas de eventos ausentes: " + ", ".join(sorted(missing)))
    head = "".join(f"<th scope='col'>{escape(label)}</th>" for _, label in EVENT_COLS)
    rows = []
    for record in events.to_dict(orient="records"):
        cells = []
        for field, label in EVENT_COLS:
            text = escape(visible_text(record[field]), quote=True)
            css = " class='history-observation'" if field == "observacao" else ""
            cells.append(f"<td data-label='{escape(label, quote=True)}'{css}>{text}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return ("<div class='history-scroll' role='region' aria-label='Histórico de eventos' tabindex='0'>"
            "<table class='history-table'><thead><tr>" + head + "</tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def bar_fill_percent(value: float, maximum: float) -> float:
    """Escala visual limitada a 0–100%; não altera o dado original."""
    try:
        val, bound = float(value), float(maximum)
        if not (isfinite(val) and isfinite(bound)) or bound <= 0:
            return 0.0
        return max(0.0, min(100.0, 100.0 * val / bound))
    except (ValueError, TypeError):
        return 0.0


def toggle_choice(current: str, clicked: str, default: str = "Todas") -> str:
    """Clicar na mesma categoria/transportadora limpa o filtro."""
    return default if current == clicked else clicked


def readonly_table_html(df: pd.DataFrame, label: str, max_height: int = 430) -> str:
    """Tabela responsiva de consulta para telas que não precisam de seleção.

    Evita o componente de seleção/edição de células do st.dataframe,
    principal suspeito do balão flutuante mostrado nos vídeos.
    Preserva a ordenação original do dataframe recebido e escapa HTML do CSV.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("A tabela precisa ser um DataFrame")
    height = max(120, min(int(max_height), 720))
    label_escaped = escape(str(label), quote=True)
    headers = "".join(
        "<th scope='col'>" + escape(str(column), quote=True) + "</th>"
        for column in df.columns
    )
    rows = []
    for record in df.itertuples(index=False, name=None):
        cells = []
        for value in record:
            display = visible_text(value)
            cells.append("<td>" + escape(display, quote=True) + "</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    if not rows:
        colspan = max(1, len(df.columns))
        rows.append(f"<tr><td colspan='{colspan}' class='readonly-table-empty'>Nenhum registro neste filtro.</td></tr>")
    return (
        f"<div class='readonly-table-scroll' role='region' aria-label='{label_escaped}' "
        f"tabindex='0' style='--readonly-max-height:{height}px'>"
        f"<table class='readonly-table'><thead><tr>{headers}</tr></thead><tbody>"
        + "".join(rows) + "</tbody></table></div>"
    )
