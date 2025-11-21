# 🤖 Analyseur d'Articles pour Levées de Fonds

Application complète d'extraction d'informations depuis des articles de presse sur les levées de fonds, utilisant un LLM pour structurer les données et WordPress comme source et destination.

## 📋 Table des matières

- [Fonctionnalités](#-fonctionnalités)
- [Architecture](#-architecture)
- [Installation](#️-installation)
- [Configuration](#️-configuration)
- [Utilisation](#-utilisation)
- [Évolutions futures](#-évolutions-futures)
- [Structure du projet](#-structure-du-projet)

---

## ✨ Fonctionnalités

### 🔐 Gestion Multi-utilisateurs
- Authentification sécurisée avec bcrypt
- Historique personnel d'extractions
- Prompts système personnalisables par utilisateur

### 📝 Extraction LLM
- **Analyse manuelle** : Collez un article et extrait les données structurées
- **Import WordPress** : Connexion directe à votre WordPress multisite
- **Traitement par lots** : CLI pour traiter plusieurs fichiers
- **Auto-correction JSON** : Le LLM corrige automatiquement ses erreurs de format
- **Détection de doublons** : Hash SHA256 pour éviter les duplicatas

### 🌐 Intégration WordPress

#### Import depuis WordPress
- ✅ Support WordPress Multisite (sous-domaines ET sous-répertoires)
- ✅ Sélection manuelle des articles avec aperçu
- ✅ Filtres avancés :
  - Recherche par mot-clé
  - Filtrage par date (7 périodes + personnalisé)
  - Filtrage par catégories
  - Pagination
- ✅ Import par lot avec barre de progression
- ✅ Aucune authentification requise pour articles publics

#### Export vers WordPress (🚧 En développement)
- Réinjection des données extraites vers WordPress
- Choix du site de destination
- Formats configurables (articles, custom fields, etc.)
- Rapport de succès détaillé

### 📊 Gestion des données
- Base PostgreSQL avec JSONB pour flexibilité
- Historique complet avec timestamps
- Export JSON des extractions
- Interface de consultation et filtrage

---

## 🏗️ Architecture

### Stack Technologique

**Frontend**
- **Streamlit** (1.51.0) - Interface web interactive
- Multi-onglets : Analyse | Historique | Import WP | Export WP

**Backend**
- **Python** 3.13
- **PostgreSQL** - Base de données relationnelle
- **OpenAI-compatible API** - LLM local (LM Studio) ou distant

**Librairies principales**
- `requests` - Connexion WordPress REST API
- `psycopg2-binary` - Driver PostgreSQL
- `bcrypt` - Hachage sécurisé des mots de passe
- `pandas` - Manipulation et affichage des données

### Flux de données

```
┌─────────────────────────────────────────┐
│  Sources d'entrée                       │
│  ├─ Saisie manuelle (textarea)          │
│  ├─ Import WordPress REST API           │
│  └─ Fichiers batch (.txt)               │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Extraction LLM                         │
│  ├─ Prompt système personnalisable      │
│  ├─ Température : 0.1                   │
│  ├─ Max tokens : 2000                   │
│  └─ Auto-correction JSON (2 retries)    │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Base PostgreSQL                        │
│  ├─ users (auth + prompts custom)       │
│  └─ extractions (JSONB + hash unique)   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Sorties                                │
│  ├─ Historique web (consultation)       │
│  ├─ Export JSON                         │
│  └─ Export WordPress (à venir)          │
└─────────────────────────────────────────┘
```

---

## ⚙️ Installation

### Prérequis

- Python 3.13+
- PostgreSQL 12+
- LM Studio ou service LLM compatible OpenAI

### Étape 1 : Clone et environnement

```bash
git clone <votre-repo>
cd sprint_Ai_final

# Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

### Étape 2 : Installer les dépendances

```bash
pip install -r requirements.txt
```

### Étape 3 : Configurer PostgreSQL

1. **Installer PostgreSQL**
   ```bash
   # macOS
   brew install postgresql
   brew services start postgresql
   
   # Ubuntu/Debian
   sudo apt install postgresql postgresql-contrib
   sudo systemctl start postgresql
   ```

2. **Créer la base de données**
   ```bash
   createdb sprint_ai_db
   ```

3. **Créer le fichier de configuration**
   ```bash
   mkdir -p .streamlit
   ```

4. **Éditer `.streamlit/secrets.toml`**
   ```toml
   [postgres]
   host = "localhost"
   port = 5432
   dbname = "sprint_ai_db"
   user = "votre_utilisateur"
   password = "votre_mot_de_passe"
   ```

### Étape 4 : Configurer le LLM

**Option A : LM Studio (Local)**
1. Télécharger [LM Studio](https://lmstudio.ai/)
2. Charger un modèle (ex: Llama, Mistral)
3. Démarrer le serveur local (port 1234 par défaut)

**Option B : LLM distant**
1. Obtenir une clé API (OpenAI, Gemini, etc.)
2. Configurer les variables d'environnement :
   ```bash
   export LLM_API_URL="https://api.openai.com/v1/chat/completions"
   export LLM_API_KEY="votre_clé_api"
   ```

---

## 🚀 Utilisation

### Interface Web (Recommandée)

```bash
streamlit run app.py
```

Ouvrez http://localhost:8501

#### 1️⃣ Créer un compte
- Cliquez sur "Créer un compte" dans la barre latérale
- Choisissez un nom d'utilisateur et mot de passe

#### 2️⃣ Analyser un article manuellement
- Onglet **"Analyse d'Article"**
- Collez le texte de l'article
- Cliquez sur **"Lancer l'analyse"**
- Les données structurées s'affichent et sont sauvegardées

#### 3️⃣ Importer depuis WordPress
- Onglet **"Import WordPress"**
- **Configuration** :
  - Type : Sous-répertoires (ex: `mind.eu.com/media`)
  - Domaine : `mind.eu.com`
  - Sites : `media`, `finance`, etc. (un par ligne)
- **Tester la connexion**
- **Filtres** :
  - Période : Dernier mois
  - Catégories : Levées de fonds
  - Recherche : "startup"
- **Charger les articles**
- **Sélectionner** les articles souhaités (cases à cocher)
- **Lancer l'extraction** : Le LLM traite chaque article

#### 4️⃣ Consulter l'historique
- Onglet **"Mon Historique"**
- Visualisez toutes vos extractions
- Téléchargez au format JSON

#### 5️⃣ Personnaliser le prompt
- Barre latérale > **"Configuration"**
- Ouvrir **"Éditer le prompt système"**
- Modifier selon vos besoins
- Sauvegarder

### Ligne de commande (Batch)

Pour traiter plusieurs fichiers automatiquement :

#### Option 1 : Fichiers TXT (dossier)

```bash
# Placer les fichiers .txt dans le dossier a_traiter/
cp article*.txt a_traiter/

# Lancer l'extraction
python3 run_extraction.py --user votre_username

# Les fichiers traités sont déplacés dans traites/
```

#### Option 2 : Fichier CSV

Créez un fichier CSV avec une colonne contenant les articles. La colonne peut s'appeler :
- `content`
- `article`
- `text`
- `texte`
- `contenu`

**Exemple de CSV** (`articles.csv`) :

```csv
content
"La startup TechCorp annonce une levée de fonds de 5M€..."
"HealthTech lève 10M€ pour révolutionner la télémédecine..."
"FinanceBot annonce un tour de table de 3M€..."
```

**Lancer l'extraction** :

```bash
python3 run_extraction.py --user votre_username --csv articles.csv
```

**Avantages du CSV** :
- ✅ Traitement de grandes quantités d'articles
- ✅ Import facile depuis Excel/Google Sheets
- ✅ Export depuis bases de données
- ✅ Rapport détaillé avec compteurs de succès/échecs

---

## 🔮 Évolutions futures

### Priorité 1 : Export WordPress

**Objectifs**
- Réinjecter les données extraites dans WordPress
- Choix du site de destination
- Rapport de succès détaillé

**Options à configurer** (selon vos besoins futurs)

1. **Action sur les données extraites**
   - [ ] Créer de nouveaux articles
   - [ ] Enrichir les articles existants avec custom fields
   - [ ] Les deux (dual mode)

2. **Format d'export**
   - [ ] Article texte formaté (HTML/Markdown)
   - [ ] Tableau HTML structuré
   - [ ] Custom fields ACF (Advanced Custom Fields)
   - [ ] Custom Post Type dédié "Levées de fonds"

3. **Destination WordPress**
   - [ ] Même multisite que la source
   - [ ] Site centralisé différent
   - [ ] Choix manuel par export

4. **Statut des articles créés**
   - [ ] Brouillon (pour validation manuelle)
   - [ ] Publié directement
   - [ ] Privé
   - [ ] Programmé (scheduled)

### Priorité 2 : Améliorations

- [ ] **Pagination WordPress** : Charger plus de 100 articles
- [ ] **Export CSV/Excel** : Format tableur en plus de JSON
- [ ] **Webhooks** : Import automatique lors de nouvelles publications WP
- [ ] **API REST** : Exposer l'extraction comme service
- [ ] **Dashboard analytics** : Statistiques sur les levées de fonds
- [ ] **Multi-langue** : Support i18n (FR/EN/ES)
- [ ] **Historique comparatif** : Détecter les changements entre versions

### Priorité 3 : Scalabilité

#### Pour le LLM
- [ ] File d'attente (Celery/RQ) pour traitement asynchrone
- [ ] Load balancing entre plusieurs instances LLM
- [ ] Cache intelligent (Redis) pour articles similaires
- [ ] Passage à GPU pour modèles lourds
- [ ] Service cloud (OpenAI API, Anthropic Claude, etc.)

#### Pour l'application
- [ ] Déploiement Docker + Docker Compose
- [ ] CI/CD (GitHub Actions)
- [ ] Streamlit Cloud ou serveur dédié
- [ ] PostgreSQL géré (AWS RDS, Supabase, etc.)
- [ ] Monitoring (Sentry, Datadog)

---

## 📁 Structure du projet

```
sprint_Ai_final/
├── 📄 app.py                      # Application Streamlit principale
├── 📄 run_extraction.py           # Script CLI batch
├── 📄 database.py                 # Gestion PostgreSQL
├── 📄 wordpress_connector.py      # Connecteur WordPress REST API
├── 📄 system_prompt.txt           # Prompt LLM par défaut
├── 📄 requirements.txt            # Dépendances Python
├── 📄 README.md                   # Ce fichier
├── 📄 test_wordpress_connection.py # Script de test WP
│
├── 📁 .streamlit/
│   └── secrets.toml               # Config PostgreSQL (gitignored)
│
├── 📁 a_traiter/                  # Input : fichiers à traiter (CLI)
├── 📁 traites/                    # Output : fichiers traités (CLI)
│   ├── article1.txt
│   ├── article2.txt
│   └── article_test_1.txt
│
└── 📁 venv/                       # Environnement virtuel Python
```

---

## 🛡️ Sécurité

- ✅ Mots de passe hachés avec bcrypt (coût 12)
- ✅ Secrets PostgreSQL dans `secrets.toml` (gitignored)
- ✅ Validation des entrées utilisateur
- ✅ Contrainte UNIQUE sur `(user_id, content_hash)` → pas de duplicata
- ⚠️ Pour production :
  - Ajouter HTTPS (reverse proxy nginx)
  - Limiter les tentatives de connexion (rate limiting)
  - Activer les logs d'audit
  - Chiffrer les données sensibles en base

---

## 🤝 Support

Pour toute question ou demande d'évolution :

1. **Issues GitHub** : Ouvrir une issue sur le dépôt
2. **Documentation** : Consulter les commentaires dans le code
3. **Configuration LLM** : Voir la documentation LM Studio

---

## 📝 Licence

Ce projet est à usage interne. Tous droits réservés.

---

## 🙏 Crédits

**Technologies utilisées :**
- [Streamlit](https://streamlit.io/) - Interface web
- [PostgreSQL](https://www.postgresql.org/) - Base de données
- [LM Studio](https://lmstudio.ai/) - LLM local
- [WordPress REST API](https://developer.wordpress.org/rest-api/) - Source de données
