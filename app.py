import json
import os
import sys
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

# Ajoute le répertoire du script au chemin Python pour permettre les importations locales
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importe les fonctions de la base de données et de l'extraction LLM
import database
import prompt_manager
from run_extraction import SYSTEM_PROMPT_FILE, extract_data_from_llm
from wordpress_connector import WordPressConnector

# --- Configuration de la Page ---
st.set_page_config(page_title="Analyseur d'Articles", layout="wide", page_icon="🤖")


# --- Initialisation de la Base de Données ---
# Crée les tables `users` et `extractions` si elles n'existent pas
database.init_db()


# --- Initialisation de l'État de Session ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.user_id = None
    st.session_state.user_data = (
        None  # Pour stocker toutes les données de l'utilisateur
    )

# Initialisation des paramètres WordPress dans l'état de session
if "wp_base_domain" not in st.session_state:
    st.session_state.wp_base_domain = ""
if "wp_subdomains" not in st.session_state:
    st.session_state.wp_subdomains = []
if "wp_selected_subdomain" not in st.session_state:
    st.session_state.wp_selected_subdomain = None
if "wp_selected_posts" not in st.session_state:
    st.session_state.wp_selected_posts = []


# --- Interface d'Authentification ---
def show_auth_ui():
    """Affiche les formulaires de connexion et de création de compte dans la barre latérale."""
    st.sidebar.title("Accès Utilisateur")
    auth_tab1, auth_tab2 = st.sidebar.tabs(["👤 Connexion", "➕ Créer un compte"])

    # Formulaire de Connexion
    with auth_tab1:
        st.markdown(
            "<div style='text-align: center; margin-bottom: 2rem;'><h3>Bon retour ! 👋</h3></div>",
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            username = st.text_input("Nom d'utilisateur", key="login_user")
            password = st.text_input("Mot de passe", type="password", key="login_pass")
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Se connecter", use_container_width=True)
            if submitted:
                user = database.get_user(username)
                if user and database.check_password(password, user["password_hash"]):
                    st.session_state.logged_in = True
                    st.session_state.username = user["username"]
                    st.session_state.user_id = user["id"]
                    st.session_state.user_data = (
                        user  # Stocker toutes les données de l'utilisateur
                    )
                    st.toast(f"Bienvenue {user['username']} !", icon="👋")
                    st.rerun()
                else:
                    st.error("Nom d'utilisateur ou mot de passe incorrect.")

    # Formulaire de Création de Compte
    with auth_tab2:
        st.markdown(
            "<div style='text-align: center; margin-bottom: 2rem;'><h3>Rejoignez-nous ! 🚀</h3></div>",
            unsafe_allow_html=True,
        )
        with st.form("signup_form"):
            new_username = st.text_input("Nom d'utilisateur", key="signup_user")
            new_password = st.text_input(
                "Mot de passe", type="password", key="signup_pass"
            )
            confirm_password = st.text_input(
                "Confirmer le mot de passe", type="password", key="signup_confirm"
            )
            st.markdown("<br>", unsafe_allow_html=True)
            signup_submitted = st.form_submit_button(
                "Créer le compte", use_container_width=True
            )
            if signup_submitted:
                if not all([new_username, new_password, confirm_password]):
                    st.error("Veuillez remplir tous les champs.")
                elif new_password != confirm_password:
                    st.error("Les mots de passe ne correspondent pas.")
                else:
                    success, message = database.add_user(new_username, new_password)
                    if success:
                        st.success(message)
                        st.info(
                            "Vous pouvez maintenant vous connecter avec votre nouveau compte."
                        )
                    else:
                        st.error(message)


# --- Application Principale ---

# Si l'utilisateur n'est pas connecté, afficher l'interface d'authentification
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
        <div style='text-align: center; padding: 2rem 0;'>
            <h1>🤖 Analyseur d'Articles</h1>
            <p style='color: #9CA3AF; font-size: 1.1rem;'>L'intelligence artificielle au service de vos analyses.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        show_auth_ui()

# Si l'utilisateur est connecté, afficher l'application principale
else:
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"### 👤 {st.session_state.username}")

        if st.button("📊 Dashboard", type="secondary", use_container_width=True):
            st.session_state.show_history = False
            st.session_state.selected_action = None
            st.session_state.show_dashboard = True
            st.rerun()

        if st.button("📚 Historique", type="secondary", use_container_width=True):
            st.session_state.show_history = True
            st.session_state.show_dashboard = False
            st.rerun()

        st.markdown("---")

        if st.button("Se déconnecter", use_container_width=True):
            # Réinitialiser l'état de la session pour la déconnexion
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Header avec navigation
    st.markdown(
        """
        <div style='text-align: center;'>
            <h1>🤖 Analyseur d'Articles</h1>
            <h3>Plateforme d'intelligence artificielle pour l'analyse</h3>
        </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Initialiser l'état pour l'affichage
    if "show_history" not in st.session_state:
        st.session_state.show_history = False
    if "selected_action" not in st.session_state:
        st.session_state.selected_action = None
    if "show_dashboard" not in st.session_state:
        st.session_state.show_dashboard = False

    # Navigation conditionnelle selon l'état
    if st.session_state.show_history:
        # Afficher l'historique
        if st.button("← Retour", type="secondary"):
            st.session_state.show_history = False
            st.rerun()

        st.markdown("---")
        st.header("📚 Historique de vos analyses")
        st.caption("Consultez et exportez vos analyses passées.")

        extractions = database.get_extractions_by_user(st.session_state.user_id)

        if not extractions:
            st.info("Vous n'avez pas encore d'analyse dans votre historique.")
        else:
            history_data = []
            for ext in extractions:
                data = ext["extracted_data"]
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except json.JSONDecodeError:
                        data = {"error": "invalid json"}

                # Récupérer la liste des investisseurs
                investisseurs_list = data.get("Investisseurs", [])
                if isinstance(investisseurs_list, list):
                    investisseurs_str = (
                        ", ".join(investisseurs_list) if investisseurs_list else "N/A"
                    )
                else:
                    investisseurs_str = (
                        str(investisseurs_list) if investisseurs_list else "N/A"
                    )

                # Extraire la date de levée pour séparer jour/mois/année
                date_levee = data.get("Date_levée", "")
                jour, mois, annee = "N/A", "N/A", "N/A"
                if date_levee and "/" in date_levee:
                    parts = date_levee.split("/")
                    if len(parts) == 3:
                        jour, mois, annee = parts[0], parts[1], parts[2]

                history_data.append(
                    {
                        "ID": ext["id"],
                        "Date_extraction": ext["created_at"].strftime("%Y-%m-%d %H:%M"),
                        "Nom_start-up": data.get("Nom_start-up", "N/A"),
                        "Type": data.get("Type", "N/A"),
                        "Montant": data.get("Montant", "N/A"),
                        "Date_levée": date_levee if date_levee else "N/A",
                        "Jour": jour,
                        "Mois": mois,
                        "Année": annee,
                        "Tour": data.get("Tour", "N/A"),
                        "Investisseurs": investisseurs_str,
                        "Lien": data.get("Lien") or ext.get("source_url", "N/A"),
                        "data_json": json.dumps(data, indent=2, ensure_ascii=False),
                    }
                )

            df = pd.DataFrame(history_data)
            display_columns = [col for col in df.columns if col != "data_json"]

            st.dataframe(
                df[display_columns],
                use_container_width=True,
                height=600,
            )

            csv = df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 Télécharger tout l'historique en CSV",
                data=csv,
                file_name=f"historique_extractions_{st.session_state.username}.csv",
                mime="text/csv",
            )

            st.subheader("Télécharger les extractions individuelles")
            cols_per_row = 4
            for i in range(0, len(df), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(cols):
                    if i + j < len(df):
                        row = df.iloc[i + j]
                        with col:
                            st.download_button(
                                label=f"📥 ID {row['ID']}",
                                data=row["data_json"],
                                file_name=f"extraction_{row['ID']}.json",
                                mime="application/json",
                                key=f"download_{row['ID']}",
                                use_container_width=True,
                            )

    elif st.session_state.selected_action == "analyse":
        # --- Interface d'Analyse ---
        if st.button("← Retour au menu", type="secondary"):
            st.session_state.selected_action = None
            st.rerun()
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.header("Extraire les informations")
            st.caption(
                "Collez le texte d'un article ci-dessous pour extraire les informations clés via l'IA."
            )

            col1, col2 = st.columns([2, 1])

            with col1:
                article_text = st.text_area(
                    "Texte de l'article",
                    height=300,
                    placeholder="Collez ici le texte complet de l'article...",
                    label_visibility="collapsed",
                )

            with col2:
                st.info(
                    "💡 **Conseil** : Copiez le texte complet de l'article, y compris le titre et la date pour de meilleurs résultats."
                )
                source_url = st.text_input(
                    "URL source (OBLIGATOIRE) ⚠️",
                    placeholder="https://exemple.com/article...",
                    help="URL de la page d'où provient l'article - requis pour la traçabilité",
                )
                st.markdown("<br>", unsafe_allow_html=True)
                analyze_btn = st.button(
                    "🚀 Lancer l'analyse", type="primary", use_container_width=True
                )

            st.markdown("</div>", unsafe_allow_html=True)

        if analyze_btn:
            if not article_text.strip():
                st.warning(
                    "Veuillez coller le texte d'un article avant de lancer l'analyse."
                )
            elif not source_url or not source_url.strip():
                st.error(
                    "⚠️ L'URL source est obligatoire pour la traçabilité. Veuillez la renseigner."
                )
            else:
                with st.spinner("Analyse en cours... Le LLM réfléchit..."):
                    try:
                        # Déterminer le prompt système à utiliser
                        prompt_id = (
                            st.session_state.user_data.get("selected_prompt_id")
                            if st.session_state.user_data
                            else None
                        )
                        if not prompt_id:
                            prompt_id = prompt_manager.get_default_prompt_id()

                        system_prompt_to_use = prompt_manager.get_prompt_by_id(
                            prompt_id
                        )
                        if not system_prompt_to_use:
                            # Fallback sur le fichier par défaut
                            with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
                                system_prompt_to_use = f.read()

                        if not system_prompt_to_use:
                            st.error(
                                f"Le prompt système est vide. Vérifiez le fichier '{SYSTEM_PROMPT_FILE}' ou votre prompt personnalisé."
                            )
                        else:
                            extracted_data = extract_data_from_llm(
                                article_text, system_prompt_to_use
                            )

                            if extracted_data:
                                st.success("✅ Analyse terminée avec succès !")
                                st.subheader("Données extraites :")
                                st.json(extracted_data)

                                # Calculer le hash du contenu
                                content_hash = database.calculate_content_hash(
                                    article_text
                                )

                                # Sauvegarder dans PostgreSQL (upsert)
                                with st.spinner("Sauvegarde dans votre historique..."):
                                    success, message = database.add_extraction(
                                        user_id=st.session_state.user_id,
                                        original_content=article_text,
                                        extracted_data=json.dumps(extracted_data),
                                        content_hash=content_hash,
                                        source_url=source_url.strip(),
                                    )
                                if success:
                                    st.success(
                                        "💾 Données sauvegardées/mises à jour dans votre historique !"
                                    )
                                    st.info(
                                        "↗️ Redirection vers l'historique dans 2 secondes..."
                                    )
                                    import time

                                    time.sleep(2)
                                    st.session_state.active_tab = (
                                        1  # Index de l'onglet Historique
                                    )
                                    st.rerun()
                                else:
                                    st.error(f"Erreur de sauvegarde : {message}")
                            else:
                                st.error(
                                    "❌ L'extraction a échoué. Le LLM n'a pas pu retourner de données valides."
                                )
                    except Exception as e:
                        st.error(f"Une erreur inattendue est survenue : {e}")

    elif st.session_state.selected_action == "import_wp":
        # --- Interface Import WordPress ---
        if st.button("← Retour au menu", type="secondary"):
            st.session_state.selected_action = None
            st.rerun()
        st.header("Importer des Articles depuis WordPress Multisite")
        st.caption(
            "Connectez-vous à votre WordPress multisite et importez des articles par verticale."
        )

        # Configuration WordPress
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("1️⃣ Configuration WordPress")

        # Pré-remplir avec mind.eu.com et les sites prédéfinis
        if not st.session_state.wp_base_domain:
            st.session_state.wp_base_domain = "mind.eu.com"
        if not st.session_state.wp_subdomains:
            st.session_state.wp_subdomains = [
                "media",
                "health",
                "retail",
                "rh",
                "fintech",
            ]

        # Toujours en mode sous-répertoires pour mind.eu.com
        st.session_state.wp_use_subdirectory = True

        col1, col2 = st.columns([1, 2])
        with col1:
            st.info(f"🌐 **Domaine:** mind.eu.com")
            st.caption("Configuration pré-définie")

        with col2:
            st.markdown("**Sélectionnez un site :**")

            # Boutons de sélection pour les sites mind
            cols = st.columns(5)
            sites_config = {
                "media": {"icon": "📰", "label": "Media"},
                "health": {"icon": "🏥", "label": "Health"},
                "retail": {"icon": "🛍️", "label": "Retail"},
                "rh": {"icon": "👥", "label": "RH"},
                "fintech": {"icon": "💰", "label": "Fintech"},
            }

            for idx, (site_key, site_info) in enumerate(sites_config.items()):
                with cols[idx]:
                    if st.button(
                        f"{site_info['icon']}\n{site_info['label']}",
                        key=f"select_{site_key}",
                        use_container_width=True,
                    ):
                        st.session_state.wp_selected_subdomain = site_key
                        st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

        # Sélection du sous-domaine
        if st.session_state.wp_base_domain and st.session_state.wp_subdomains:
            # Utiliser le site sélectionné ou attendre la sélection
            if (
                "wp_selected_subdomain" in st.session_state
                and st.session_state.wp_selected_subdomain
            ):
                selected_subdomain = st.session_state.wp_selected_subdomain
            else:
                selected_subdomain = None

            if selected_subdomain:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader(f"2️⃣ Site sélectionné : mind.eu.com/{selected_subdomain}")
                st.caption(f"🔗 https://mind.eu.com/{selected_subdomain}")

                # Test de connexion
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("🔍 Tester la connexion"):
                        if st.session_state.wp_use_subdirectory:
                            site_format = f"{st.session_state.wp_base_domain}/{selected_subdomain}"
                        else:
                            site_format = f"{selected_subdomain}.{st.session_state.wp_base_domain}"

                        with st.spinner(f"Test de connexion à {site_format}..."):
                            try:
                                # Créer le connecteur
                                connector = WordPressConnector(
                                    st.session_state.wp_base_domain,
                                    use_subdirectory=st.session_state.wp_use_subdirectory,
                                )

                                result = connector.test_connection(selected_subdomain)

                                if result["success"]:
                                    st.success(f"✅ Connexion réussie à {site_format}")
                                    st.info(f"🔗 URL de l'API : {result['url']}")
                                    st.session_state.wp_selected_subdomain = (
                                        selected_subdomain
                                    )
                                else:
                                    st.error(f"❌ {result['message']}")
                                    st.warning(f"🔗 URL testée : {result['url']}")
                                    if result["status_code"]:
                                        st.info(f"Code HTTP : {result['status_code']}")

                                    # Suggestions d'aide
                                    with st.expander("💡 Suggestions de dépannage"):
                                        st.markdown("""
                                        **Vérifications à faire :**

                                        1. **Format du domaine** : Entrez uniquement `example.com` (sans http/https)

                                        2. **Sous-domaine correct** : Si votre site est `tech.example.com`, entrez :
                                           - Domaine : `example.com`
                                           - Sous-domaine : `tech`

                                        3. **WordPress REST API activée** : Testez manuellement dans votre navigateur :
                                           `https://tech.example.com/wp-json/wp/v2`

                                           Vous devriez voir une réponse JSON.

                                        4. **Firewall/Protection** : Certains plugins de sécurité WordPress bloquent l'API REST.
                                           Vérifiez : Wordfence, iThemes Security, etc.

                                        5. **HTTPS requis** : L'API WordPress utilise HTTPS par défaut.
                                        """)
                            except Exception as e:
                                st.error(f"Erreur inattendue: {str(e)}")

                st.markdown("</div>", unsafe_allow_html=True)

                # Chargement des articles
                if st.session_state.wp_selected_subdomain == selected_subdomain:
                    st.subheader("3️⃣ Sélection des Articles")

                    # Initialiser les filtres dans session_state si nécessaire
                    if "wp_filter_search" not in st.session_state:
                        st.session_state.wp_filter_search = ""
                    if "wp_filter_per_page" not in st.session_state:
                        st.session_state.wp_filter_per_page = 20
                    if "wp_filter_date" not in st.session_state:
                        st.session_state.wp_filter_date = "Tous"
                    if "wp_filter_categories" not in st.session_state:
                        st.session_state.wp_filter_categories = []
                    if "wp_filter_tags" not in st.session_state:
                        st.session_state.wp_filter_tags = []
                    if "wp_filter_reset_counter" not in st.session_state:
                        st.session_state.wp_filter_reset_counter = 0

                    # Filtres
                    with st.expander("🎛️ Filtres et recherche", expanded=True):
                        # Ligne 1: Recherche et nombre d'articles
                        st.markdown("**🔍 Recherche**")
                        col_search1, col_search2 = st.columns([3, 1])
                        with col_search1:
                            search_term = st.text_input(
                                "Mot-clé",
                                value=st.session_state.wp_filter_search,
                                placeholder="Rechercher dans les articles...",
                                label_visibility="collapsed",
                                key=f"search_input_{st.session_state.wp_filter_reset_counter}",
                            )
                            st.session_state.wp_filter_search = search_term

                        with col_search2:
                            per_page = st.slider(
                                "Articles par page",
                                5,
                                50,
                                st.session_state.wp_filter_per_page,
                                key=f"per_page_slider_{st.session_state.wp_filter_reset_counter}",
                            )
                            st.session_state.wp_filter_per_page = per_page

                        st.divider()

                        # Ligne 2: Filtres par taxonomie
                        st.markdown("**📑 Taxonomies**")
                        col_tax1, col_tax2 = st.columns(2)

                        with col_tax1:
                            # Récupérer les catégories disponibles
                            try:
                                connector = WordPressConnector(
                                    st.session_state.wp_base_domain,
                                    use_subdirectory=st.session_state.wp_use_subdirectory,
                                )

                                categories = connector.get_categories(
                                    selected_subdomain
                                )
                                cat_options = {
                                    cat["name"]: cat["id"] for cat in categories
                                }
                                selected_cats = st.multiselect(
                                    "🏷️ Catégories",
                                    options=list(cat_options.keys()),
                                    default=st.session_state.wp_filter_categories,
                                    key=f"categories_select_{st.session_state.wp_filter_reset_counter}",
                                )
                                st.session_state.wp_filter_categories = selected_cats
                                selected_cat_ids = [
                                    cat_options[cat] for cat in selected_cats
                                ]
                            except:
                                selected_cat_ids = []
                                st.caption("⚠️ Impossible de charger les catégories")

                        with col_tax2:
                            # Récupérer les tags disponibles
                            try:
                                connector = WordPressConnector(
                                    st.session_state.wp_base_domain,
                                    use_subdirectory=st.session_state.wp_use_subdirectory,
                                )

                                tags = connector.get_tags(selected_subdomain)
                                tag_options = {tag["name"]: tag["id"] for tag in tags}
                                selected_tags = st.multiselect(
                                    "🔖 Tags",
                                    options=list(tag_options.keys()),
                                    default=st.session_state.wp_filter_tags,
                                    key=f"tags_select_{st.session_state.wp_filter_reset_counter}",
                                )
                                st.session_state.wp_filter_tags = selected_tags
                                selected_tag_ids = [
                                    tag_options[tag] for tag in selected_tags
                                ]
                            except:
                                selected_tag_ids = []
                                st.caption("⚠️ Impossible de charger les tags")

                        st.divider()

                        # Ligne 3: Filtre par date
                        st.markdown("**📅 Période**")
                        col_date1, col_date2 = st.columns([1, 2])

                        with col_date1:
                            date_filter = st.selectbox(
                                "Période",
                                options=[
                                    "Tous",
                                    "Dernière semaine",
                                    "Dernier mois",
                                    "3 derniers mois",
                                    "6 derniers mois",
                                    "Dernière année",
                                    "Personnalisé",
                                ],
                                index=[
                                    "Tous",
                                    "Dernière semaine",
                                    "Dernier mois",
                                    "3 derniers mois",
                                    "6 derniers mois",
                                    "Dernière année",
                                    "Personnalisé",
                                ].index(st.session_state.wp_filter_date),
                                key=f"date_filter_select_{st.session_state.wp_filter_reset_counter}",
                                label_visibility="collapsed",
                            )
                            st.session_state.wp_filter_date = date_filter

                        date_after = None
                        date_before = None

                        with col_date2:
                            if date_filter == "Personnalisé":
                                col_date_from, col_date_to = st.columns(2)
                                today = datetime.now()
                                with col_date_from:
                                    date_from = st.date_input(
                                        "Du", value=today - timedelta(days=30)
                                    )
                                    date_after = datetime.combine(
                                        date_from, datetime.min.time()
                                    ).isoformat()
                                with col_date_to:
                                    date_to = st.date_input("Au", value=today)
                                    date_before = datetime.combine(
                                        date_to, datetime.max.time()
                                    ).isoformat()
                            else:
                                if date_filter != "Tous":
                                    today = datetime.now()
                                    if date_filter == "Dernière semaine":
                                        date_after = (
                                            today - timedelta(days=7)
                                        ).isoformat()
                                    elif date_filter == "Dernier mois":
                                        date_after = (
                                            today - timedelta(days=30)
                                        ).isoformat()
                                    elif date_filter == "3 derniers mois":
                                        date_after = (
                                            today - timedelta(days=90)
                                        ).isoformat()
                                    elif date_filter == "6 derniers mois":
                                        date_after = (
                                            today - timedelta(days=180)
                                        ).isoformat()
                                    elif date_filter == "Dernière année":
                                        date_after = (
                                            today - timedelta(days=365)
                                        ).isoformat()

                                if date_after:
                                    st.caption(
                                        f"📆 Articles depuis le {datetime.fromisoformat(date_after).strftime('%d/%m/%Y')}"
                                    )

                        st.divider()

                        # Boutons d'action
                        col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
                        with col_btn1:
                            load_button = st.button(
                                "📥 Charger les articles",
                                type="primary",
                                use_container_width=True,
                            )
                        with col_btn2:
                            if st.button("🔄 Réinitialiser", use_container_width=True):
                                st.session_state.wp_filter_search = ""
                                st.session_state.wp_filter_per_page = 20
                                st.session_state.wp_filter_date = "Tous"
                                st.session_state.wp_filter_categories = []
                                st.session_state.wp_filter_tags = []
                                st.session_state.wp_filter_reset_counter += 1
                                st.rerun()
                        with col_btn3:
                            # Afficher le nombre de filtres actifs
                            active_filters = 0
                            if search_term:
                                active_filters += 1
                            if selected_cat_ids:
                                active_filters += len(selected_cat_ids)
                            if selected_tag_ids:
                                active_filters += len(selected_tag_ids)
                            if date_filter != "Tous":
                                active_filters += 1

                            if active_filters > 0:
                                st.info(
                                    f"🎯 {active_filters} filtre{'s' if active_filters > 1 else ''}"
                                )

                # Bouton pour charger les articles
                if load_button:
                    with st.spinner("Chargement des articles..."):
                        try:
                            connector = WordPressConnector(
                                st.session_state.wp_base_domain,
                                use_subdirectory=st.session_state.wp_use_subdirectory,
                            )

                            result = connector.get_posts(
                                subdomain=selected_subdomain,
                                per_page=per_page,
                                search=search_term if search_term else "",
                                categories=selected_cat_ids
                                if selected_cat_ids
                                else None,
                                tags=selected_tag_ids if selected_tag_ids else None,
                                after=date_after,
                                before=date_before,
                            )

                            st.session_state.wp_posts = result["posts"]
                            st.session_state.wp_total_pages = result["total_pages"]
                            st.session_state.wp_total_posts = result["total_posts"]

                            st.success(
                                f"✅ {len(result['posts'])} articles chargés (Total: {result['total_posts']})"
                            )
                        except Exception as e:
                            st.error(f"Erreur lors du chargement: {str(e)}")

                # Affichage et sélection des articles
                if "wp_posts" in st.session_state and st.session_state.wp_posts:
                    st.write(
                        f"**{st.session_state.wp_total_posts} articles disponibles**"
                    )

                    # Initialiser la liste de sélection si elle n'existe pas
                    if "wp_selected_post_ids" not in st.session_state:
                        st.session_state.wp_selected_post_ids = []

                    # Afficher chaque article avec case à cocher
                    for post in st.session_state.wp_posts:
                        with st.container():
                            col1, col2 = st.columns([1, 20])

                            with col1:
                                is_selected = st.checkbox(
                                    "",
                                    value=post["id"]
                                    in st.session_state.wp_selected_post_ids,
                                    key=f"post_check_{post['id']}",
                                )
                                if (
                                    is_selected
                                    and post["id"]
                                    not in st.session_state.wp_selected_post_ids
                                ):
                                    st.session_state.wp_selected_post_ids.append(
                                        post["id"]
                                    )
                                elif (
                                    not is_selected
                                    and post["id"]
                                    in st.session_state.wp_selected_post_ids
                                ):
                                    st.session_state.wp_selected_post_ids.remove(
                                        post["id"]
                                    )

                            with col2:
                                st.markdown(f"**{post['title']}**")
                                st.caption(
                                    f"📅 {post['date'][:10]} | ✍️ {post['author']} | 🏷️ {', '.join(post['categories']) if post['categories'] else 'Sans catégorie'}"
                                )

                                # Afficher un extrait
                                excerpt = connector.strip_html_tags(post["excerpt"])[
                                    :200
                                ]
                                if len(excerpt) >= 200:
                                    excerpt += "..."
                                st.text(excerpt)

                                # Lien vers l'article
                                st.markdown(f"[🔗 Voir l'article]({post['link']})")

                            st.divider()

                    # Bouton d'import des articles sélectionnés
                    if st.session_state.wp_selected_post_ids:
                        st.subheader("4️⃣ Extraction et Import")
                        st.info(
                            f"**{len(st.session_state.wp_selected_post_ids)} article(s) sélectionné(s)**"
                        )

                        if st.button(
                            "🤖 Lancer l'extraction LLM et sauvegarder", type="primary"
                        ):
                            # Déterminer le prompt système à utiliser
                            prompt_id = (
                                st.session_state.user_data.get("selected_prompt_id")
                                if st.session_state.user_data
                                else None
                            )
                            if not prompt_id:
                                prompt_id = prompt_manager.get_default_prompt_id()

                            system_prompt_to_use = prompt_manager.get_prompt_by_id(
                                prompt_id
                            )
                            if not system_prompt_to_use:
                                # Fallback sur le fichier par défaut
                                with open(
                                    SYSTEM_PROMPT_FILE, "r", encoding="utf-8"
                                ) as f:
                                    system_prompt_to_use = f.read()

                            progress_bar = st.progress(0)
                            status_text = st.empty()

                            success_count = 0
                            error_count = 0
                            total = len(st.session_state.wp_selected_post_ids)

                            for idx, post_id in enumerate(
                                st.session_state.wp_selected_post_ids
                            ):
                                # Trouver le post correspondant
                                post = next(
                                    (
                                        p
                                        for p in st.session_state.wp_posts
                                        if p["id"] == post_id
                                    ),
                                    None,
                                )
                                if not post:
                                    continue

                                status_text.text(
                                    f"Traitement de '{post['title'][:50]}...' ({idx + 1}/{total})"
                                )

                                try:
                                    # Extraire le contenu texte
                                    article_text = connector.strip_html_tags(
                                        post["content"]
                                    )

                                    # Ajouter l'URL WordPress au texte pour que le LLM puisse l'extraire
                                    article_text_with_url = (
                                        f"{article_text}\n\nSource: {post['link']}"
                                    )

                                    # Extraction LLM
                                    extracted_data = extract_data_from_llm(
                                        article_text_with_url, system_prompt_to_use
                                    )

                                    if extracted_data:
                                        # Calculer le hash
                                        content_hash = database.calculate_content_hash(
                                            article_text
                                        )

                                        # Sauvegarder avec l'URL de l'article WordPress
                                        success, message = database.add_extraction(
                                            user_id=st.session_state.user_id,
                                            original_content=article_text,
                                            extracted_data=json.dumps(extracted_data),
                                            content_hash=content_hash,
                                            source_url=post["link"],
                                        )

                                        if success:
                                            success_count += 1
                                        else:
                                            error_count += 1
                                    else:
                                        error_count += 1

                                except Exception as e:
                                    st.warning(
                                        f"Erreur pour '{post['title']}': {str(e)}"
                                    )
                                    error_count += 1

                                # Mettre à jour la barre de progression
                                progress_bar.progress((idx + 1) / total)

                            status_text.empty()
                            progress_bar.empty()

                            # Afficher le résumé
                            if success_count > 0:
                                st.success(
                                    f"✅ {success_count} article(s) extrait(s) et sauvegardé(s) avec succès!"
                                )
                            if error_count > 0:
                                st.warning(f"⚠️ {error_count} article(s) ont échoué.")

                            # Réinitialiser la sélection
                            st.session_state.wp_selected_post_ids = []
                            st.rerun()

    elif st.session_state.selected_action == "export_wp":
        # --- Interface Export WordPress ---
        if st.button("← Retour au menu", type="secondary"):
            st.session_state.selected_action = None
            st.rerun()
        st.header("📤 Exporter les données extraites vers WordPress")
        st.info("🚧 **Fonctionnalité en développement**")

        st.write("Cette fonctionnalité permettra de :")
        st.markdown("""
        ### 🎯 Objectifs
        - ✅ Sélectionner les extractions à exporter
        - ✅ Choisir le site WordPress de destination
        - ✅ Configurer le format d'export
        - ✅ Prévisualiser avant l'export
        - ✅ Rapport de succès détaillé

        ### ⚙️ Options à configurer (selon vos besoins)

        **1. Action sur les données extraites :**
        - Créer de nouveaux articles
        - Enrichir les articles existants
        - Les deux

        **2. Format d'export :**
        - Article texte formaté
        - Tableau HTML
        - Custom fields (ACF)
        - Custom Post Type dédié

        **3. Destination WordPress :**
        - Même multisite que la source
        - Site centralisé différent
        - Choix manuel par export

        **4. Statut des articles :**
        - Brouillon (pour validation manuelle)
        - Publié directement
        - Privé
        - Programmé

        ### 📋 Prochaines étapes
        Contactez-nous pour définir vos besoins spécifiques et activer cette fonctionnalité.
        """)

        # Aperçu des extractions disponibles
        st.subheader("📊 Aperçu de vos extractions")
        extractions = database.get_extractions_by_user(st.session_state.user_id)

        if extractions:
            st.info(
                f"**{len(extractions)} extraction(s)** disponible(s) dans votre historique"
            )

            # Tableau récapitulatif
            export_data = []
            for ext in extractions[:10]:  # Limite à 10 pour l'aperçu
                data = ext["extracted_data"]
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except:
                        data = {}

                export_data.append(
                    {
                        "ID": ext["id"],
                        "Date": ext["created_at"].strftime("%Y-%m-%d"),
                        "Entreprise": data.get("Nom_start-up", "N/A"),
                        "Montant": data.get("Montant", "N/A"),
                    }
                )

            df_export = pd.DataFrame(export_data)
            st.dataframe(df_export, use_container_width=True)

            if len(extractions) > 10:
                st.caption(
                    f"Affichage des 10 premières extractions sur {len(extractions)} disponibles"
                )
        else:
            st.warning(
                "Aucune extraction disponible. Utilisez l'onglet 'Analyse d'Article' ou 'Import WordPress' pour créer des extractions."
            )

    elif st.session_state.selected_action == "export_gsheet":
        # --- Interface Export Google Sheets ---
        if st.button("← Retour au menu", type="secondary"):
            st.session_state.selected_action = None
            st.rerun()

        st.header("📊 Exporter vers Google Sheets")
        st.caption("Exportez vos analyses vers une feuille Google Sheets")
        st.markdown("<br>", unsafe_allow_html=True)

        # Récupérer les extractions
        extractions = database.get_extractions_by_user(st.session_state.user_id)

        if not extractions:
            st.warning(
                "Aucune extraction disponible. Effectuez d'abord des analyses d'articles."
            )
        else:
            # Étape 1: Sélection des extractions
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("1️⃣ Sélectionner les extractions à exporter")
            st.info(
                f"**{len(extractions)} extraction(s)** disponible(s) dans votre historique"
            )

            # Initialiser la liste de sélection
            if "gsheet_selected_ids" not in st.session_state:
                st.session_state.gsheet_selected_ids = []

            # Option pour tout sélectionner
            col_select1, col_select2 = st.columns([1, 3])
            with col_select1:
                select_all = st.checkbox("Tout sélectionner", value=False)
                if select_all:
                    st.session_state.gsheet_selected_ids = [
                        ext["id"] for ext in extractions
                    ]
                elif not select_all and len(
                    st.session_state.gsheet_selected_ids
                ) == len(extractions):
                    st.session_state.gsheet_selected_ids = []

            # Afficher les extractions avec checkboxes
            for ext in extractions[:20]:  # Limite à 20 pour l'affichage
                data = ext["extracted_data"]
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except:
                        data = {}

                col1, col2 = st.columns([1, 20])
                with col1:
                    is_selected = st.checkbox(
                        "",
                        value=ext["id"] in st.session_state.gsheet_selected_ids,
                        key=f"gsheet_check_{ext['id']}",
                    )
                    if (
                        is_selected
                        and ext["id"] not in st.session_state.gsheet_selected_ids
                    ):
                        st.session_state.gsheet_selected_ids.append(ext["id"])
                    elif (
                        not is_selected
                        and ext["id"] in st.session_state.gsheet_selected_ids
                    ):
                        st.session_state.gsheet_selected_ids.remove(ext["id"])

                with col2:
                    st.markdown(
                        f"**{data.get('Nom_start-up', 'N/A')}** - {data.get('Montant', 'N/A')} - {ext['created_at'].strftime('%d/%m/%Y')}"
                    )

            if len(extractions) > 20:
                st.caption(
                    f"Affichage des 20 premières sur {len(extractions)} disponibles"
                )

            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            # Étape 2: Configuration Google Sheets
            if st.session_state.gsheet_selected_ids:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("2️⃣ Configuration Google Sheets")
                st.info(
                    f"**{len(st.session_state.gsheet_selected_ids)} extraction(s)** sélectionnée(s)"
                )

                col1, col2 = st.columns(2)
                with col1:
                    sheet_url = st.text_input(
                        "URL de la feuille Google Sheets",
                        placeholder="https://docs.google.com/spreadsheets/d/...",
                        help="Collez l'URL complète de votre Google Sheet",
                    )

                with col2:
                    worksheet_name = st.text_input(
                        "Nom de l'onglet (optionnel)",
                        value="Extractions",
                        help="Nom de l'onglet où exporter les données",
                    )

                export_mode = st.radio(
                    "Mode d'export",
                    options=[
                        "Ajouter aux données existantes",
                        "Remplacer toutes les données",
                    ],
                    index=0,
                    horizontal=True,
                )

                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

                # Étape 3: Aperçu et Export
                st.subheader("3️⃣ Aperçu et Export")

                if st.button(
                    "🔍 Prévisualiser les données",
                    type="secondary",
                    use_container_width=True,
                ):
                    # Préparer les données pour l'aperçu
                    preview_data = []
                    for ext in extractions:
                        if ext["id"] in st.session_state.gsheet_selected_ids:
                            data = ext["extracted_data"]
                            if isinstance(data, str):
                                try:
                                    data = json.loads(data)
                                except:
                                    data = {}

                            # Récupérer la liste des investisseurs
                            investisseurs_list = data.get("Investisseurs", [])
                            if isinstance(investisseurs_list, list):
                                investisseurs_str = (
                                    ", ".join(investisseurs_list)
                                    if investisseurs_list
                                    else ""
                                )
                            else:
                                investisseurs_str = (
                                    str(investisseurs_list)
                                    if investisseurs_list
                                    else ""
                                )

                            preview_data.append(
                                {
                                    "Nom_start-up": data.get("Nom_start-up", ""),
                                    "Type": data.get("Type", ""),
                                    "Montant": data.get("Montant", ""),
                                    "Date_levée": data.get("Date_levée", ""),
                                    "Tour": data.get("Tour", ""),
                                    "Investisseurs": investisseurs_str,
                                    "Lien": data.get("Lien")
                                    or ext.get("source_url", ""),
                                }
                            )

                    df_preview = pd.DataFrame(preview_data)
                    st.dataframe(df_preview, use_container_width=True)

                st.markdown("<br>", unsafe_allow_html=True)

                if st.button(
                    "🚀 Exporter vers Google Sheets",
                    type="primary",
                    use_container_width=True,
                ):
                    if not sheet_url:
                        st.error("Veuillez fournir l'URL de la feuille Google Sheets")
                    else:
                        with st.spinner("Export en cours vers Google Sheets..."):
                            try:
                                import gspread
                                from oauth2client.service_account import (
                                    ServiceAccountCredentials,
                                )

                                # Configuration des credentials
                                scope = [
                                    "https://spreadsheets.google.com/feeds",
                                    "https://www.googleapis.com/auth/drive",
                                ]

                                # Utiliser Streamlit Secrets en production, sinon le fichier local
                                if "gcp_service_account" in st.secrets:
                                    # Utiliser les secrets Streamlit Cloud
                                    creds = ServiceAccountCredentials.from_json_keyfile_dict(
                                        st.secrets["gcp_service_account"], scope
                                    )
                                else:
                                    # En local, utiliser le fichier credentials.json
                                    creds_file = os.path.join(
                                        os.path.dirname(os.path.abspath(__file__)),
                                        "credentials.json",
                                    )
                                    if not os.path.exists(creds_file):
                                        st.error(
                                            "Le fichier credentials.json est introuvable. Assurez-vous qu'il est dans le répertoire du projet ou configurez les secrets Streamlit."
                                        )
                                    else:
                                        creds = ServiceAccountCredentials.from_json_keyfile_name(
                                            creds_file, scope
                                        )

                                if "creds" in locals():
                                    client = gspread.authorize(creds)

                                    # Ouvrir la feuille
                                    try:
                                        # Extraire l'ID du sheet depuis l'URL
                                        if "/d/" in sheet_url:
                                            sheet_id = sheet_url.split("/d/")[1].split(
                                                "/"
                                            )[0]
                                            spreadsheet = client.open_by_key(sheet_id)
                                        else:
                                            st.error(
                                                "URL de feuille Google Sheets invalide"
                                            )
                                            raise ValueError("Invalid URL")

                                        # Sélectionner ou créer l'onglet
                                        try:
                                            worksheet = spreadsheet.worksheet(
                                                worksheet_name
                                            )
                                        except:
                                            worksheet = spreadsheet.add_worksheet(
                                                title=worksheet_name,
                                                rows="1000",
                                                cols="20",
                                            )

                                        # Préparer les données
                                        export_data = []
                                        headers = [
                                            "Nom_start-up",
                                            "Type",
                                            "Montant",
                                            "Date_levée",
                                            "Jour",
                                            "Mois",
                                            "Année",
                                            "Tour",
                                            "Investisseurs",
                                            "Lien",
                                        ]

                                        for ext in extractions:
                                            if (
                                                ext["id"]
                                                in st.session_state.gsheet_selected_ids
                                            ):
                                                data = ext["extracted_data"]
                                                if isinstance(data, str):
                                                    try:
                                                        data = json.loads(data)
                                                    except:
                                                        data = {}

                                                # Extraire date et ses composants
                                                date_levee = data.get("Date_levée", "")
                                                jour, mois, annee = "", "", ""
                                                if date_levee and "/" in date_levee:
                                                    parts = date_levee.split("/")
                                                    if len(parts) == 3:
                                                        jour, mois, annee = (
                                                            parts[0],
                                                            parts[1],
                                                            parts[2],
                                                        )

                                                # Récupérer les investisseurs
                                                investisseurs_list = data.get(
                                                    "Investisseurs", []
                                                )
                                                if isinstance(investisseurs_list, list):
                                                    investisseurs_str = (
                                                        ", ".join(investisseurs_list)
                                                        if investisseurs_list
                                                        else ""
                                                    )
                                                else:
                                                    investisseurs_str = (
                                                        str(investisseurs_list)
                                                        if investisseurs_list
                                                        else ""
                                                    )

                                                row = [
                                                    data.get("Nom_start-up", ""),
                                                    data.get("Type", ""),
                                                    data.get("Montant", ""),
                                                    date_levee,
                                                    jour,
                                                    mois,
                                                    annee,
                                                    data.get("Tour", ""),
                                                    investisseurs_str,
                                                    data.get("Lien")
                                                    or ext.get("source_url", ""),
                                                ]

                                                export_data.append(row)

                                        # Exporter selon le mode
                                        if (
                                            export_mode
                                            == "Remplacer toutes les données"
                                        ):
                                            worksheet.clear()
                                            worksheet.update([headers] + export_data)
                                        else:
                                            # Ajouter les headers si la feuille est vide
                                            if (
                                                worksheet.row_count == 0
                                                or not worksheet.row_values(1)
                                            ):
                                                worksheet.update(
                                                    [headers] + export_data
                                                )
                                            else:
                                                # Ajouter à la suite
                                                worksheet.append_rows(export_data)

                                        # Rapport de succès
                                        st.success(
                                            "✅ Export réussi vers Google Sheets!"
                                        )
                                        st.balloons()

                                        st.markdown("### 📋 Rapport d'export")
                                        col_report1, col_report2, col_report3 = (
                                            st.columns(3)
                                        )
                                        with col_report1:
                                            st.metric(
                                                "Extractions exportées",
                                                len(export_data),
                                            )
                                        with col_report2:
                                            st.metric("Colonnes", len(headers))
                                        with col_report3:
                                            st.metric(
                                                "Mode",
                                                "Ajout"
                                                if export_mode
                                                == "Ajouter aux données existantes"
                                                else "Remplacement",
                                            )

                                        st.info(
                                            f"🔗 [Ouvrir la feuille Google Sheets]({sheet_url})"
                                        )

                                        # Réinitialiser la sélection
                                        st.session_state.gsheet_selected_ids = []

                                    except Exception as e:
                                        st.error(
                                            f"Erreur lors de l'accès à la feuille: {str(e)}"
                                        )
                                        st.info(
                                            "Assurez-vous que le compte de service a accès à cette feuille (partager avec l'email du service account)"
                                        )

                            except ImportError:
                                st.error(
                                    "Les bibliothèques gspread et oauth2client ne sont pas installées."
                                )
                                st.code(
                                    "pip install gspread oauth2client", language="bash"
                                )
                            except Exception as e:
                                st.error(f"Erreur lors de l'export: {str(e)}")

    elif st.session_state.show_dashboard:
        # --- Page Dashboard avec Statistiques ---
        if st.button("← Retour au menu", type="secondary"):
            st.session_state.show_dashboard = False
            st.rerun()

        st.header("📊 Dashboard")
        st.caption("Vue d'ensemble de votre activité")
        st.markdown("<br>", unsafe_allow_html=True)

        extractions = database.get_extractions_by_user(st.session_state.user_id)

        # Statistiques principales
        col_stat1, col_stat2, col_stat3 = st.columns(3)

        with col_stat1:
            st.markdown(
                """
            <div class="metric-card" style="padding: 2rem;">
                <h4 style="color: #6B7280; margin-bottom: 1rem; font-size: 0.9rem; text-transform: uppercase;">Total analyses</h4>
                <h1 style="color: #7C3AED; margin: 0; font-size: 3rem;">"""
                + str(len(extractions))
                + """</h1>
                <p style="color: #9CA3AF; margin-top: 0.5rem; font-size: 0.85rem;">Analyses effectuées</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col_stat2:
            last_extraction = extractions[0] if extractions else None
            if last_extraction:
                last_date = last_extraction["created_at"].strftime("%d/%m/%Y")
                st.markdown(
                    """
                <div class="metric-card" style="padding: 2rem;">
                    <h4 style="color: #6B7280; margin-bottom: 1rem; font-size: 0.9rem; text-transform: uppercase;">Dernière analyse</h4>
                    <h2 style="color: #3B82F6; margin: 0; font-size: 2rem;">"""
                    + last_date
                    + """</h2>
                    <p style="color: #9CA3AF; margin-top: 0.5rem; font-size: 0.85rem;">Date de la dernière extraction</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    """
                <div class="metric-card" style="padding: 2rem;">
                    <h4 style="color: #6B7280; margin-bottom: 1rem; font-size: 0.9rem; text-transform: uppercase;">Dernière analyse</h4>
                    <h2 style="color: #9CA3AF; margin: 0; font-size: 2rem;">N/A</h2>
                    <p style="color: #9CA3AF; margin-top: 0.5rem; font-size: 0.85rem;">Aucune analyse effectuée</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )

        with col_stat3:
            status_text = "✓ Actif" if extractions else "○ En attente"
            status_color = "#10B981" if extractions else "#F59E0B"
            st.markdown(
                """
            <div class="metric-card" style="padding: 2rem;">
                <h4 style="color: #6B7280; margin-bottom: 1rem; font-size: 0.9rem; text-transform: uppercase;">Statut</h4>
                <h2 style="color: """
                + status_color
                + """; margin: 0; font-size: 2rem;">"""
                + status_text
                + """</h2>
                <p style="color: #9CA3AF; margin-top: 0.5rem; font-size: 0.85rem;">État du compte</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        st.markdown("<br><br>", unsafe_allow_html=True)

        # Graphique d'activité récente
        if extractions and len(extractions) > 0:
            st.subheader("📈 Activité récente")

            # Créer un DataFrame pour les analyses des 30 derniers jours
            from datetime import timedelta

            thirty_days_ago = datetime.now() - timedelta(days=30)

            recent_extractions = []
            for ext in extractions:
                val = ext.get("created_at")
                if val:
                    # 1. Si c'est déjà un objet datetime
                    if isinstance(val, datetime):
                        # Si l'un a un fuseau horaire (tz) et pas l'autre, on les aligne
                        val_naive = val.replace(tzinfo=None)
                        thirty_days_naive = thirty_days_ago.replace(tzinfo=None)
            
                        if val_naive >= thirty_days_naive:
                            recent_extractions.append(ext)
                
                    # 2. Si c'est du texte (str), on le convertit d'abord
                    elif isinstance(val, str):
                        try:
                            # Adaptez le format "%Y-%m-%d" selon la forme de votre texte (ex: 2026-07-09)
                            val_date = datetime.strptime(val[:10], "%Y-%m-%d")
                            if val_date >= thirty_days_ago.replace(tzinfo=None):
                                recent_extractions.append(ext)
                        except ValueError:
                            pass # Format de texte invalide, on ignore

            if recent_extractions:
                # Compter par jour
                dates_count = {}
                for ext in recent_extractions:
                    date_key = ext["created_at"].strftime("%Y-%m-%d")
                    dates_count[date_key] = dates_count.get(date_key, 0) + 1

                chart_df = pd.DataFrame(
                    list(dates_count.items()), columns=["Date", "Analyses"]
                )
                chart_df = chart_df.sort_values("Date")

                st.line_chart(chart_df.set_index("Date"))
                st.caption(
                    f"📊 {len(recent_extractions)} analyses effectuées ces 30 derniers jours"
                )
            else:
                st.info("Aucune analyse récente dans les 30 derniers jours")

    else:
        # --- Menu Principal avec Cartes Cliquables ---
        st.subheader("Que souhaitez-vous faire ?")
        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown('<div class="card-button">', unsafe_allow_html=True)
            if st.button(
                "✍️\n\nAnalyser un article\n\nCollez le texte d'un article pour extraire automatiquement les informations clés via l'IA",
                key="btn_analyse",
                use_container_width=True,
                help="Cliquez pour analyser un article",
            ):
                st.session_state.selected_action = "analyse"
                st.session_state.show_dashboard = False
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="card-button">', unsafe_allow_html=True)
            if st.button(
                "🌐\n\nImport WordPress\n\nImportez des articles depuis votre WordPress multisite et analysez-les en masse",
                key="btn_import",
                use_container_width=True,
                help="Cliquez pour importer depuis WordPress",
            ):
                st.session_state.selected_action = "import_wp"
                st.session_state.show_dashboard = False
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with col3:
            st.markdown('<div class="card-button">', unsafe_allow_html=True)
            if st.button(
                "📊\n\nExport Google Sheets\n\nExportez vos données extraites vers Google Sheets",
                key="btn_export_gsheet",
                use_container_width=True,
                help="Cliquez pour exporter vers Google Sheets",
            ):
                st.session_state.selected_action = "export_gsheet"
                st.session_state.show_dashboard = False
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with col4:
            st.markdown('<div class="card-button">', unsafe_allow_html=True)
            if st.button(
                "📤\n\nExport WordPress\n\nExportez vos données extraites vers votre site WordPress",
                key="btn_export",
                use_container_width=True,
                help="Cliquez pour exporter vers WordPress",
            ):
                st.session_state.selected_action = "export_wp"
                st.session_state.show_dashboard = False
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # --- Sélecteur de Prompt dans la Barre Latérale ---
    st.sidebar.title("Configuration")
    with st.sidebar.expander("📝 Modèle d'extraction", expanded=False):
        st.markdown("**Choisissez le type d'analyse :**")

        # Récupérer les prompts disponibles
        available_prompts = prompt_manager.get_available_prompts()

        # Déterminer le prompt actuellement sélectionné
        current_prompt_id = (
            st.session_state.user_data.get("selected_prompt_id")
            if st.session_state.user_data
            else None
        )
        if not current_prompt_id:
            current_prompt_id = prompt_manager.get_default_prompt_id()

        # Créer les options pour le selectbox
        prompt_options = {
            f"{p['icon']} {p['name']}": p["id"] for p in available_prompts
        }

        # Trouver l'index actuel
        current_index = 0
        for idx, (label, pid) in enumerate(prompt_options.items()):
            if pid == current_prompt_id:
                current_index = idx
                break

        # Afficher le sélecteur
        selected_label = st.selectbox(
            "Type d'extraction",
            options=list(prompt_options.keys()),
            index=current_index,
            label_visibility="collapsed",
        )

        selected_prompt_id = prompt_options[selected_label]

        # Afficher la description du prompt sélectionné
        prompt_info = prompt_manager.get_prompt_info(selected_prompt_id)
        if prompt_info:
            st.caption(prompt_info["description"])

        # Sauvegarder si changement
        if selected_prompt_id != current_prompt_id:
            if st.button("✅ Appliquer ce modèle", use_container_width=True):
                success, message = database.update_user_prompt(
                    st.session_state.user_id, selected_prompt_id
                )
                if success:
                    st.session_state.user_data["selected_prompt_id"] = (
                        selected_prompt_id
                    )
                    st.success(f"Modèle changé : {prompt_info['name']}")
                    st.rerun()
                else:
                    st.error(f"Erreur : {message}")
