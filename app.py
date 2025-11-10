import streamlit as st
import pandas as pd
import json
import sys
import os

# Ajoute le répertoire du script au chemin Python pour permettre les importations locales
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importe les fonctions de la base de données et de l'extraction LLM
import database
from run_extraction import extract_data_from_llm, SYSTEM_PROMPT_FILE

# --- Configuration de la Page ---
st.set_page_config(page_title="Analyseur d'Articles", layout="wide")

# --- Initialisation de la Base de Données ---
# Crée les tables `users` et `extractions` si elles n'existent pas
database.init_db()

# --- Initialisation de l'État de Session ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.user_id = None
    st.session_state.user_data = None # Pour stocker toutes les données de l'utilisateur

# --- Interface d'Authentification ---
def show_auth_ui():
    """Affiche les formulaires de connexion et de création de compte dans la barre latérale."""
    st.sidebar.title("Accès Utilisateur")
    auth_tab1, auth_tab2 = st.sidebar.tabs(["👤 Connexion", "➕ Créer un compte"])

    # Formulaire de Connexion
    with auth_tab1:
        with st.form("login_form"):
            username = st.text_input("Nom d'utilisateur", key="login_user")
            password = st.text_input("Mot de passe", type="password", key="login_pass")
            submitted = st.form_submit_button("Se connecter")
            if submitted:
                user = database.get_user(username)
                if user and database.check_password(password, user['password_hash']):
                    st.session_state.logged_in = True
                    st.session_state.username = user['username']
                    st.session_state.user_id = user['id']
                    st.session_state.user_data = user # Stocker toutes les données de l'utilisateur
                    st.rerun()
                else:
                    st.error("Nom d'utilisateur ou mot de passe incorrect.")

    # Formulaire de Création de Compte
    with auth_tab2:
        with st.form("signup_form"):
            new_username = st.text_input("Nom d'utilisateur", key="signup_user")
            new_password = st.text_input("Mot de passe", type="password", key="signup_pass")
            confirm_password = st.text_input("Confirmer le mot de passe", type="password", key="signup_confirm")
            signup_submitted = st.form_submit_button("Créer le compte")
            if signup_submitted:
                if not all([new_username, new_password, confirm_password]):
                    st.error("Veuillez remplir tous les champs.")
                elif new_password != confirm_password:
                    st.error("Les mots de passe ne correspondent pas.")
                else:
                    success, message = database.add_user(new_username, new_password)
                    if success:
                        st.success(message)
                        st.info("Vous pouvez maintenant vous connecter avec votre nouveau compte.")
                    else:
                        st.error(message)

# --- Application Principale ---

# Si l'utilisateur n'est pas connecté, afficher l'interface d'authentification
if not st.session_state.logged_in:
    st.warning("Veuillez vous connecter ou créer un compte pour utiliser l'application.")
    show_auth_ui()

# Si l'utilisateur est connecté, afficher l'application principale
else:
    st.sidebar.title(f"Bienvenue, {st.session_state.username}")
    if st.sidebar.button("Se déconnecter"):
        # Réinitialiser l'état de la session pour la déconnexion
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.title("🤖 Analyseur d'Articles pour Levées de Fonds")

    main_tab1, main_tab2 = st.tabs(["✍️ Analyse d'Article", "📚 Mon Historique"])

    # --- Onglet d'Analyse ---
    with main_tab1:
        st.header("Extraire les informations d'un article")
        st.write("Collez le texte d'un article ci-dessous pour extraire les informations clés.")
        
        article_text = st.text_area("Texte de l'article", height=300, placeholder="Collez ici le texte complet de l'article...")

        if st.button("Lancer l'analyse", type="primary"):
            if article_text.strip():
                with st.spinner("Analyse en cours... Le LLM réfléchit..."):
                    try:
                        # Déterminer le prompt système à utiliser
                        if st.session_state.user_data and st.session_state.user_data['custom_system_prompt']:
                            system_prompt_to_use = st.session_state.user_data['custom_system_prompt']
                        else:
                            with open(SYSTEM_PROMPT_FILE, 'r', encoding='utf-8') as f:
                                system_prompt_to_use = f.read()

                        if not system_prompt_to_use:
                             st.error(f"Le prompt système est vide. Vérifiez le fichier '{SYSTEM_PROMPT_FILE}' ou votre prompt personnalisé.")
                        else:
                            extracted_data = extract_data_from_llm(article_text, system_prompt_to_use)

                            if extracted_data:
                                st.success("✅ Analyse terminée avec succès !")
                                st.subheader("Données extraites :")
                                st.json(extracted_data)

                                # Calculer le hash du contenu
                                content_hash = database.calculate_content_hash(article_text)

                                # Sauvegarder dans PostgreSQL (upsert)
                                with st.spinner("Sauvegarde dans votre historique..."):
                                    success, message = database.add_extraction(
                                        user_id=st.session_state.user_id,
                                        original_content=article_text,
                                        extracted_data=json.dumps(extracted_data),
                                        content_hash=content_hash
                                    )
                                if success:
                                    st.success("💾 Données sauvegardées/mises à jour dans votre historique !")
                                else:
                                    st.error(f"Erreur de sauvegarde : {message}")
                            else:
                                st.error("❌ L'extraction a échoué. Le LLM n'a pas pu retourner de données valides.")
                    except Exception as e:
                        st.error(f"Une erreur inattendue est survenue : {e}")
            else:
                st.warning("Veuillez coller le texte d'un article avant de lancer l'analyse.")

    # --- Onglet Historique ---
    with main_tab2:
        st.header("Historique de vos analyses")
        extractions = database.get_extractions_by_user(st.session_state.user_id)

        if not extractions:
            st.info("Vous n'avez pas encore d'analyse dans votre historique.")
        else:
            history_data = []
            for ext in extractions:
                data = ext['extracted_data']
                if isinstance(data, str):
                    try: data = json.loads(data)
                    except json.JSONDecodeError: data = {"error": "invalid json"}
                
                history_data.append({
                    'ID': ext['id'],
                    'Date': ext['created_at'].strftime('%Y-%m-%d %H:%M'),
                    'Nom Entreprise': data.get('nom_entreprise', 'N/A'),
                    'Montant Levé': data.get('montant_leve', 'N/A'),
                    'Investisseurs': ', '.join(data.get('investisseurs', [])) if data.get('investisseurs') else 'N/A',
                    'data_json': json.dumps(data, indent=2)
                })
            
            df = pd.DataFrame(history_data)

            st.dataframe(df[['ID', 'Date', 'Nom Entreprise', 'Montant Levé', 'Investisseurs']], use_container_width=True)

            st.subheader("Télécharger les extractions")
            for index, row in df.iterrows():
                st.download_button(
                    label=f"📥 Télécharger JSON pour ID {row['ID']}",
                    data=row['data_json'],
                    file_name=f"extraction_{row['ID']}.json",
                    mime="application/json",
                    key=f"download_{row['ID']}"
                )

    # --- Éditeur de Prompt dans la Barre Latérale ---
    st.sidebar.title("Configuration")
    with st.sidebar.expander("Éditer le prompt système", expanded=False):
        # Déterminer la valeur initiale de l'éditeur de prompt
        if st.session_state.user_data and st.session_state.user_data['custom_system_prompt']:
            initial_prompt_value = st.session_state.user_data['custom_system_prompt']
            st.info("Vous utilisez un prompt personnalisé.")
        else:
            with open(SYSTEM_PROMPT_FILE, 'r', encoding='utf-8') as f:
                initial_prompt_value = f.read()
            st.info("Vous utilisez le prompt système par défaut.")

        prompt_area = st.text_area(
            "Prompt Système:",
            value=initial_prompt_value,
            height=400,
            key="prompt_editor"
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Sauvegarder le Prompt Personnalisé"):
                success, message = database.update_user_prompt(st.session_state.user_id, prompt_area)
                if success:
                    st.session_state.user_data['custom_system_prompt'] = prompt_area # Mettre à jour l'état de la session
                    st.success("Prompt personnalisé sauvegardé !")
                    st.rerun()
                else:
                    st.error(f"Erreur lors de la sauvegarde du prompt : {message}")
        with col2:
            if st.button("Réinitialiser au Prompt par Défaut"):
                success, message = database.update_user_prompt(st.session_state.user_id, None) # Mettre à NULL
                if success:
                    st.session_state.user_data['custom_system_prompt'] = None # Mettre à jour l'état de la session
                    st.success("Prompt réinitialisé au prompt par défaut !")
                    st.rerun()
                else:
                    st.error(f"Erreur lors de la réinitialisation du prompt : {message}")