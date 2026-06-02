import streamlit as st


AVE_COLORS = {
    "azul": "#0f1c75",
    "celeste": "#1c73f5",
    "verde": "#00ab0d",
    "amarillo": "#ffb500",
    "gris_fondo": "#f7f9fc",
    "gris_texto": "#333333"
}


def apply_ave_styles():
    """Aplica estilos visuales base de AVE UVG."""
    st.markdown(
        f"""
        <style>
        .main {{
            background-color: {AVE_COLORS["gris_fondo"]};
        }}

        h1, h2, h3 {{
            color: {AVE_COLORS["azul"]};
        }}

        .stButton > button {{
            background-color: {AVE_COLORS["azul"]};
            color: white;
            border-radius: 8px;
            border: none;
            padding: 0.5rem 1rem;
            font-weight: 600;
        }}

        .stButton > button:hover {{
            background-color: {AVE_COLORS["celeste"]};
            color: white;
        }}

        .ave-card {{
            background-color: white;
            padding: 1.2rem;
            border-radius: 12px;
            border-left: 6px solid {AVE_COLORS["celeste"]};
            box-shadow: 0px 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 1rem;
        }}

        .ave-title {{
            font-size: 2rem;
            font-weight: 800;
            color: {AVE_COLORS["azul"]};
        }}

        .ave-subtitle {{
            font-size: 1rem;
            color: {AVE_COLORS["gris_texto"]};
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
