# Projet d'Extraction LLM vers PostgreSQL (Multi-utilisateurs)

Ce projet utilise un LLM local pour extraire des informations structurées depuis des articles et les enregistrer dans une base de données PostgreSQL. Il offre une interface web conviviale avec gestion des utilisateurs et un historique personnalisé, ainsi qu'une option en ligne de commande pour le traitement par lots.

## Structure des Fichiers

```
.
├── app.py                # L'application web interactive (Streamlit) avec gestion des utilisateurs.
├── run_extraction.py     # Le script pour le traitement par lots en ligne de commande.
├── database.py           # Module de gestion de la base de données PostgreSQL (connexion, utilisateurs, extractions).
├── system_prompt.txt     # Fichier contenant les instructions (prompt) pour le LLM.
├── a_traiter/            # DOSSIER : Placez vos fichiers .txt pour le traitement par lots.
├── traites/              # DOSSIER : Les fichiers traités sont déplacés ici.
├── .streamlit/           # DOSSIER : Contient le fichier secrets.toml pour les identifiants de la BDD.
│   └── secrets.toml      # Fichier de configuration sécurisé pour les identifiants PostgreSQL.
└── venv/                 # L'environnement virtuel Python.
```

## ⚙️ Configuration

Suivez ces étapes pour configurer le projet.

### Étape 1 : Installation et Configuration de PostgreSQL

1.  **Installer PostgreSQL** :
    *   **macOS (avec Homebrew)** : Ouvrez votre terminal et exécutez `brew install postgresql`.
    *   **Autres OS** : Suivez les instructions officielles pour votre système d'exploitation.

2.  **Démarrer le service PostgreSQL** :
    *   **macOS (avec Homebrew)** : `brew services start postgresql`.
    *   Assurez-vous que le service PostgreSQL est en cours d'exécution.

3.  **Créer la base de données** :
    *   Créez une base de données dédiée pour le projet. Par exemple : `createdb sprint_ai_db`.

4.  **Configurer les identifiants dans `secrets.toml`** :
    *   Créez un dossier `.streamlit` à la racine de votre projet.
    *   À l'intérieur de ce dossier, créez un fichier nommé `secrets.toml`.
    *   Ajoutez-y vos informations de connexion PostgreSQL. Exemple pour une installation locale par défaut sur macOS :

    ```toml
    # .streamlit/secrets.toml

    [postgres]
    host = "localhost"
    port = 5432
    dbname = "sprint_ai_db"
    user = "VOTRE_NOM_UTILISATEUR_SYSTEME" # Remplacez par votre nom d'utilisateur macOS
    password = "" # Laissez vide si vous n'avez pas défini de mot de passe
    ```
    *   **Important** : Remplacez `VOTRE_NOM_UTILISATEUR_SYSTEME` par votre véritable nom d'utilisateur système.

### Étape 2 : Installation des Dépendances Python

1.  Ouvrez un terminal à la racine du projet.
2.  Créez et activez un environnement virtuel (si ce n'est pas déjà fait) :
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  Installez toutes les bibliothèques nécessaires :
    ```bash
    pip install streamlit requests pandas psycopg2-binary bcrypt
    ```

## 🚀 Utilisation

Vous avez deux façons d'utiliser cet outil.

### Option 1 : Interface Web (Recommandé)

C'est la méthode la plus simple et la plus interactive, avec gestion des utilisateurs et historique.

1.  **Lancez votre serveur LLM** (avec LM Studio, par exemple).
2.  Assurez-vous que votre environnement virtuel est activé (`source venv/bin/activate`).
3.  Lancez l'application Streamlit :
    ```bash
    streamlit run app.py
    ```
4.  Ouvrez l'URL locale affichée dans votre terminal (généralement `http://localhost:8501`) dans votre navigateur.
5.  **Connectez-vous** ou **créez un compte**.
6.  Dans l'onglet "Analyse d'Article", collez le texte et lancez l'extraction. Les résultats seront sauvegardés dans votre historique personnel.
7.  Consultez vos extractions passées dans l'onglet "Mon Historique" et téléchargez-les au format JSON.

### Option 2 : Ligne de Commande (Traitement par Lots)

Utilisez cette méthode pour traiter plusieurs fichiers d'un coup et les associer à un utilisateur existant.

1.  Placez un ou plusieurs fichiers `.txt` dans le dossier `a_traiter`.
2.  Lancez votre serveur LLM.
3.  Depuis votre terminal (avec l'environnement activé), exécutez le script en spécifiant un nom d'utilisateur existant (créé via l'interface web) :
    ```bash
    python3 run_extraction.py --user VOTRE_NOM_UTILISATEUR
    ```
    *   **Important** : L'utilisateur spécifié doit exister dans la base de données.

## 🧠 Fonctionnalités

*   **Gestion des Utilisateurs** : Chaque utilisateur a son propre compte et son historique d'extractions.
*   **Historique Personnalisé** : Accédez et téléchargez vos extractions passées directement depuis l'interface web.
*   **Auto-réparation du JSON** : Le script intègre un mécanisme de résilience : si le LLM renvoie un JSON malformé, il lui demande automatiquement de corriger sa propre erreur, réduisant ainsi les échecs d'analyse.
*   **Prompts Personnalisables** : Chaque utilisateur peut définir et sauvegarder son propre prompt système pour adapter l'extraction à ses besoins spécifiques.

## 🎨 Personnalisation

*   **Comportement de l'IA** : Le moyen le plus simple d'affiner l'extraction est de modifier le prompt système directement depuis l'interface web (section "Configuration" dans la barre latérale). Vous pouvez aussi éditer le fichier `system_prompt.txt` manuellement.

## 📈 Évolutions Possibles

*   **Mise à jour des données** existantes au lieu de l'ajout systématique.
*   **Analyse depuis une URL** directement dans l'interface web.
*   **Gestion des rôles** utilisateurs (administrateur, etc.).
*   **Interface d'administration** pour gérer les utilisateurs et les extractions.
*   **Scalabilité du LLM** : Pour gérer un plus grand nombre de requêtes simultanées ou des modèles plus lourds :
    *   **Déploiement sur un serveur dédié** : Héberger le LLM sur un serveur plus puissant (avec GPU si nécessaire) et accessible via une API.
    *   **Utilisation d'un service LLM Cloud** : Intégrer un service de LLM externe (ex: OpenAI, Gemini API, Hugging Face Inference API) qui gère la scalabilité automatiquement, moyennant des coûts d'utilisation.
*   **Déploiement de l'application** :
    *   **Streamlit Cloud (Recommandé)** : La solution la plus simple pour mettre votre application en ligne. Nécessite que votre code soit sur GitHub. Vous devrez configurer vos secrets (base de données, clé API LLM) directement dans l'interface de Streamlit Cloud. **Attention :** Votre LLM local devra être remplacé par un service LLM cloud ou un LLM déployé sur un serveur distant accessible via une API. Votre base de données PostgreSQL devra également être accessible depuis Streamlit Cloud.