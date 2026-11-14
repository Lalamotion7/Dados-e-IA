"""Configurações visuais do gráfico de composição, sem dependência do Streamlit."""
from __future__ import annotations

import plotly.graph_objects as go


def show_carrier_mix_legend(fig: go.Figure) -> go.Figure:
    """Uma legenda SEM moldura, gerada dentro do SVG do Plotly.

    Desliga a legenda nativa e usa exatamente uma anotação interna
    no rodapé do gráfico: No prazo (verde) seguido por Com atraso (laranja).
    Não há st.markdown/HTML externo nem outros contêineres de legenda.
    """
    fig.update_layout(showlegend=False, height=345, margin=dict(t=30, b=76, l=18, r=18))
    fig.add_annotation(
        x=1, y=-0.22, xref="paper", yref="paper",
        xanchor="right", yanchor="middle", showarrow=False,
        text=(
            "<span style='color:#A3E635'>■</span>&nbsp; No prazo"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
            "<span style='color:#FF9F54'>■</span>&nbsp; Com atraso"
        ),
        align="right", font=dict(color="#E1F1E9", size=13),
        bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)", borderwidth=0,
    )
    return fig
