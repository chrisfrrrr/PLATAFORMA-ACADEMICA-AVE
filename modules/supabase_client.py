import streamlit as st
from supabase import create_client


def get_supabase_client():
    """Crea cliente de Supabase usando secrets.toml."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def test_supabase_connection():
    """
    Prueba básica de conexión con Supabase.
    En esta fase valida que el cliente pueda crearse.
    En fases posteriores se validará contra tablas reales.
    """
    try:
        client = get_supabase_client()
        if client:
            return True, "Conexión con Supabase creada correctamente."
        return False, "No se pudo crear el cliente de Supabase."
    except Exception as e:
        return False, str(e)
