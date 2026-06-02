import streamlit as st
from supabase import create_client


def get_supabase_client():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def test_supabase_connection():
    try:
        client = get_supabase_client()
        if client:
            return True, "Conexión con Supabase creada correctamente."
        return False, "No se pudo crear el cliente de Supabase."
    except Exception as e:
        return False, str(e)
