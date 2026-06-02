import streamlit as st

AVE_COLORS = {
    "azul": "#0f1c75",
    "celeste": "#1c73f5",
    "verde": "#00ab0d",
    "amarillo": "#ffb500",
    "rojo": "#e74c3c",
    "gris_fondo": "#f7f9fc",
    "gris_texto": "#333333",
}


def apply_ave_styles():
    st.markdown(
        f"""
        <style>
        .main {{ background-color: {AVE_COLORS['gris_fondo']}; }}
        h1, h2, h3 {{ color: {AVE_COLORS['azul']}; }}
        .stButton > button {{
            background-color: {AVE_COLORS['azul']};
            color: white;
            border-radius: 8px;
            border: none;
            padding: 0.55rem 1rem;
            font-weight: 700;
        }}
        .stButton > button:hover {{
            background-color: {AVE_COLORS['celeste']};
            color: white;
        }}
        .ave-title {{
            font-size: 2rem;
            font-weight: 800;
            color: {AVE_COLORS['azul']};
            margin-bottom: 0.2rem;
        }}
        .ave-subtitle {{
            font-size: 1rem;
            color: {AVE_COLORS['gris_texto']};
        }}
        .metric-card {{
            background: white;
            padding: 1rem;
            border-radius: 14px;
            border-left: 7px solid {AVE_COLORS['celeste']};
            box-shadow: 0 2px 9px rgba(0,0,0,0.08);
            min-height: 110px;
        }}
        .metric-value {{
            font-size: 2rem;
            font-weight: 800;
            color: {AVE_COLORS['azul']};
        }}
        .metric-label {{
            font-size: 0.92rem;
            color: #555;
        }}
        .small-note {{ color:#666; font-size:0.9rem; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value, border_color: str = None):
    color = border_color or AVE_COLORS["celeste"]
    st.markdown(
        f"""
        <div class="metric-card" style="border-left-color:{color};">
            <div class="metric-value">{value}</div>
            <div class="metric-label">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
