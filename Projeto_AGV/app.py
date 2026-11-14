"""Dashboard web do desafio AGV TechLab.

Execute da raiz: streamlit run app.py
Usa exclusivamente saídas do pipeline Python; sem APIs externas e sem rotas reais.
"""
from __future__ import annotations

import base64
import hashlib
import re
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_option_menu import option_menu
from st_aggrid import AgGrid
from PIL import Image

from src.dashboard_data import (
    COLORS, LABELS, ORDER, OUTPUT, carriers_kpis, csv_bytes,
    filter_orders, load_data, scoped_metrics, filter_quality_by_orders,
    keep_selected_order, selected_order_from_grid, occurrence_counts, filter_occurrences,
)
from src.dashboard_charts import show_carrier_mix_legend
from src.diagnostico import REFERENCIA
from src.ui_helpers import history_table_html, bar_fill_percent, toggle_choice, readonly_table_html

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
INTERFACE_BUILD = "14d"  # Confirmar no rodapé qual versão está realmente em execução

PAGE_OPTIONS = ["Visão geral", "Rastreamento", "Transportadoras", "Ocorrências", "Qualidade", "Alertas"]
PAGE_ICONS = ["house", "truck", "bar-chart", "exclamation-octagon", "shield-check", "bell"]

ICON_SVGS = {
    "orders": """<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><path d='M12 3L4 7l8 4 8-4-8-4Z' stroke='currentColor' stroke-width='1.8' stroke-linejoin='round'/><path d='M4 12l8 4 8-4' stroke='currentColor' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/><path d='M4 17l8 4 8-4' stroke='currentColor' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/></svg>""",
    "target": """<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><circle cx='12' cy='12' r='7.8' stroke='currentColor' stroke-width='1.8'/><circle cx='12' cy='12' r='3.2' stroke='currentColor' stroke-width='1.8'/><path d='M12 2.6v3M21.4 12h-3M12 21.4v-3M2.6 12h3' stroke='currentColor' stroke-width='1.8' stroke-linecap='round'/></svg>""",
    "truck": """<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><path d='M3 6.5h10.5v8.2H3z' stroke='currentColor' stroke-width='1.8' stroke-linejoin='round'/><path d='M13.5 9.5h3.4l2.1 2.3v2.9h-5.5V9.5Z' stroke='currentColor' stroke-width='1.8' stroke-linejoin='round'/><circle cx='7.2' cy='17.2' r='1.8' stroke='currentColor' stroke-width='1.8'/><circle cx='17.2' cy='17.2' r='1.8' stroke='currentColor' stroke-width='1.8'/></svg>""",
    "alert": """<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><path d='M12 4.2 20.2 18H3.8L12 4.2Z' stroke='currentColor' stroke-width='1.8' stroke-linejoin='round'/><path d='M12 9v4.4' stroke='currentColor' stroke-width='1.8' stroke-linecap='round'/><circle cx='12' cy='16.3' r='1' fill='currentColor'/></svg>""",
    "grid": """<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><rect x='4' y='4' width='6' height='6' rx='1' stroke='currentColor' stroke-width='1.8'/><rect x='14' y='4' width='6' height='6' rx='1' stroke='currentColor' stroke-width='1.8'/><rect x='4' y='14' width='6' height='6' rx='1' stroke='currentColor' stroke-width='1.8'/><rect x='14' y='14' width='6' height='6' rx='1' stroke='currentColor' stroke-width='1.8'/></svg>""",
    "tag": """<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><path d='M10 4h6.2L20 7.8V14l-6 6-10-10L10 4Z' stroke='currentColor' stroke-width='1.8' stroke-linejoin='round'/><circle cx='14.8' cy='8.8' r='1.1' fill='currentColor'/></svg>""",
    "spark": """<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><path d='M8 15.8V13M12 15.8V8M16 15.8V10.7' stroke='currentColor' stroke-width='1.8' stroke-linecap='round'/><path d='M5 19.5h14' stroke='currentColor' stroke-width='1.8' stroke-linecap='round'/></svg>""",
    "check": """<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><circle cx='12' cy='12' r='8' stroke='currentColor' stroke-width='1.8'/><path d='m8.6 12.2 2.2 2.3 4.8-5' stroke='currentColor' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/></svg>""",
    "database": """<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><ellipse cx='12' cy='6.5' rx='6.8' ry='2.8' stroke='currentColor' stroke-width='1.8'/><path d='M5.2 6.5v5c0 1.6 3 2.8 6.8 2.8s6.8-1.2 6.8-2.8v-5' stroke='currentColor' stroke-width='1.8'/><path d='M5.2 11.5v5c0 1.6 3 2.8 6.8 2.8s6.8-1.2 6.8-2.8v-5' stroke='currentColor' stroke-width='1.8'/></svg>""",
    "clock": """<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><circle cx='12' cy='12' r='8' stroke='currentColor' stroke-width='1.8'/><path d='M12 7.6v4.8l3.2 1.9' stroke='currentColor' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/></svg>""",
    "warning": """<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><path d='M12 4.2 20.2 18H3.8L12 4.2Z' stroke='currentColor' stroke-width='1.8' stroke-linejoin='round'/><path d='M12 9v4.4' stroke='currentColor' stroke-width='1.8' stroke-linecap='round'/><circle cx='12' cy='16.3' r='1' fill='currentColor'/></svg>""",
    "carriers": """<svg viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><path d='M6 17.5V11' stroke='currentColor' stroke-width='1.8' stroke-linecap='round'/><path d='M12 17.5V7' stroke='currentColor' stroke-width='1.8' stroke-linecap='round'/><path d='M18 17.5v-4.8' stroke='currentColor' stroke-width='1.8' stroke-linecap='round'/></svg>""",
}

st.set_page_config(
    page_title="AGV | Tracking Intelligence", page_icon=Image.open(ASSETS / "somosagvbrasil_logo.jpg"),
    layout="wide", initial_sidebar_state="auto",
)


def inject_style():
    css = (ASSETS / "theme.css").read_text(encoding="utf-8")
    map_svg = ASSETS / "mapa_brasil_ilustrativo.svg"
    extra = ""
    if map_svg.exists():
        encoded = base64.b64encode(map_svg.read_bytes()).decode()
        extra = """
        [data-testid="stAppViewContainer"]::after {
          content:""; position:fixed; z-index:0; pointer-events:none;
          top:8%; right:-4%; width:min(48vw,760px); height:min(70vh,760px);
          opacity:.085;
          background:url('data:image/svg+xml;base64,MAPDATA') no-repeat center center / contain;
          filter:drop-shadow(0 0 24px rgba(86,223,180,.12));
          mask-image:radial-gradient(circle at 58% 52%, black 0%, black 55%, transparent 90%);
          -webkit-mask-image:radial-gradient(circle at 58% 52%, black 0%, black 55%, transparent 90%);
        }
        @media (max-width:1100px) {
          [data-testid="stAppViewContainer"]::after {
            width:min(64vw,640px); right:-16%; top:12%; opacity:.07;
          }
        }
        @media (max-width:640px) {
          [data-testid="stAppViewContainer"]::after {
            width:82vw; right:-26%; top:16%; opacity:.06;
          }
        }
        """.replace("MAPDATA", encoded)
    st.markdown("<style>" + css + "\n" + extra + "</style>", unsafe_allow_html=True)

def fmt_int(v):
    return f"{int(v):,}".replace(",", ".")


def fmt_pct(v):
    return f"{float(v):.2f}".replace(".", ",") + "%"


def fmt_date(v):
    if pd.isna(v) or str(v).strip() == "":
        return "—"
    stamp = pd.to_datetime(v, errors="coerce")
    return stamp.strftime("%d/%m/%Y %H:%M") if pd.notna(stamp) else "—"


def safe(v):
    return escape(str(v))


def title(text, description, animated=False):
    """Título sem redundância; o brilho animado é experimental e só aparece na home."""
    modifier = " page-title--shimmer" if animated else ""
    st.markdown(f"""<div class='page-title{modifier}'>{safe(text)}</div>
       <div class='page-subtitle'>{safe(description)}</div>""", unsafe_allow_html=True)


def section(text, symbol="▣"):
    st.markdown(f"<div class='section-head'><span class='symbol'>{symbol}</span>{safe(text)}</div>", unsafe_allow_html=True)


def render_icon(name: str) -> str:
    return ICON_SVGS.get(name, ICON_SVGS["grid"])


def render_logo() -> str:
    """Retorna o SVG oficial inline, sem depender de URL externa."""
    logo = ASSETS / "logo.svg"
    if not logo.exists():
        return "<div class='brand-fallback'>AGV</div>"
    encoded = base64.b64encode(logo.read_bytes()).decode()
    return f"<img class='brand-logo' src='data:image/svg+xml;base64,{encoded}' alt='Logo AGV' />"


def kpi(label, value, icon, note, warning=False):
    css = " warn" if warning else ""
    st.markdown(f"""<div class='kpi{css}'>
      <div class='kpi-top'><span class='kpi-icon'>{render_icon(icon)}</span>{safe(label)}</div>
      <div class='kpi-value'>{safe(value)}</div>
      <div class='kpi-note'>{safe(note)}</div></div>""", unsafe_allow_html=True)


def readonly_table(df: pd.DataFrame, label: str, max_height: int = 430) -> None:
    """Tabela de consulta sem seleção de célula/overlay flutuante.

    Ao contrário de st.dataframe, HTML semântico não abre o editor/copiador
    da célula durante duplo clique e não desloca popups ao rolar a página.
    """
    st.markdown(readonly_table_html(df, label=label, max_height=max_height), unsafe_allow_html=True)


def note(content):
    st.markdown(f"<div class='note'>{safe(content)}</div>", unsafe_allow_html=True)


def chart_layout(fig: go.Figure, height=285, margin=None):
    fig.update_layout(
        height=height, margin=margin or dict(t=25, b=35, l=18, r=30),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI, Arial, sans-serif", size=12, color="#d4eee2"),
        showlegend=False,
    )
    fig.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(color="#a3cbbd"))
    fig.update_yaxes(showgrid=False, zeroline=False, tickfont=dict(color="#cde5dc"))
    return fig




def choose_carrier(carrier_name: str) -> None:
    """Callback de widget NATIVO, executado antes de recriar o selectbox lateral.

    Diferente do on_select do Plotly, a seleção usa o clique em um botão
    Streamlit real, inclusive após rolar a página em telas menores.
    """
    st.session_state["carrier"] = toggle_choice(
        st.session_state.get("carrier", "Todas"), carrier_name
    )


def clear_carrier() -> None:
    st.session_state["carrier"] = "Todas"


def clickable_bar(key: str, label: str, value: float, maximum: float,
                  selected: bool, callback, suffix: str = "", emphasized: bool = True) -> None:
    """Barra de progresso CLICÁVEL com botão nativo e acessível.

    O fundo do botão representa o valor na escala. Não dependemos de um
    canvas/overlay Plotly para receber os cliques, o que evita o problema de
    seleção de pontos observado após rolagem no navegador.
    """
    fill = bar_fill_percent(value, maximum)
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", key).strip("_") or "filtro"
    bar_key = f"{slug}_{hashlib.sha256(key.encode('utf-8')).hexdigest()[:6]}"
    # A classe st-key-<key> é atribuída ao contêiner do widget pelo Streamlit.
    # Se o tema do framework mudar, o botão continua acessível e clicável.
    st.markdown(
        f"<div class='click-bar-label'><span>{safe(label)}</span>"
        f"<strong>{safe(suffix)}</strong></div>", unsafe_allow_html=True
    )
    fill_color = "#b5eb45" if emphasized else "#3a7665"
    st.markdown(f"""<style>
      .st-key-{bar_key} button {{
        background:linear-gradient(90deg,{fill_color} 0%,{fill_color} {fill:.3f}%,
                   #164441 {fill:.3f}%,#164441 100%) !important;
        border-color:{'rgba(181,235,69,.78)' if selected else 'rgba(100,193,160,.16)'} !important;
      }}
      .st-key-{bar_key} button:hover {{filter:brightness(1.12);border-color:#b5eb45 !important;}}
    </style>""", unsafe_allow_html=True)
    st.button(
        f"Selecionar {label}", key=bar_key, use_container_width=True,
        on_click=callback, help=f"Clique para {'limpar' if selected else 'filtrar por'} {label}",
        type="secondary",
    )


def chart_carriers(df_all, key="otd_geral"):
    """Comparativo interativo baseado em controles nativos do Streamlit.

    Mostra sempre as três transportadoras para permitir alternar o filtro.
    """
    carriers = carriers_kpis(df_all)
    if carriers.empty:
        st.info("Não há transportadoras para comparar.")
        return
    active = st.session_state.get("carrier", "Todas")
    with st.container(key=f"native_chart_{key}"):
        st.markdown("<div class='native-chart-eyebrow'>Clique em uma barra para aplicar o filtro</div>",
                    unsafe_allow_html=True)
        for row in carriers.itertuples(index=False):
            name = str(row.transportadora)
            selected = active == name
            clickable_bar(
                key=f"bar_{key}_{name}", label=name, value=float(row.otd_pct), maximum=100.0,
                selected=selected, emphasized=(active == "Todas" or selected),
                callback=lambda val=name: choose_carrier(val), suffix=fmt_pct(row.otd_pct),
            )
        st.markdown("<div class='native-chart-axis'><span>0%</span><span>25%</span>"
                    "<span>50%</span><span>75%</span><span>100%</span></div>",
                    unsafe_allow_html=True)
    st.caption("Clique em outra barra para trocar a transportadora; clique na barra selecionada para limpar.")

def chart_carrier_mix(df):
    carriers = carriers_kpis(df).copy()
    if carriers.empty:
        st.info("Não há transportadoras para comparar.")
        return
    carriers = carriers.sort_values(["entregues_no_prazo", "otd_pct"], ascending=[True, True])
    fig = go.Figure()
    fig.add_bar(
        y=carriers["transportadora"], x=carriers["entregues_no_prazo"], orientation="h",
        name="No prazo", marker=dict(color="#a3e635"),
        text=carriers["entregues_no_prazo"], texttemplate="%{text}", textposition="inside",
        insidetextanchor="middle", textfont=dict(color="#062627", size=14),
        customdata=carriers[["total_entregues", "otd_pct"]].values,
        hovertemplate="%{y}<br>No prazo: %{x}<br>Total entregues: %{customdata[0]}<br>OTD: %{customdata[1]:.2f}%<extra></extra>",
    )
    fig.add_bar(
        y=carriers["transportadora"], x=carriers["entregues_com_atraso"], orientation="h",
        name="Com atraso", marker=dict(color="#ff9f54"),
        text=carriers["entregues_com_atraso"], texttemplate="%{text}", textposition="inside",
        insidetextanchor="middle", textfont=dict(color="#fffaf0", size=14),
        customdata=carriers[["total_entregues", "otd_pct"]].values,
        hovertemplate="%{y}<br>Com atraso: %{x}<br>Total entregues: %{customdata[0]}<br>OTD: %{customdata[1]:.2f}%<extra></extra>",
    )
    fig.update_layout(barmode="stack", uniformtext_minsize=12, uniformtext_mode="hide")
    chart_layout(fig, height=345, margin=dict(t=30, b=78, l=18, r=18))
    # Uma única legenda, renderizada no rodapé DENTRO do Plotly (sem borda ou bloco externo).
    show_carrier_mix_legend(fig)
    fig.update_xaxes(title_text="", showgrid=False, showticklabels=False, zeroline=False)
    fig.update_yaxes(title_text="")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def chart_situations(df):
    counts = df["situacao_sla"].value_counts()
    active = [(key, int(counts.get(key, 0))) for key in ORDER if counts.get(key, 0) > 0]
    if not active:
        st.info("Sem pedidos para exibir.")
        return
    fig = go.Figure(go.Pie(
        labels=[LABELS[key] for key, _ in active],
        values=[val for _, val in active],
        hole=.68, sort=False, textinfo="none",
        marker=dict(colors=[COLORS[key] for key, _ in active], line=dict(width=2, color="#092c2d")),
        hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
    ))
    chart_layout(fig, height=312, margin=dict(t=16, b=20, l=0, r=0))
    fig.add_annotation(text=f"<b>{len(df)}</b><br><span style='font-size:12px'>pedidos</span>",
                       x=.5, y=.5, font=dict(size=26, color="#e9f9ed"), showarrow=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    chips = "".join(
        f"<div style='display:flex;align-items:center;gap:8px;margin:4px 0;font-size:.73rem;color:#c5e0d4'>"
        f"<span style='background:{COLORS[key]};height:9px;width:9px;border-radius:3px;display:inline-block'></span>"
        f"<span style='flex:1'>{safe(LABELS[key])}</span><strong>{value}</strong></div>"
        for key, value in active
    )
    st.markdown(f"<div class='glass-panel mini'>{chips}</div>", unsafe_allow_html=True)


def map_panel():
    svg = (ASSETS / "mapa_brasil_ilustrativo.svg").read_bytes()
    encoded = base64.b64encode(svg).decode()
    st.markdown(f"""<div class='map-card'>
      <img class='map-graphic' src='data:image/svg+xml;base64,{encoded}' alt='Mapa do Brasil ilustrativo, com linhas decorativas sem representatividade logística real'/>
      <div class='map-copy'><h3>Operação em perspectiva</h3>
      <p>Rastreabilidade, qualidade e desempenho em um só lugar.</p></div>
      <div class='map-caution'>ⓘ Conexões ilustrativas</div>
    </div>""", unsafe_allow_html=True)


def alert_cards(alertas, limit=4):
    if alertas.empty:
        st.success("Nenhum pedido em risco ou atrasado neste filtro.")
        return
    items = []
    for row in alertas.head(limit).itertuples(index=False):
        high = row.situacao_sla == "ATRASADO_EM_ABERTO"
        style = "red" if high else "yellow"
        label = "ATRASADO" if high else "EM RISCO"
        items.append(f"""<div class='alert-item'>
          <div class='alert-line'><span class='alert-id'>{safe(row.id_pedido)}</span>
          <span class='chip {style}'>{label}</span></div>
          <div class='alert-meta'>{safe(row.transportadora)} • {safe(row.cidade_destino)}/{safe(row.uf)} • vence {fmt_date(row.data_limite_sla)}</div>
          <div class='alert-action'>{safe(row.acao_sugerida)}</div>
        </div>""")
    st.markdown("<div class='glass-panel'>" + "".join(items) + "</div>", unsafe_allow_html=True)


def display_orders(df, key="orders") -> str | None:
    """Grid de linha clicável, sem checkboxes ou seleção flutuante de célula.

    O destaque pertence à LINHA inteira do AG Grid. A seleção retorna
    o ID real do pedido, mesmo após ordenar, paginar ou rolar.
    """
    cols = ["id_pedido", "cliente", "transportadora", "cidade_destino", "uf", "status_atual",
            "situacao_sla", "data_limite_sla", "data_hora_ultimo_evento", "data_entrega"]
    shown = df[cols].reset_index(drop=True).copy()
    for col in ["data_limite_sla", "data_hora_ultimo_evento", "data_entrega"]:
        shown[col] = shown[col].map(fmt_date)
    shown["situacao_sla"] = shown["situacao_sla"].map(LABELS)
    shown.columns = ["Pedido", "Cliente", "Transportadora", "Cidade", "UF", "Status", "SLA",
                     "Vencimento", "Último evento", "Entrega"]

    # Chave estável entre reruns e diferente quando o recorte é alterado.
    signature = hashlib.sha256("|".join(shown["Pedido"].astype(str)).encode()).hexdigest()[:12]
    options = {
        "rowSelection": {
            "mode": "singleRow", "checkboxes": False, "headerCheckbox": False,
            "enableClickSelection": True,
        },
        "defaultColDef": {"sortable": True, "resizable": True, "filter": False, "editable": False},
        "columnDefs": [
            {"field": col, "headerName": col, "minWidth": (125 if col in ["Pedido", "Status", "UF"] else 155),
             "flex": (2 if col in ["Cliente", "SLA"] else 1)}
            for col in shown.columns
        ],
        "suppressCellFocus": True,
        "animateRows": False,
        "rowHeight": 36,
        "headerHeight": 38,
        "pagination": True,
        "paginationPageSize": 12,
        "paginationPageSizeSelector": False,
        "suppressFieldDotNotation": True,
    }
    grid = AgGrid(
        shown, gridOptions=options, height=min(550, max(150, 85 + min(len(shown), 12) * 36)),
        theme="streamlit", update_on=["selectionChanged"],
        data_return_mode="AS_INPUT", reload_data=False,
        key=f"{key}_{signature}",
        custom_css={
            ".ag-root-wrapper": {"background-color": "#082b2e", "border": "1px solid #246161", "border-radius": "12px"},
            ".ag-header": {"background-color": "#103d3e", "color": "#dff4ea"},
            ".ag-row": {"background-color": "#082a2d", "color": "#e3f7ed", "cursor": "pointer"},
            ".ag-row-odd": {"background-color": "#0b3032"},
            ".ag-row-hover": {"background-color": "#174f47 !important"},
            ".ag-row-selected": {"background-color": "#24614a !important", "color": "#f2ffee"},
            ".ag-cell": {"border-color": "#174b49"},
        },
    )
    return selected_order_from_grid(grid, df)


def go_to_alerts():
    """Callback executado antes da reexecução dos widgets da barra lateral."""
    st.session_state["pagina"] = "Alertas"
    st.session_state["manual_page"] = "Alertas"


def overview(data, orders):
    title("Tracking Intelligence", "Painel de controle operacional • indicadores calculados a partir dos CSVs fictícios da AGV", animated=True)
    m = scoped_metrics(orders)
    with st.container(key="overview_kpis"):
        kcols = st.columns(4, gap="medium")
        with kcols[0]: kpi("Pedidos monitorados", fmt_int(m["pedidos"]), "orders", "Base de pedidos consolidada")
        with kcols[1]: kpi("OTD geral", fmt_pct(m["otd"]), "target", f"{m['pontuais']} de {m['entregues']} entregas no prazo")
        with kcols[2]: kpi("Entregas realizadas", fmt_int(m["entregues"]), "truck", "Entregas validadas")
        with kcols[3]: kpi("Exigem atenção", fmt_int(m["alertas"]), "alert", f"{m['atrasados_abertos']} atrasados • {m['em_risco']} em risco", warning=True)

    top = st.columns([1.05, .95], gap="medium")
    with top[0]:
        section("OTD por transportadora", "▥")
        chart_carriers(data["pedidos"], key="otd_overview")
        note("O clique nas barras aplica o filtro de transportadora em toda a navegação operacional, sem perder a visão comparativa entre os parceiros.")
    with top[1]:
        section("Atenção prioritária", "♧")
        alerts = data["alertas"]
        alerts = alerts[alerts["id_pedido"].isin(orders["id_pedido"])].copy()
        alert_cards(alerts, limit=4)
        if not alerts.empty and st.button("Abrir central de alertas", key="cta_alerts", use_container_width=True):
            go_to_alerts()
            st.rerun()

    bottom = st.columns([.92, 1.08], gap="medium")
    with bottom[0]:
        section("Situação dos pedidos", "◔")
        chart_situations(orders)
    with bottom[1]:
        section("Resumo por transportadora", "⊞")
        summary = carriers_kpis(orders).sort_values(["otd_pct", "total_pedidos"], ascending=[False, False]).rename(columns={
            "transportadora": "Transportadora", "total_pedidos": "Pedidos", "total_entregues": "Entregues",
            "entregues_no_prazo": "No prazo", "entregues_com_atraso": "Com atraso",
            "otd_pct": "OTD (%)", "alertas": "Alertas"
        })
        if not summary.empty:
            readonly_table(summary, "Resumo por transportadora", max_height=305)
        else:
            st.info("Sem transportadoras para exibir neste recorte.")
        note("O mapa foi incorporado ao pano de fundo do dashboard para reforçar a identidade visual sem ocupar espaço analítico na torre de controle.")

def tracking(data, orders):
    title("Rastreamento de pedidos", "Consulte o estado consolidado e investigue a linha do tempo de um pedido.")
    f1, f2, f3 = st.columns([1.2, 1, 1], gap="small")
    with f1:
        search = st.text_input("Buscar", placeholder="Pedido, cliente ou cidade", key="tr_search")
    with f2:
        labels = st.multiselect(
            "Situação de SLA", options=ORDER, format_func=lambda item: LABELS[item],
            placeholder="Todas as situações", key="tr_sla",
        )
    with f3:
        statuses = st.multiselect(
            "Status logístico", options=sorted(data["pedidos"]["status_atual"].unique()),
            placeholder="Todos os status", key="tr_status",
        )
    result = filter_orders(orders, situacoes=labels, status=statuses, search=search)
    st.caption(f"{len(result)} pedido(s) encontrados • clique em uma linha para consultar seu histórico")
    clicked_id = display_orders(result, key="tracking_table")
    if clicked_id:
        st.session_state["selected_order"] = clicked_id

    # Preserva o pedido após trocar de página, mas nunca exibe um pedido fora
    # do filtro atual (transportadora, busca, SLA ou status).
    selected = keep_selected_order(st.session_state.get("selected_order"), result)
    st.session_state["selected_order"] = selected

    st.download_button("⬇ Exportar pedidos filtrados (CSV)", csv_bytes(result),
                       file_name="pedidos_filtrados.csv", mime="text/csv", key="dl_tracking")
    section("Detalhes e histórico de eventos", "◷")
    if result.empty:
        st.info("Nenhum pedido corresponde aos filtros. Ajuste a busca para consultar outros pedidos.")
        return
    if selected is None:
        st.info("Selecione um pedido na tabela acima para visualizar os detalhes e o histórico de eventos.")
        return

    info = result[result["id_pedido"].astype(str) == selected].iloc[0]
    left, right = st.columns([1, 2], gap="large")
    with left:
        st.markdown("<div class='glass-panel mini'>" +
            f"<div class='panel-eyebrow'>Pedido {safe(selected)}</div>" +
            f"<div class='panel-value'>{safe(info['status_atual'])}</div>" +
            f"<div class='alert-meta'>Cliente: {safe(info['cliente'])}</div>" +
            f"<div class='alert-meta'>SLA: {safe(LABELS.get(info['situacao_sla'], info['situacao_sla']))}</div>" +
            f"<div class='alert-meta'>Prazo: {fmt_date(info['data_limite_sla'])}</div>" +
            f"<div class='alert-meta'>Entrega: {fmt_date(info['data_entrega'])}</div>" + "</div>",
            unsafe_allow_html=True)
        audit = data["auditoria"]
        anomalies = audit[(audit["id_pedido"] == selected) & (audit["decisao"] == "QUARENTENA")]
        st.caption(f"{len(anomalies)} evento(s) do pedido em quarentena (não entram no cálculo).")
    with right:
        events = data["eventos"]
        rows = events[events["id_pedido"] == selected].copy()
        if rows.empty:
            st.warning("Pedido sem eventos válidos de rastreamento.")
        else:
            rows = rows.sort_values("data_hora_dt")
            rows["data_hora_dt"] = rows["data_hora_dt"].map(fmt_date)
            st.markdown(history_table_html(rows), unsafe_allow_html=True)
        if not anomalies.empty:
            with st.expander("Ver eventos isolados na auditoria"):
                readonly_table(anomalies[["id_evento", "codigo_evento", "data_hora", "motivo"]], "Eventos isolados do pedido", max_height=250)


def carriers_page(data, orders):
    title("Desempenho das transportadoras", "Comparação de volume, pontualidade e atraso a partir das entregas válidas.")
    tbl = carriers_kpis(orders)
    m = scoped_metrics(orders)
    k = st.columns(3)
    with k[0]: kpi("OTD do recorte", fmt_pct(m["otd"]), "target", "Somente entregas concluídas")
    with k[1]: kpi("Transportadoras", fmt_int(len(tbl)), "carriers", "No filtro atual")
    with k[2]: kpi("Entregas avaliadas", fmt_int(m["entregues"]), "truck", "Base do denominador do OTD")
    section("Composição das entregas", "▥")
    chart_carrier_mix(orders)
    if not tbl.empty:
        pretty = tbl.sort_values(["otd_pct", "total_pedidos"], ascending=[False, False]).rename(columns={
            "transportadora":"Transportadora", "total_pedidos":"Pedidos", "total_entregues":"Entregues",
            "entregues_no_prazo":"No prazo", "entregues_com_atraso":"Com atraso", "otd_pct":"OTD (%)", "alertas":"Alertas"})
        readonly_table(pretty, "Comparativo de desempenho por transportadora", max_height=300)
    note("Nesta tela, o foco sai do filtro interativo da home e passa para a composição das entregas: volume concluído, pontualidade e atrasos por transportadora.")

def choose_occurrence(category: str) -> None:
    """A seleção funciona via botão nativo, sem depender de Plotly on_select."""
    st.session_state["oco_category"] = toggle_choice(
        st.session_state.get("oco_category", "Todas"), category
    )


def clear_occurrence_category() -> None:
    st.session_state["oco_category"] = "Todas"

def occurrences_page(data, orders):
    title("Ocorrências registradas", "Agrupamento automático por palavras-chave, com possibilidade de múltiplas categorias.")
    occ = data["ocorrencias"].copy()
    occ = occ[occ["id_pedido"].isin(orders["id_pedido"])].copy()
    total = len(occ)
    multi = int(occ["categorias"].fillna("").str.contains("|", regex=False).sum())
    k = st.columns(3)
    with k[0]: kpi("Eventos de ocorrência", fmt_int(total), "tag", "Eventos OCO validados")
    with k[1]: kpi("Multicategoria", fmt_int(multi), "grid", "Ocorrências com mais de um problema")
    with k[2]: kpi("Classificação", "Regras", "spark", "Sem API externa ou LLM")
    if occ.empty:
        st.session_state["oco_category"] = "Todas"
        st.info("Não há ocorrências para a transportadora selecionada.")
        return

    categ = occurrence_counts(occ)
    valid = categ["categoria"].tolist()
    st.session_state["oco_valid_categories"] = valid
    if st.session_state.get("oco_category", "Todas") not in ["Todas"] + valid:
        clear_occurrence_category()
    current = st.session_state.get("oco_category", "Todas")

    section("Tipos de ocorrência", "▥")
    with st.container(key="native_chart_occurrences"):
        st.markdown("<div class='native-chart-eyebrow'>Clique em uma barra para filtrar as ocorrências</div>",
                    unsafe_allow_html=True)
        largest = max(float(categ["quantidade"].max()), 1.0)
        for row in categ.itertuples(index=False):
            category = str(row.categoria)
            clickable_bar(
                key=f"bar_occ_{category}", label=category.replace("_", " "),
                value=float(row.quantidade), maximum=largest,
                selected=current == category, emphasized=(current == "Todas" or current == category),
                callback=lambda chosen=category: choose_occurrence(chosen),
                suffix=str(int(row.quantidade)),
            )
        st.markdown(f"<div class='native-chart-axis'><span>0</span>"
                    f"<span>{int(largest / 2)}</span><span>{int(largest)}</span></div>",
                    unsafe_allow_html=True)
    st.caption("Clique na barra de uma categoria para filtrar a tabela. Ocorrências com duas categorias podem aparecer em ambos os recortes.")

    if current != "Todas":
        active_left, active_right = st.columns([4, 1], vertical_alignment="center")
        count = len(filter_occurrences(occ, current))
        with active_left:
            st.markdown(f"<div class='active-filter'>Categoria: <b>{safe(current)}</b> · {count} ocorrência(s)</div>",
                        unsafe_allow_html=True)
        with active_right:
            st.button("Limpar categoria ✕", on_click=clear_occurrence_category,
                      key="reset_oco_category", use_container_width=True)

    filtered = filter_occurrences(occ, current)
    filtered_display = filtered.copy()
    filtered_display["data_hora_dt"] = filtered_display["data_hora_dt"].map(fmt_date)
    filtered_display["observacao"] = filtered_display["observacao"].fillna("—").astype(str).replace(r"^\s*$", "—", regex=True)
    readonly_table(filtered_display.rename(columns={
        "id_pedido":"Pedido", "data_hora_dt":"Data/hora", "observacao":"Observação",
        "categoria_principal":"Principal", "categorias":"Categorias", "metodo":"Método", "fonte":"Fonte"}),
        "Ocorrências classificadas", max_height=420)
    st.markdown("<div class='agv-export-gap' aria-hidden='true'></div>", unsafe_allow_html=True)
    st.download_button("⬇ Exportar ocorrências exibidas", csv_bytes(filtered),
                       file_name="ocorrencias_filtradas.csv", mime="text/csv")


def quality_page(data, orders):
    carrier = st.session_state.get("carrier", "Todas")
    if carrier == "Todas":
        title("Qualidade e auditoria", "Diagnóstico dos arquivos originais: visão completa da operação.")
    else:
        title("Qualidade e auditoria", f"Registros associados aos pedidos da transportadora {carrier}.")
        st.caption("Registros órfãos sem transportadora identificável só aparecem na visão Todas.")
    diag, audit = filter_quality_by_orders(data["qualidade"], data["auditoria"], orders, carrier)
    quarantined = audit[audit["decisao"] == "QUARENTENA"]
    m = st.columns(4)
    with m[0]: kpi("Eventos de entrada", fmt_int(len(audit)), "database", "Total bruto")
    with m[1]: kpi("Eventos utilizados", fmt_int(int((audit["decisao"] == "UTILIZADO").sum())), "check", "Após validação")
    with m[2]: kpi("Em quarentena", fmt_int(len(quarantined)), "warning", "Preservados na auditoria", warning=True)
    with m[3]: kpi("Anotações de qualidade", fmt_int(len(diag)), "grid", "Categorias podem se sobrepor")
    section("Diagnóstico por tipo", "⊞")
    counts = diag["problema"].value_counts().rename_axis("problema").reset_index(name="quantidade")
    actions = diag.groupby("problema")["tratamento_proposto"].first()
    counts["tratamento"] = counts["problema"].map(actions)
    readonly_table(counts.rename(columns={"problema":"Problema", "quantidade":"Registros", "tratamento":"Tratamento proposto"}),
                 "Diagnóstico por tipo de problema", max_height=340)
    selected = st.selectbox("Investigar tipo de problema", ["Todos"]+sorted(diag["problema"].unique().tolist()))
    issues = diag if selected == "Todos" else diag[diag["problema"] == selected]
    readonly_table(issues, "Registros do diagnóstico de qualidade", max_height=280)
    section("Quarentena de eventos", "⚑")
    st.caption("A quarentena afasta os registros inválidos dos indicadores, mas mantém o histórico original na auditoria.")
    readonly_table(quarantined[["id_evento", "id_pedido", "codigo_evento", "data_hora", "decisao", "motivo"]],
                 "Eventos em quarentena", max_height=310)
    st.markdown("<div class='agv-export-gap' aria-hidden='true'></div>", unsafe_allow_html=True)
    st.download_button("⬇ Baixar auditoria completa", csv_bytes(audit), file_name="auditoria_eventos.csv", mime="text/csv")


def alerts_page(data, orders):
    title("Central de alertas", "Prioridades calculadas na referência fixa do desafio; envio externo não habilitado.")
    alerts = data["alertas"]
    alerts = alerts[alerts["id_pedido"].isin(orders["id_pedido"])].copy()
    overdue = int((alerts["prioridade"] == "ALTA").sum())
    risk = int((alerts["prioridade"] == "ATENCAO").sum())
    cols = st.columns(3)
    with cols[0]: kpi("Pedidos prioritários", fmt_int(len(alerts)), "warning", "Necessitam análise", warning=True)
    with cols[1]: kpi("Atrasados em aberto", fmt_int(overdue), "alert", "Prioridade alta", warning=True)
    with cols[2]: kpi("Vencem nas próximas 24 h", fmt_int(risk), "clock", "Em risco")
    st.caption("As ações sugeridas são orientações automáticas e não representam contatos realizados.")
    if alerts.empty:
        st.success("Não há alertas no filtro selecionado.")
    else:
        selected_prio = st.radio("Prioridade", ["Todas", "ALTA", "ATENCAO"], horizontal=True)
        subset = alerts if selected_prio == "Todas" else alerts[alerts["prioridade"] == selected_prio]
        shown = subset.copy()
        shown["data_limite_sla"] = shown["data_limite_sla"].map(fmt_date)
        shown = shown[["id_pedido", "transportadora", "prioridade", "data_limite_sla", "ultima_ocorrencia", "acao_sugerida"]]
        shown.columns = ["Pedido", "Transportadora", "Prioridade", "Prazo", "Ocorrência", "Ação recomendada"]
        readonly_table(shown, "Pedidos com alerta operacional", max_height=470)
        st.markdown("<div class='agv-export-gap' aria-hidden='true'></div>", unsafe_allow_html=True)
        st.download_button("⬇ Exportar alertas do recorte", csv_bytes(subset), file_name="alertas_operacionais.csv", mime="text/csv")
    section("Mensagem operacional simulada", "✉")
    if len(orders) == len(data["pedidos"]):
        message = (OUTPUT / "alerta_operacional.txt").read_text(encoding="utf-8")
    else:
        from src.ocorrencias import mensagem_alerta
        message = mensagem_alerta(alerts)
    with st.expander("Prévia da mensagem (não enviada)", expanded=True):
        st.code(message, language="text")
    st.download_button("⬇ Baixar mensagem simulada", message.encode("utf-8"), file_name="alerta_operacional.txt", mime="text/plain")


def footer():
    st.markdown("""<div class='footer'>AGV Tracking Intelligence • Protótipo técnico para processo seletivo
    • Dados fictícios • Sem integração real com TMS / AGV GO / EDI • Mapa com conexões ilustrativas • Interface v14d</div>""", unsafe_allow_html=True)


def main():
    inject_style()
    with st.sidebar:
        st.markdown(f"""<div class='brand'>
          {render_logo()}
          <div class='brand-sub'>TECHLAB · INTELLIGENCE</div>
          <div class='brand-standalone'>Protótipo técnico • não oficial</div></div>""", unsafe_allow_html=True)
        st.markdown("<div class='nav-heading'>Navegação</div>", unsafe_allow_html=True)
        if "pagina" not in st.session_state:
            st.session_state["pagina"] = PAGE_OPTIONS[0]
        default_index = PAGE_OPTIONS.index(st.session_state["pagina"]) if st.session_state["pagina"] in PAGE_OPTIONS else 0
        forced_page = st.session_state.pop("manual_page", None)
        selected = option_menu(
            menu_title=None,
            options=PAGE_OPTIONS,
            icons=PAGE_ICONS,
            default_index=default_index,
            manual_select=PAGE_OPTIONS.index(forced_page) if forced_page in PAGE_OPTIONS else None,
            key="pagina_menu",
            styles={
                "container": {
                    "padding": "0!important", "margin": "0!important",
                    "background": "transparent!important", "background-color": "transparent!important",
                    "border": "0!important", "box-shadow": "none!important",
                },
                "nav-link": {
                    "font-size": "0.95rem", "font-weight": "600", "color": "#d9eee4", "padding": "11px 12px",
                    "border-radius": "12px", "margin": "2px 0", "transition": "all .15s ease-in-out",
                    "background": "transparent", "--hover-color": "rgba(160,235,80,.08)",
                },
                "nav-link-selected": {
                    "background": "linear-gradient(100deg,rgba(170,230,64,.23),rgba(34,111,93,.10))",
                    "color": "#f7fff9", "border": "1px solid rgba(174,233,69,.42)"
                },
                "icon": {"font-size": "1.05rem", "color": "#b5eb45"},
                "menu-title": {"font-size": "0.98rem", "font-weight": "700", "color": "#effbf4", "padding": "0 4px 8px 0"},
            },
        )
        st.session_state["pagina"] = selected
        st.divider()
        st.markdown("<div class='eyebrow'>ESCOPO DE CONSULTA</div>", unsafe_allow_html=True)
        # Os nomes vêm da própria tabela de pedidos, sem valores artificiais.
        try:
            preview = pd.read_csv(OUTPUT / "pedidos_sla.csv", sep=";", usecols=["transportadora"])
            carriers = sorted(preview["transportadora"].dropna().unique().tolist())
        except (FileNotFoundError, pd.errors.EmptyDataError):
            carriers = []
        st.session_state["carrier_choices"] = carriers
        if st.session_state.get("carrier", "Todas") not in ["Todas"] + carriers:
            st.session_state["carrier"] = "Todas"
        st.selectbox("Transportadora", ["Todas"] + carriers, key="carrier")
        st.divider()
        st.markdown(f"""<div class='header-badge'>◷ Base do desafio: <b>{REFERENCIA:%d/%m/%Y %H:%M}</b></div>
        <div style='margin-top:11px;font-size:.75rem;color:#89b0a6'>Referência fixa, não é monitoramento em tempo real.</div>""", unsafe_allow_html=True)

    _, header_actions = st.columns([3.5, 1], vertical_alignment="center")
    with header_actions:
        if st.button("⟳ Atualizar dados", use_container_width=True, type="primary", help="Reexecuta o pipeline a partir dos três CSVs de origem"):
            try:
                from src.main import main as execute_pipeline
                with st.spinner("Validando arquivos, processando e publicando relatórios..."):
                    resultado = execute_pipeline()
                st.session_state["resultado_atualizacao"] = resultado
                st.session_state.pop("erro_atualizacao", None)
                st.rerun()
            except Exception as exc:
                st.session_state["erro_atualizacao"] = str(exc)
                st.session_state.pop("resultado_atualizacao", None)
                st.rerun()
    if st.session_state.get("erro_atualizacao"):
        st.error("Atualização cancelada: " + st.session_state["erro_atualizacao"] +
                 " Os relatórios anteriores foram preservados.")
    if st.session_state.get("resultado_atualizacao"):
        resumo = st.session_state["resultado_atualizacao"]
        m = resumo["metricas"]
        dif = resumo["alteracoes"]
        st.success(f"Dados atualizados com sucesso! {m['pedidos']} pedidos • "
                   f"{m['eventos']} eventos • {m['eventos_quarentena']} em quarentena • "
                   f"{m['alertas']} alertas.")
        if dif.get("comparacao_disponivel"):
            st.caption(f"Mudanças desde a execução anterior: +{dif['novos_pedidos']} pedidos, "
                       f"-{dif['pedidos_removidos']} pedidos e +{dif['novos_eventos']} eventos.")
        else:
            st.caption("Primeira atualização com histórico: a comparação começa na próxima execução.")
        st.caption("Hora da execução: " + resumo["executado_em"] +
                   " · O SLA continua calculado na referência fixa de 24/09/2026 às 18h.")
        if st.button("Fechar resumo", key="dismiss_update"):
            st.session_state.pop("resultado_atualizacao", None)
            st.session_state.pop("erro_atualizacao", None)
            st.rerun()

    if not (OUTPUT / "pedidos_sla.csv").exists():
        try:
            from src.main import main as execute_pipeline
            execute_pipeline()
        except Exception as exc:
            st.error(f"Falha ao gerar os relatórios iniciais: {exc}")
            st.stop()
    try:
        data = load_data()
    except (FileNotFoundError, pd.errors.ParserError) as exc:
        st.error(f"Saída ausente ou inválida: {exc}. Execute `python -m src.main` na raiz do projeto.")
        st.stop()
    current_carrier = st.session_state.get("carrier", "Todas")
    orders = filter_orders(data["pedidos"], transportadora=current_carrier)
    if st.session_state.get("last_oco_carrier") != current_carrier:
        # Um novo recorte não herda o clique feito no gráfico da transportadora anterior.
        st.session_state["oco_category"] = "Todas"
        st.session_state["oco_chart_revision"] = st.session_state.get("oco_chart_revision", 0) + 1
        st.session_state["last_oco_carrier"] = current_carrier
    # Seleção de pedido persiste entre páginas, mas não invade outro recorte.
    st.session_state["selected_order"] = keep_selected_order(
        st.session_state.get("selected_order"), orders
    )
    if current_carrier != "Todas":
        filter_col, clear_col = st.columns([4, 1], vertical_alignment="center")
        with filter_col:
            st.markdown(f"<div class='active-filter'>Filtro ativo: <b>{safe(current_carrier)}</b> · "
                        f"{len(orders)} pedidos neste recorte</div>", unsafe_allow_html=True)
        with clear_col:
            st.button("Limpar filtro ✕", on_click=clear_carrier, key="reset_carrier", use_container_width=True)
    page = st.session_state["pagina"]
    # Versão da animação muda SOMENTE quando a página muda; filtros, busca,
    # seleção de pedido e atualização de dados não reiniciam a transição.
    previous_page = st.session_state.get("agv_previous_page")
    if previous_page is None:
        st.session_state["agv_page_revision"] = 0
    elif previous_page != page:
        st.session_state["agv_page_revision"] = st.session_state.get("agv_page_revision", 0) + 1
    st.session_state["agv_previous_page"] = page
    revision = st.session_state.get("agv_page_revision", 0)
    wrapper_key = "agv_page_initial" if revision == 0 else f"agv_page_reveal_{revision}"
    # O conteúdo da nova página é revelado em círculo; a barra lateral permanece
    # estável e o efeito CSS não exige JavaScript nem intercepta cliques.
    with st.container(key=wrapper_key):
        if page == "Visão geral": overview(data, orders)
        elif page == "Rastreamento": tracking(data, orders)
        elif page == "Transportadoras": carriers_page(data, orders)
        elif page == "Ocorrências": occurrences_page(data, orders)
        elif page == "Qualidade": quality_page(data, orders)
        else: alerts_page(data, orders)
        footer()


if __name__ == "__main__":
    main()
