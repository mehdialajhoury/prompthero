import streamlit as st
import os

def load_css_file(css_file_path):
    """Charge un fichier CSS et l'injecte dans Streamlit"""
    try:
        with open(css_file_path, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Erreur de chargement CSS : {e}")

def apply_custom_style():
    """Fonction principale appelée par l'app"""
    # Calcul dynamique du chemin pour être robuste
    # On remonte de src/ui/ vers la racine, puis on va dans assets/css/
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir)) # Remonte à prompthero/
    css_path = os.path.join(root_dir, "assets", "css", "style.css")
    
    load_css_file(css_path)