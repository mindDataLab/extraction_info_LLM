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
from run_extraction import SYSTEM_PROMPT_FILE, extract_data_from_llm
from wordpress_connector import WordPressConnector

# --- Configuration de la Page ---
st.set_page_config(page_title="Analyseur d'Articles", layout="wide")

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
        with st.form("login_form"):
            username = st.text_input("Nom d'utilisateur", key="login_user")
            password = st.text_input("Mot de passe", type="password", key="login_pass")
            submitted = st.form_submit_button("Se connecter")
            if submitted:
                user = database.get_user(username)
                if user and database.check_password(password, user["password_hash"]):
                    st.session_state.logged_in = True
                    st.session_state.username = user["username"]
                    st.session_state.user_id = user["id"]
                    st.session_state.user_data = (
                        user  # Stocker toutes les données de l'utilisateur
                    )
                    st.rerun()
                else:
                    st.error("Nom d'utilisateur ou mot de passe incorrect.")

    # Formulaire de Création de Compte
    with auth_tab2:
        with st.form("signup_form"):
            new_username = st.text_input("Nom d'utilisateur", key="signup_user")
            new_password = st.text_input(
                "Mot de passe", type="password", key="signup_pass"
            )
            confirm_password = st.text_input(
                "Confirmer le mot de passe", type="password", key="signup_confirm"
            )
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
                        st.info(
                            "Vous pouvez maintenant vous connecter avec votre nouveau compte."
                        )
                    else:
                        st.error(message)


# --- Application Principale ---

# Si l'utilisateur n'est pas connecté, afficher l'interface d'authentification
if not st.session_state.logged_in:
    st.warning(
        "Veuillez vous connecter ou créer un compte pour utiliser l'application."
    )
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

    main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs(
        [
            "✍️ Analyse d'Article",
            "📚 Mon Historique",
            "🌐 Import WordPress",
            "📤 Export vers WordPress",
        ]
    )

    # --- Onglet d'Analyse ---
    with main_tab1:
        st.header("Extraire les informations d'un article")
        st.write(
            "Collez le texte d'un article ci-dessous pour extraire les informations clés."
        )

        article_text = st.text_area(
            "Texte de l'article",
            height=300,
            placeholder="Collez ici le texte complet de l'article...",
        )

        source_url = st.text_input(
            "URL source (optionnel)",
            placeholder="https://exemple.com/article...",
            help="URL de la page d'où provient l'article",
        )

        if st.button("Lancer l'analyse", type="primary"):
            if article_text.strip():
                with st.spinner("Analyse en cours... Le LLM réfléchit..."):
                    try:
                        # Déterminer le prompt système à utiliser
                        if (
                            st.session_state.user_data
                            and st.session_state.user_data["custom_system_prompt"]
                        ):
                            system_prompt_to_use = st.session_state.user_data[
                                "custom_system_prompt"
                            ]
                        else:
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
                                        source_url=source_url
                                        if source_url.strip()
                                        else None,
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
            else:
                st.warning(
                    "Veuillez coller le texte d'un article avant de lancer l'analyse."
                )

    # --- Onglet Historique ---
    with main_tab2:
        st.header("Historique de vos analyses")
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

                # Récupérer les investisseurs (Investisseur 1 à 13) - colonnes séparées
                investisseurs_dict = {}
                for i in range(1, 14):
                    inv = data.get(f"Investisseur {i}", "")
                    investisseurs_dict[f"Inv{i}"] = inv if inv and inv.strip() else ""

                history_data.append(
                    {
                        "ID": ext["id"],
                        "ID_levée": data.get("ID_levée", "N/A"),
                        "Date": ext["created_at"].strftime("%Y-%m-%d %H:%M"),
                        "Nom": data.get("Nom_start-up", "N/A"),
                        "Secteur": data.get("Secteur_start-up", "N/A"),
                        "Type": data.get("Type", "N/A"),
                        "Montant": data.get("Montant", "N/A"),
                        "Jour": data.get("Jour", "N/A"),
                        "Mois": data.get("Mois", "N/A"),
                        "Année": data.get("Année", "N/A"),
                        "Concat": data.get("Concat", "N/A"),
                        "Tour": data.get("Tour", "N/A"),
                        "URL_source": ext.get("source_url", "N/A"),
                        **investisseurs_dict,  # Ajoute Inv1, Inv2, ... Inv13
                        "data_json": json.dumps(data, indent=2, ensure_ascii=False),
                    }
                )

            df = pd.DataFrame(history_data)

            # Colonnes à afficher (toutes sauf data_json)
            display_columns = [col for col in df.columns if col != "data_json"]

            st.dataframe(
                df[display_columns],
                use_container_width=True,
                height=600,
            )

            # Option de téléchargement CSV
            csv = df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 Télécharger tout l'historique en CSV",
                data=csv,
                file_name=f"historique_extractions_{st.session_state.username}.csv",
                mime="text/csv",
            )

            st.subheader("Télécharger les extractions")
            for index, row in df.iterrows():
                st.download_button(
                    label=f"📥 Télécharger JSON pour ID {row['ID']}",
                    data=row["data_json"],
                    file_name=f"extraction_{row['ID']}.json",
                    mime="application/json",
                    key=f"download_{row['ID']}",
                )

    # --- Onglet Import WordPress ---
    with main_tab3:
        st.header("Importer des Articles depuis WordPress Multisite")
        st.write(
            "Connectez-vous à votre WordPress multisite et importez des articles par verticale."
        )

        # Configuration WordPress
        st.subheader("1️⃣ Configuration WordPress")

        # Type de multisite
        multisite_type = st.radio(
            "Type de multisite WordPress",
            options=["Sous-domaines", "Sous-répertoires"],
            index=1,  # Par défaut sur sous-répertoires
            horizontal=True,
            help="Sous-domaines: tech.example.com | Sous-répertoires: example.com/tech",
        )
        use_subdirectory = multisite_type == "Sous-répertoires"

        # Sauvegarder dans session state
        if "wp_use_subdirectory" not in st.session_state:
            st.session_state.wp_use_subdirectory = use_subdirectory
        else:
            st.session_state.wp_use_subdirectory = use_subdirectory

        col1, col2 = st.columns(2)
        with col1:
            if use_subdirectory:
                placeholder_domain = "mind.eu.com"
                help_text = "Ex: mind.eu.com pour des sites comme mind.eu.com/media"
            else:
                placeholder_domain = "example.com"
                help_text = "Ex: example.com pour des sites comme tech.example.com"

            base_domain = st.text_input(
                "Domaine de base (sans http/https)",
                value=st.session_state.wp_base_domain,
                placeholder=placeholder_domain,
                help=help_text,
            )
            if base_domain != st.session_state.wp_base_domain:
                st.session_state.wp_base_domain = base_domain

        with col2:
            if use_subdirectory:
                placeholder_sites = "media\nfinance\ntech"
                help_text = (
                    "Listez vos sites, un par ligne (ex: media pour mind.eu.com/media)"
                )
            else:
                placeholder_sites = "tech\nfinance\nhealth"
                help_text = "Listez vos sous-domaines, un par ligne (ex: tech pour tech.example.com)"

            subdomains_input = st.text_area(
                "Sites / Verticales (un par ligne)",
                value="\n".join(st.session_state.wp_subdomains),
                placeholder=placeholder_sites,
                height=100,
                help=help_text,
            )
            subdomains_list = [
                s.strip() for s in subdomains_input.split("\n") if s.strip()
            ]
            if subdomains_list != st.session_state.wp_subdomains:
                st.session_state.wp_subdomains = subdomains_list

        # Sélection du sous-domaine
        if st.session_state.wp_base_domain and st.session_state.wp_subdomains:
            st.subheader("2️⃣ Sélection de la Verticale")

            selected_subdomain = st.selectbox(
                "Choisissez une verticale",
                options=st.session_state.wp_subdomains,
                key="subdomain_selector",
            )

            # Test de connexion
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("🔍 Tester la connexion"):
                    if st.session_state.wp_use_subdirectory:
                        site_format = (
                            f"{st.session_state.wp_base_domain}/{selected_subdomain}"
                        )
                    else:
                        site_format = (
                            f"{selected_subdomain}.{st.session_state.wp_base_domain}"
                        )

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

            # Chargement des articles
            if st.session_state.wp_selected_subdomain == selected_subdomain:
                st.subheader("3️⃣ Sélection des Articles")

                # Filtres
                with st.expander("🎛️ Filtres", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        search_term = st.text_input(
                            "Rechercher", placeholder="Mot-clé..."
                        )
                        per_page = st.slider("Articles par page", 5, 50, 20)

                    with col2:
                        # Filtre par date
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
                            index=0,
                        )

                        date_after = None
                        date_before = None

                        if date_filter != "Tous":
                            today = datetime.now()

                            if date_filter == "Dernière semaine":
                                date_after = (today - timedelta(days=7)).isoformat()
                            elif date_filter == "Dernier mois":
                                date_after = (today - timedelta(days=30)).isoformat()
                            elif date_filter == "3 derniers mois":
                                date_after = (today - timedelta(days=90)).isoformat()
                            elif date_filter == "6 derniers mois":
                                date_after = (today - timedelta(days=180)).isoformat()
                            elif date_filter == "Dernière année":
                                date_after = (today - timedelta(days=365)).isoformat()
                            elif date_filter == "Personnalisé":
                                col_date1, col_date2 = st.columns(2)
                                with col_date1:
                                    date_from = st.date_input(
                                        "Du", value=today - timedelta(days=30)
                                    )
                                    date_after = datetime.combine(
                                        date_from, datetime.min.time()
                                    ).isoformat()
                                with col_date2:
                                    date_to = st.date_input("Au", value=today)
                                    date_before = datetime.combine(
                                        date_to, datetime.max.time()
                                    ).isoformat()

                    with col3:
                        # Récupérer les catégories disponibles
                        try:
                            connector = WordPressConnector(
                                st.session_state.wp_base_domain,
                                use_subdirectory=st.session_state.wp_use_subdirectory,
                            )

                            categories = connector.get_categories(selected_subdomain)
                            cat_options = {cat["name"]: cat["id"] for cat in categories}
                            selected_cats = st.multiselect(
                                "Catégories", options=list(cat_options.keys())
                            )
                            selected_cat_ids = [
                                cat_options[cat] for cat in selected_cats
                            ]
                        except:
                            selected_cat_ids = []

                # Bouton pour charger les articles
                if st.button("📥 Charger les articles", type="primary"):
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
                            if (
                                st.session_state.user_data
                                and st.session_state.user_data["custom_system_prompt"]
                            ):
                                system_prompt_to_use = st.session_state.user_data[
                                    "custom_system_prompt"
                                ]
                            else:
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

                                    # Extraction LLM
                                    extracted_data = extract_data_from_llm(
                                        article_text, system_prompt_to_use
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

    # --- Onglet Export vers WordPress ---
    with main_tab4:
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

    # --- Éditeur de Prompt dans la Barre Latérale ---
    st.sidebar.title("Configuration")
    with st.sidebar.expander("Éditer le prompt système", expanded=False):
        # Déterminer la valeur initiale de l'éditeur de prompt
        if (
            st.session_state.user_data
            and st.session_state.user_data["custom_system_prompt"]
        ):
            initial_prompt_value = st.session_state.user_data["custom_system_prompt"]
            st.info("Vous utilisez un prompt personnalisé.")
        else:
            with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
                initial_prompt_value = f.read()
            st.info("Vous utilisez le prompt système par défaut.")

        prompt_area = st.text_area(
            "Prompt Système:",
            value=initial_prompt_value,
            height=400,
            key="prompt_editor",
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Sauvegarder le Prompt Personnalisé"):
                success, message = database.update_user_prompt(
                    st.session_state.user_id, prompt_area
                )
                if success:
                    st.session_state.user_data["custom_system_prompt"] = (
                        prompt_area  # Mettre à jour l'état de la session
                    )
                    st.success("Prompt personnalisé sauvegardé !")
                    st.rerun()
                else:
                    st.error(f"Erreur lors de la sauvegarde du prompt : {message}")
        with col2:
            if st.button("Réinitialiser au Prompt par Défaut"):
                success, message = database.update_user_prompt(
                    st.session_state.user_id, None
                )  # Mettre à NULL
                if success:
                    st.session_state.user_data["custom_system_prompt"] = (
                        None  # Mettre à jour l'état de la session
                    )
                    st.success("Prompt réinitialisé au prompt par défaut !")
                    st.rerun()
                else:
                    st.error(
                        f"Erreur lors de la réinitialisation du prompt : {message}"
                    )
