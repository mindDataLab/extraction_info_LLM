# 🚀 Guide de Déploiement - Streamlit Cloud + Supabase

Ce guide vous explique comment déployer votre application sur **Streamlit Cloud** (gratuit et optimisé pour Streamlit) avec votre base de données Supabase.

---

## ✅ Avantages de Streamlit Cloud vs Vercel

| Critère | Streamlit Cloud | Vercel |
|---------|----------------|--------|
| **Optimisé pour Streamlit** | ✅ Oui | ⚠️ Non |
| **Limite de taille** | ✅ Pas de limite stricte | ❌ 250 MB max |
| **Prix** | ✅ Gratuit | ✅ Gratuit (mais limité) |
| **Configuration** | ✅ Simple | ⚠️ Complexe |
| **Performance** | ✅ Excellente | ⚠️ Moyenne |

---

## 📋 Prérequis

- ✅ Compte GitHub (déjà fait)
- ✅ Code poussé sur GitHub (déjà fait)
- ✅ Base de données Supabase configurée (déjà fait)
- ✅ Clé API OpenAI (déjà configurée)
- ⏳ Compte Streamlit Cloud (à créer - gratuit)

---

## 🎯 Étape 1 : Créer un compte Streamlit Cloud

1. Allez sur **[share.streamlit.io](https://share.streamlit.io)**
2. Cliquez sur **"Sign up"** ou **"Get started"**
3. **Connectez-vous avec GitHub** (recommandé)
4. Autorisez Streamlit à accéder à vos repos GitHub

✅ Votre compte est créé !

---

## 📦 Étape 2 : Déployer votre application

### 1. Créer une nouvelle app

1. Dans le dashboard Streamlit Cloud, cliquez sur **"New app"**
2. Remplissez les informations :

```
Repository: escanorf/extraction_info_LLM
Branch: main
Main file path: app.py
App URL (optional): choisissez un nom unique (ex: extraction-llm-samuel)
```

3. Cliquez sur **"Advanced settings"** avant de déployer

---

## 🔐 Étape 3 : Configurer les secrets (Variables d'environnement)

Dans **Advanced settings** > **Secrets**, copiez-collez ceci :

```toml
# === DATABASE SUPABASE ===
DB_HOST = "aws-0-[region].pooler.supabase.com"
DB_PORT = "6543"
DB_NAME = "postgres"
DB_USER = "postgres.xxxxxxxxxxxxx"
DB_PASSWORD = "votre_mot_de_passe_supabase"

# === OPENAI API ===
USE_OPENAI = "true"
OPENAI_API_KEY = "sk-proj-VOTRE_CLE_API_OPENAI_ICI"
OPENAI_MODEL = "gpt-4o-mini"
```

**📋 Note importante** : Remplacez les valeurs ci-dessus par vos vraies credentials :
- Récupérez vos infos Supabase depuis votre Dashboard Supabase
- Récupérez votre clé OpenAI depuis [platform.openai.com](https://platform.openai.com/api-keys)

**⚠️ Important** : Le format est TOML (pas comme .env). Notez les guillemets autour des valeurs.

---

## 🚀 Étape 4 : Lancer le déploiement

1. Vérifiez que tout est correct
2. Cliquez sur **"Deploy!"**
3. Attendez 2-5 minutes ⏱️

Vous verrez les logs en temps réel :
```
Installing dependencies...
✅ streamlit==1.51.0
✅ psycopg2-binary==2.9.11
✅ bcrypt==5.0.0
✅ openai==2.8.1
✅ pandas==2.3.3
✅ requests==2.32.5

Starting app...
✅ App is live!
```

---

## 🎉 Étape 5 : Accéder à votre application

Votre app sera disponible à l'URL :
```
https://[votre-nom-app].streamlit.app
```

Exemple : `https://extraction-llm-samuel.streamlit.app`

---

## 🧪 Étape 6 : Tester l'application

1. Ouvrez l'URL de votre app
2. **Créez un compte** utilisateur
3. **Testez une extraction** d'article
4. Vérifiez dans **Supabase Table Editor** que les données sont sauvegardées

✅ Tout fonctionne ? Félicitations ! 🎊

---

## 🔧 Configuration avancée

### Modifier les secrets après déploiement

1. Dans le dashboard Streamlit Cloud
2. Cliquez sur votre app
3. Menu **⚙️ Settings** > **Secrets**
4. Modifiez et sauvegardez
5. L'app redémarre automatiquement

### Mettre à jour l'application

Pour déployer une nouvelle version :

```bash
# Sur votre machine locale
git add .
git commit -m "Nouvelle fonctionnalité"
git push origin main
```

Streamlit Cloud **redéploie automatiquement** quand vous poussez sur GitHub ! 🚀

### Voir les logs en temps réel

1. Dans le dashboard, cliquez sur votre app
2. Cliquez sur **"Manage app"**
3. Onglet **"Logs"** pour voir les logs en direct

---

## 🛟 Résolution de problèmes

### Erreur : "ModuleNotFoundError"

**Cause** : Une dépendance manque dans `requirements.txt`

**Solution** :
1. Ajoutez la dépendance dans `requirements.txt`
2. Commit et push
3. Streamlit Cloud redéploie automatiquement

### Erreur : "Connection to database failed"

**Cause** : Les secrets Supabase sont incorrects

**Solution** :
1. Vérifiez les secrets dans Settings > Secrets
2. Assurez-vous du format TOML avec guillemets
3. Vérifiez le mot de passe Supabase

### Erreur : "OpenAI API Error"

**Cause** : Clé API invalide ou quota dépassé

**Solution** :
1. Vérifiez votre clé sur [platform.openai.com](https://platform.openai.com)
2. Vérifiez que vous avez des crédits disponibles
3. Mettez à jour le secret `OPENAI_API_KEY`

### L'app est lente ou s'endort

**Cause** : Plan gratuit = l'app s'endort après inactivité

**Solutions** :
- Sur le plan gratuit, l'app s'endort après 7 jours sans visite
- Elle redémarre automatiquement quand quelqu'un visite
- Upgrade vers un plan payant pour une app toujours active

---

## 📊 Limites du plan gratuit

| Ressource | Limite |
|-----------|--------|
| **Apps publiques** | Illimité |
| **Visiteurs** | Illimité |
| **Storage** | 1 GB |
| **Calcul** | Partagé |
| **Temps d'activité** | App s'endort après 7j d'inactivité |

Pour la plupart des usages, c'est **largement suffisant** ! ✅

---

## 🔒 Sécurité et confidentialité

### Rendre votre app privée (optionnel)

Par défaut, votre app est **publique** (n'importe qui avec l'URL peut y accéder).

Pour la rendre privée :
1. Settings > **Sharing**
2. Activez **"Restrict viewer access"**
3. Ajoutez les emails autorisés

⚠️ **Note** : Votre app a déjà un système d'authentification intégré (users/password), donc même si l'URL est publique, il faut se connecter pour utiliser les fonctionnalités.

### Secrets exposés ?

- ✅ Les secrets (DB_PASSWORD, OPENAI_API_KEY) ne sont **jamais exposés** au public
- ✅ Ils sont stockés de manière sécurisée par Streamlit Cloud
- ✅ Seuls les admins de l'app peuvent les voir

---

## 📈 Monitoring

### Voir l'utilisation

1. Dashboard Streamlit Cloud
2. Cliquez sur votre app
3. **Analytics** pour voir :
   - Nombre de visiteurs
   - Utilisation des ressources
   - Temps de réponse

### Voir l'utilisation Supabase

1. Dashboard Supabase
2. **Database** pour voir le nombre de requêtes
3. **Table Editor** pour voir les données

### Voir l'utilisation OpenAI

1. [platform.openai.com/usage](https://platform.openai.com/usage)
2. Surveillez vos crédits et coûts

---

## 🎁 Fonctionnalités bonus de Streamlit Cloud

- ✅ **Auto-redéploiement** : Push sur GitHub = mise à jour automatique
- ✅ **HTTPS gratuit** : Certificat SSL automatique
- ✅ **Logs en temps réel** : Debugging facile
- ✅ **Partage facile** : Une simple URL à partager
- ✅ **Support communautaire** : Forum actif

---

## ✅ Checklist finale

- [ ] Compte Streamlit Cloud créé
- [ ] Connecté avec GitHub
- [ ] Nouvelle app créée
- [ ] Repository et branch sélectionnés
- [ ] Fichier app.py spécifié
- [ ] Secrets configurés (format TOML)
- [ ] Application déployée avec succès
- [ ] Test de création de compte réussi
- [ ] Test d'extraction réussi
- [ ] Données visibles dans Supabase
- [ ] URL de production notée et partagée 🎊

---

## 🆚 Comparaison avec Vercel

Si vous voulez quand même essayer Vercel plus tard (pas recommandé pour Streamlit) :
- Les fichiers `vercel.json` et `runtime.txt` sont déjà dans votre repo
- Mais Streamlit Cloud est **vraiment** plus adapté

---

## 🎉 Félicitations !

Votre application est maintenant déployée et accessible au monde entier ! 🌍

**URL de votre app** : `https://[votre-nom].streamlit.app`

Pour toute question :
- 📖 [Documentation Streamlit](https://docs.streamlit.io)
- 💬 [Forum Streamlit](https://discuss.streamlit.io)
- 🗄️ [Documentation Supabase](https://supabase.com/docs)

---

## 🚀 Prochaines étapes suggérées

1. Testez votre app en conditions réelles
2. Partagez l'URL avec vos utilisateurs
3. Surveillez les logs et l'utilisation
4. Ajoutez des fonctionnalités supplémentaires
5. Configurez un domaine personnalisé (optionnel, plan payant)

Bonne chance ! 🍀
