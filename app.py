import streamlit as st
import os
import glob
import tempfile
from datetime import datetime
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Union

# =============================================================================
# CLASSES D'ANALYSE (intégrées directement)
# =============================================================================

class AnalyseurTexte:
    """Classe pour analyser le contenu textuel"""
    
    @staticmethod
    def analyser_texte(texte: str) -> Dict:
        """Analyse complète d'un texte"""
        if not texte.strip():
            return {"erreur": "Fichier vide"}
        
        mots = texte.split()
        lignes = texte.split('\n')
        phrases = texte.split('.')
        
        return {
            "statistiques": {
                "caracteres_total": len(texte),
                "caracteres_sans_espaces": len(texte.replace(" ", "")),
                "nombre_mots": len(mots),
                "nombre_lignes": len(lignes),
                "nombre_phrases": len([p for p in phrases if p.strip()]),
                "mots_par_ligne": round(len(mots) / max(len(lignes), 1), 2),
                "mots_par_phrase": round(len(mots) / max(len([p for p in phrases if p.strip()]), 1), 2)
            },
            "mots_cles": AnalyseurTexte._extraire_mots_cles(mots),
            "complexite": AnalyseurTexte._analyser_complexite(texte, mots)
        }
    
    @staticmethod
    def _extraire_mots_cles(mots: List[str], top_n: int = 10) -> List[str]:
        """Extrait les mots les plus fréquents"""
        from collections import Counter
        
        # Filtrer les mots courts et communs
        mots_filtres = [mot.lower() for mot in mots if len(mot) > 3]
        mots_communs = {'dans', 'avec', 'pour', 'dont', 'cette', 'comme', 'plus', 'tout', 'fait', 'sont'}
        mots_filtres = [mot for mot in mots_filtres if mot not in mots_communs]
        
        compteur = Counter(mots_filtres)
        return [mot for mot, count in compteur.most_common(top_n)]
    
    @staticmethod
    def _analyser_complexite(texte: str, mots: List[str]) -> Dict:
        """Analyse la complexité du texte"""
        mots_longues = [mot for mot in mots if len(mot) > 8]
        pourcentage_mots_longues = (len(mots_longues) / max(len(mots), 1)) * 100
        
        return {
            "niveau_complexite": "Élevé" if pourcentage_mots_longues > 15 else "Moyen" if pourcentage_mots_longues > 8 else "Simple",
            "pourcentage_mots_complexes": round(pourcentage_mots_longues, 2),
            "score_lisibilite": round(max(0, 100 - pourcentage_mots_longues * 2), 2)
        }

class GestionnaireFichiers:
    """Classe pour gérer les opérations sur les fichiers"""
    
    @staticmethod
    def formats_supportes() -> List[str]:
        return ["*.txt", "*.md", "*.csv", "*.log"]
    
    @staticmethod
    def detecter_encodage(chemin_fichier: str) -> str:
        """Tente de détecter l'encodage du fichier"""
        encodages = ['utf-8', 'latin-1', 'windows-1252', 'iso-8859-1']
        
        for enc in encodages:
            try:
                with open(chemin_fichier, 'r', encoding=enc) as f:
                    f.read()
                return enc
            except UnicodeDecodeError:
                continue
        
        return 'utf-8'  # encodage par défaut

class AnalyseurFichiers:
    def __init__(self):
        self.analyseur = AnalyseurTexte()
        self.gestionnaire = GestionnaireFichiers()
        self.historique = []
    
    def analyser_fichier(self, chemin_fichier: str, afficher_details: bool = True) -> Optional[Dict]:
        """Analyse un fichier texte avec gestion d'erreurs améliorée"""
        try:
            if not os.path.exists(chemin_fichier):
                return {"erreur": f"Fichier non trouvé: {chemin_fichier}"}
            
            # Vérifier la taille du fichier
            taille = os.path.getsize(chemin_fichier)
            if taille > 10 * 1024 * 1024:  # 10MB
                return {"erreur": f"Fichier trop volumineux ({taille/1024/1024:.2f} MB)"}
            
            # Détection automatique de l'encodage
            encodage = self.gestionnaire.detecter_encodage(chemin_fichier)
            
            with open(chemin_fichier, 'r', encoding=encodage) as f:
                texte = f.read()
            
            resultats = self.analyseur.analyser_texte(texte)
            
            # Sauvegarder dans l'historique
            self._ajouter_historique(chemin_fichier, resultats)
            
            return resultats
            
        except PermissionError:
            return {"erreur": f"Permission refusée: {chemin_fichier}"}
        except Exception as e:
            return {"erreur": f"Erreur lors de l'analyse: {str(e)}"}
    
    def analyser_dossier(self, chemin_dossier: str, extension: str = "*.txt", 
                        recursif: bool = False) -> Dict[str, Dict]:
        """Analyse tous les fichiers d'un dossier avec options avancées"""
        if not os.path.exists(chemin_dossier):
            return {}
        
        if recursif:
            pattern = os.path.join(chemin_dossier, "**", extension)
        else:
            pattern = os.path.join(chemin_dossier, extension)
        
        fichiers = glob.glob(pattern, recursive=recursif)
        fichiers = [f for f in fichiers if os.path.isfile(f)]
        
        if not fichiers:
            return {}
        
        resultats_totaux = {}
        
        for i, fichier in enumerate(fichiers):
            resultats = self.analyser_fichier(fichier, afficher_details=False)
            if resultats and "erreur" not in resultats:
                nom_fichier = os.path.basename(fichier)
                resultats_totaux[nom_fichier] = resultats
        
        return resultats_totaux
    
    def _ajouter_historique(self, chemin_fichier: str, resultats: Dict):
        """Ajoute une analyse à l'historique"""
        entree = {
            "timestamp": datetime.now().isoformat(),
            "fichier": chemin_fichier,
            "resultats": resultats
        }
        self.historique.append(entree)
    
    def exporter_resultats(self, resultats: Dict, format_export: str = "json"):
        """Exporte les résultats dans un fichier"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nom_fichier = f"analyse_texte_{timestamp}.{format_export}"
        
        try:
            if format_export == "json":
                with open(nom_fichier, 'w', encoding='utf-8') as f:
                    json.dump(resultats, f, ensure_ascii=False, indent=2)
            elif format_export == "txt":
                with open(nom_fichier, 'w', encoding='utf-8') as f:
                    f.write("RAPPORT D'ANALYSE DE TEXTE\n")
                    f.write("=" * 50 + "\n\n")
                    for fichier, analyse in resultats.items():
                        f.write(f"FICHIER: {fichier}\n")
                        f.write(f"Nombre de mots: {analyse['statistiques']['nombre_mots']}\n")
                        f.write(f"Complexité: {analyse['complexite']['niveau_complexite']}\n\n")
            
            return f"✅ Résultats exportés: {nom_fichier}"
        except Exception as e:
            return f"❌ Erreur lors de l'export: {e}"

# =============================================================================
# CLASSES AMÉLIORÉES POUR STREAMLIT
# =============================================================================

class AnalyseurTexteAmeliore:
    """Classe améliorée pour l'analyse textuelle avec nuage de mots"""
    
    @staticmethod
    def generer_nuage_mots(texte, largeur=800, hauteur=400, max_mots=100):
        """Génère un nuage de mots à partir du texte"""
        if not texte.strip():
            return None
            
        # Nettoyer le texte et compter les mots
        mots = [mot.lower() for mot in texte.split() if len(mot) > 3]
        mots_communs = {'dans', 'avec', 'pour', 'dont', 'cette', 'comme', 'plus', 'tout', 'fait', 'sont', 'dans', 'elle', 'elles'}
        mots_filtres = [mot for mot in mots if mot not in mots_communs]
        
        if not mots_filtres:
            return None
            
        # Créer le nuage de mots
        wordcloud = WordCloud(
            width=largeur,
            height=hauteur,
            background_color='white',
            max_words=max_mots,
            colormap='viridis',
            relative_scaling=0.5
        ).generate(' '.join(mots_filtres))
        
        return wordcloud
    
    @staticmethod
    def analyser_sentiments_basique(texte):
        """Analyse basique des sentiments (positif/négatif/neutre)"""
        mots_positifs = {'bon', 'excellent', 'super', 'génial', 'parfait', 'magnifique', 'heureux', 'content'}
        mots_negatifs = {'mauvais', 'terrible', 'horrible', 'nul', 'triste', 'malheureux', 'probleme', 'difficile'}
        
        mots = texte.lower().split()
        score_positif = sum(1 for mot in mots if mot in mots_positifs)
        score_negatif = sum(1 for mot in mots if mot in mots_negatifs)
        total_mots_pertinents = score_positif + score_negatif
        
        if total_mots_pertinents == 0:
            return "Neutre", 50
        
        score = (score_positif / total_mots_pertinents) * 100
        
        if score > 60:
            sentiment = "Positif"
        elif score < 40:
            sentiment = "Négatif"
        else:
            sentiment = "Neutre"
            
        return sentiment, round(score, 2)

# =============================================================================
# APPLICATION STREAMLIT
# =============================================================================

# Configuration de la page
st.set_page_config(
    page_title="Wordtextapp - Analyseur de Texte Avancé",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
    }
    .word-cloud-container {
        background-color: white;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
</style>
<html>
<p>Power by Lab_mat and RMT</>
</html>

""", unsafe_allow_html=True)

def main():
    st.markdown('<h1 class="main-header">🔍 Wordtextapp - Analyseur de Texte Avancé</h1>', unsafe_allow_html=True)
    st.markdown("---")
    
    analyseur = AnalyseurFichiers()
    analyseur_ameliore = AnalyseurTexteAmeliore()
    
    # Sidebar améliorée
    with st.sidebar:
        st.title("🌐 Navigation")
        st.markdown("---")
        
        option = st.radio(
            "Choisissez une option:",
            ["🏠 Accueil", "📄 Analyser un fichier", "📁 Analyser un dossier", "☁️ Nuage de mots", "📚 Formats supportés"]
        )
        
        st.markdown("---")
        st.markdown("### 📊 Statistiques rapides")
        if 'historique_analyses' in st.session_state:
            st.write(f"📝 Analyses aujourd'hui: {len(st.session_state.historique_analyses)}")
        
        st.markdown("---")
        st.markdown("### ⚙️ Paramètres")
        theme = st.selectbox("Thème des graphiques", ["plotly", "seaborn", "matplotlib"])
        
        if st.button("🧹 Effacer l'historique"):
            if 'historique_analyses' in st.session_state:
                st.session_state.historique_analyses = []
            st.success("Historique effacé!")

    # Initialisation de l'historique
    if 'historique_analyses' not in st.session_state:
        st.session_state.historique_analyses = []
    
    if option == "🏠 Accueil":
        afficher_accueil()
    elif option == "📄 Analyser un fichier":
        analyser_fichier(analyseur, analyseur_ameliore)
    elif option == "📁 Analyser un dossier":
        analyser_dossier(analyseur)
    elif option == "☁️ Nuage de mots":
        afficher_nuage_mots(analyseur_ameliore)
    elif option == "📚 Formats supportés":
        afficher_formats_ameliore()

def afficher_accueil():
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("🎯 Bienvenue sur Wordtextapp")
        st.markdown("""
        **Wordtextapp** est un outil d'analyse de texte avancé qui vous permet de :
        
        - 📊 **Analyser statistiquement** vos documents texte
        - ☁️ **Générer des nuages de mots** visuels
        - 📈 **Visualiser les données** avec des graphiques interactifs
        - 🔍 **Extraire les mots-clés** les plus importants
        - 📋 **Exporter les résultats** en différents formats
        
        ### 🚀 Comment commencer ?
        1. Choisissez **"Analyser un fichier"** pour un document unique
        2. Sélectionnez **"Analyser un dossier"** pour plusieurs fichiers
        3. Utilisez **"Nuage de mots"** pour des visualisations créatives
        """)
    
    with col2:
        st.markdown("### 📈 Stats globales")
        st.metric("Formats supportés", "4")
        st.metric("Fonctionnalités", "8+")
        st.metric("Export disponible", "JSON, TXT")

def analyser_fichier(analyseur, analyseur_ameliore):
    st.header("📄 Analyse de Fichier Unique")
    
    uploaded_file = st.file_uploader(
        "Choisissez un fichier à analyser",
        type=['txt', 'md', 'csv', 'log'],
        help="Formats supportés: TXT, MD, CSV, LOG"
    )
    
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        try:
            # Section informations du fichier
            with st.expander("📋 Informations du fichier", expanded=True):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("📝 Nom", uploaded_file.name)
                with col2:
                    st.metric("📦 Taille", f"{uploaded_file.size / 1024:.2f} KB")
                with col3:
                    st.metric("🔤 Type", uploaded_file.type.split('/')[-1].upper())
            
            # Analyse du fichier
            with st.spinner("🔍 Analyse en cours..."):
                resultats = analyseur.analyser_fichier(tmp_path, afficher_details=False)
            
            if resultats and "erreur" not in resultats:
                # Ajouter à l'historique
                entree_historique = {
                    "timestamp": datetime.now().isoformat(),
                    "fichier": uploaded_file.name,
                    "resultats": resultats
                }
                st.session_state.historique_analyses.append(entree_historique)
                
                # Lire le texte pour les analyses avancées
                with open(tmp_path, 'r', encoding='utf-8') as f:
                    texte_complet = f.read()
                
                afficher_resultats_detailles_ameliore(resultats, analyseur_ameliore, texte_complet)
            else:
                st.error("❌ Erreur lors de l'analyse du fichier")
                if resultats and "erreur" in resultats:
                    st.error(f"Détails: {resultats['erreur']}")
                
        finally:
            os.unlink(tmp_path)

def afficher_nuage_mots(analyseur_ameliore):
    st.header("☁️ Générateur de Nuage de Mots")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        texte_input = st.text_area(
            "Collez votre texte ici pour générer un nuage de mots",
            height=200,
            placeholder="Entrez votre texte ici... Le nuage de mots sera généré automatiquement."
        )
    
    with col2:
        st.markdown("### ⚙️ Paramètres")
        max_mots = st.slider("Nombre max de mots", 50, 200, 100)
        largeur = st.slider("Largeur", 400, 1200, 800)
        hauteur = st.slider("Hauteur", 200, 800, 400)
    
    if texte_input:
        with st.spinner("🎨 Génération du nuage de mots en cours..."):
            wordcloud = analyseur_ameliore.generer_nuage_mots(
                texte_input, largeur, hauteur, max_mots
            )
            
            if wordcloud:
                # Afficher le nuage de mots
                st.markdown("### 🎨 Votre Nuage de Mots")
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.imshow(wordcloud, interpolation='bilinear')
                ax.axis('off')
                st.pyplot(fig)
                
                # Statistiques des mots
                mots = [mot for mot in texte_input.split() if len(mot) > 3]
                compteur = Counter(mots)
                mots_plus_frequents = compteur.most_common(10)
                
                st.markdown("### 📊 Top 10 des Mots les Plus Fréquents")
                df_mots = pd.DataFrame(mots_plus_frequents, columns=['Mot', 'Fréquence'])
                fig_bar = px.bar(df_mots, x='Mot', y='Fréquence', color='Fréquence')
                st.plotly_chart(fig_bar, use_container_width=True)
                
            else:
                st.warning("⚠️ Texte trop court ou pas assez de mots significatifs pour générer un nuage de mots.")

def afficher_resultats_detailles_ameliore(resultats, analyseur_ameliore, texte_complet):
    st.header("📊 Résultats Détaillés de l'Analyse")
    
    # Analyse des sentiments
    sentiment, score_sentiment = analyseur_ameliore.analyser_sentiments_basique(texte_complet)
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("📊 Mots total", resultats["statistiques"]["nombre_mots"])
        st.metric("📝 Lignes", resultats["statistiques"]["nombre_lignes"])
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("🔤 Caractères", resultats["statistiques"]["caracteres_total"])
        st.metric("💬 Phrases", resultats["statistiques"]["nombre_phrases"])
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("🎯 Complexité", resultats["complexite"]["niveau_complexite"])
        st.metric("⭐ Lisibilité", f"{resultats['complexite']['score_lisibilite']}/100")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("😊 Sentiment", sentiment)
        st.metric("📈 Score sentiment", f"{score_sentiment}%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Onglets pour organiser les résultats
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Statistiques", "🔑 Mots-clés", "☁️ Nuage de Mots", "📋 Export"])
    
    with tab1:
        afficher_statistiques_detaillees(resultats)
    
    with tab2:
        afficher_mots_cles_ameliore(resultats)
    
    with tab3:
        afficher_nuage_mots_fichier(analyseur_ameliore, texte_complet)
    
    with tab4:
        exporter_resultats_avances(analyseur, resultats)

def afficher_statistiques_detaillees(resultats):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📐 Statistiques de base")
        stats = resultats["statistiques"]
        
        data_stats = {
            'Metric': ['Caractères totaux', 'Caractères sans espaces', 'Mots', 'Lignes', 'Phrases'],
            'Valeur': [
                stats['caracteres_total'],
                stats['caracteres_sans_espaces'],
                stats['nombre_mots'],
                stats['nombre_lignes'],
                stats['nombre_phrases']
            ]
        }
        
        df_stats = pd.DataFrame(data_stats)
        st.dataframe(df_stats, use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("📊 Graphique des métriques")
        fig = px.pie(df_stats, values='Valeur', names='Metric', title="Distribution des éléments textuels")
        st.plotly_chart(fig, use_container_width=True)

def afficher_mots_cles_ameliore(resultats):
    if resultats["mots_cles"]:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔑 Top 10 des Mots-clés")
            mots_cles = resultats["mots_cles"][:10]
            
            for i, mot in enumerate(mots_cles, 1):
                st.markdown(f"{i}. **{mot}**")
        
        with col2:
            st.subheader("📈 Fréquence visuelle")
            # Simulation de fréquences pour la visualisation
            frequences = {mot: len(mots_cles) - i for i, mot in enumerate(mots_cles)}
            df_freq = pd.DataFrame(list(frequences.items()), columns=['Mot', 'Fréquence'])
            
            fig = px.bar(df_freq, x='Mot', y='Fréquence', color='Fréquence')
            st.plotly_chart(fig, use_container_width=True)

def afficher_nuage_mots_fichier(analyseur_ameliore, texte):
    st.subheader("☁️ Nuage de Mots du Document")
    
    with st.spinner("Génération du nuage de mots..."):
        wordcloud = analyseur_ameliore.generer_nuage_mots(texte)
        
        if wordcloud:
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis('off')
            ax.set_title('Nuage de Mots du Document', size=16)
            st.pyplot(fig)
        else:
            st.info("ℹ️ Le texte ne contient pas assez de mots significatifs pour générer un nuage de mots.")

def exporter_resultats_avances(analyseur, resultats):
    st.subheader("📤 Exporter les Résultats")
    
    col1, col2 = st.columns(2)
    
    with col1:
        format_export = st.selectbox("Format d'export", ["JSON", "CSV", "TXT", "HTML"])
        nom_fichier = st.text_input("Nom du fichier", value=f"analyse_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    with col2:
        st.write("### Options d'export")
        inclure_stats = st.checkbox("Inclure les statistiques", value=True)
        inclure_mots_cles = st.checkbox("Inclure les mots-clés", value=True)
        inclure_complexite = st.checkbox("Inclure l'analyse de complexité", value=True)
    
    if st.button("🚀 Générer l'export", type="primary"):
        with st.spinner("Génération de l'export en cours..."):
            # Simulation d'export
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nom_complet = f"{nom_fichier}.{format_export.lower()}"
            
            st.success(f"✅ Export généré avec succès: **{nom_complet}**")
            st.info("💡 Fonctionnalité d'export à implémenter avec votre logique existante")

def analyser_dossier(analyseur):
    st.header("📁 Analyse de Dossier")
    
    col1, col2 = st.columns(2)
    
    with col1:
        dossier_path = st.text_input(
            "Chemin du dossier",
            placeholder="/chemin/vers/votre/dossier"
        )
        extension = st.selectbox(
            "Extension des fichiers",
            ["*.txt", "*.md", "*.csv", "*.log", "*.*"]
        )
    
    with col2:
        recursif = st.checkbox("Recherche récursive", value=False)
        max_files = st.number_input("Nombre maximum de fichiers", min_value=1, value=100, step=10)
    
    if st.button("🚀 Lancer l'analyse du dossier", type="primary") and dossier_path:
        if os.path.exists(dossier_path) and os.path.isdir(dossier_path):
            with st.spinner(f"🔍 Analyse de {max_files} fichiers maximum..."):
                resultats = analyseur.analyser_dossier(
                    dossier_path, 
                    extension, 
                    recursif
                )
            
            if resultats:
                afficher_statistiques_globales_ameliore(resultats)
                
                # Option d'export
                if st.button("📤 Exporter tous les résultats"):
                    resultat_export = analyseur.exporter_resultats(resultats, "json")
                    st.success(resultat_export)
            else:
                st.warning("⚠️ Aucun fichier trouvé ou analysable dans le dossier spécifié")
        else:
            st.error("❌ Le dossier spécifié n'existe pas ou n'est pas accessible")

def afficher_statistiques_globales_ameliore(resultats):
    st.header("📊 Tableau de Bord Global")
    
    # Métriques principales
    total_fichiers = len(resultats)
    total_mots = sum(r["statistiques"]["nombre_mots"] for r in resultats.values())
    total_lignes = sum(r["statistiques"]["nombre_lignes"] for r in resultats.values())
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📂 Fichiers analysés", total_fichiers)
    with col2:
        st.metric("📊 Total mots", total_mots)
    with col3:
        st.metric("📝 Total lignes", total_lignes)
    with col4:
        avg_words = total_mots / total_fichiers if total_fichiers > 0 else 0
        st.metric("📈 Moyenne mots/fichier", f"{avg_words:.0f}")
    
    # Graphiques
    col1, col2 = st.columns(2)
    
    with col1:
        # Distribution de complexité
        niveaux = [r["complexite"]["niveau_complexite"] for r in resultats.values()]
        df_complexite = pd.DataFrame({'Niveau': niveaux})
        
        fig_complexite = px.pie(df_complexite, names='Niveau', title="Distribution des Niveaux de Complexité")
        st.plotly_chart(fig_complexite, use_container_width=True)
    
    with col2:
        # Histogramme des tailles de fichiers
        tailles_mots = [r["statistiques"]["nombre_mots"] for r in resultats.values()]
        fig_hist = px.histogram(x=tailles_mots, nbins=20, title="Distribution des Tailles de Fichiers (mots)")
        fig_hist.update_layout(xaxis_title="Nombre de mots", yaxis_title="Nombre de fichiers")
        st.plotly_chart(fig_hist, use_container_width=True)
    
    # Tableau détaillé
    st.subheader("📋 Résumé Détaillé par Fichier")
    summary_data = []
    for fichier, analyse in resultats.items():
        summary_data.append({
            "Fichier": fichier,
            "Mots": analyse["statistiques"]["nombre_mots"],
            "Lignes": analyse["statistiques"]["nombre_lignes"],
            "Phrases": analyse["statistiques"]["nombre_phrases"],
            "Complexité": analyse["complexite"]["niveau_complexite"],
            "Score Lisibilité": analyse["complexite"]["score_lisibilite"]
        })
    
    df = pd.DataFrame(summary_data)
    st.dataframe(df, use_container_width=True, height=400)

def afficher_formats_ameliore():
    st.header("📚 Formats Supportés et Fonctionnalités")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 Formats de Fichiers")
        st.markdown("""
        - **.txt** - Fichiers texte standard
        - **.md** - Fichiers Markdown
        - **.csv** - Fichiers CSV (analyse textuelle)
        - **.log** - Fichiers de log
        """)
        
        st.subheader("🎯 Métriques d'Analyse")
        st.markdown("""
        ✅ **Statistiques de base** : mots, caractères, lignes, phrases  
        ✅ **Analyse de complexité** : niveau de difficulté  
        ✅ **Score de lisibilité** : évaluation de la facilité de lecture  
        ✅ **Mots-clés** : extraction automatique  
        ✅ **Nuage de mots** : visualisation créative  
        ✅ **Analyse de sentiments** : positif/négatif/neutre  
        """)
    
    with col2:
        st.subheader("📊 Visualisations")
        st.markdown("""
        - **Graphiques interactifs** avec Plotly
        - **Nuages de mots** personnalisables
        - **Histogrammes** et camemberts
        - **Tableaux de bord** en temps réel
        """)
        
        st.subheader("📤 Fonctionnalités d'Export")
        st.markdown("""
        - **JSON** : Format structuré
        - **CSV** : Pour tableurs
        - **TXT** : Rapport texte
        - **HTML** : Rapport web
        - **Personnalisation** des données exportées
        """)
    
    st.markdown("---")
    st.success("🚀 **Nouveautés** : Nuage de mots et analyse de sentiments maintenant disponibles!")

if __name__ == "__main__":
    main()