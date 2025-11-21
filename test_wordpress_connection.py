"""
Script de test pour vérifier la connexion WordPress
"""

from wordpress_connector import WordPressConnector

# Configuration pour votre cas
BASE_DOMAIN = "mind.eu.com"
SITE = "media"
USE_SUBDIRECTORY = True

print("=" * 60)
print("Test de connexion WordPress")
print("=" * 60)

# Créer le connecteur
connector = WordPressConnector(
    base_domain=BASE_DOMAIN, use_subdirectory=USE_SUBDIRECTORY
)

print(f"\n📋 Configuration:")
print(f"   Domaine de base: {BASE_DOMAIN}")
print(f"   Site: {SITE}")
print(f"   Type: {'Sous-répertoire' if USE_SUBDIRECTORY else 'Sous-domaine'}")
print(
    f"   URL construite: https://{BASE_DOMAIN}/{SITE if USE_SUBDIRECTORY else SITE + '.' + BASE_DOMAIN}"
)

# Test de connexion
print(f"\n🔍 Test de connexion...")
result = connector.test_connection(SITE)

if result["success"]:
    print(f"✅ {result['message']}")
    print(f"🔗 URL: {result['url']}")
    print(f"📊 Code HTTP: {result['status_code']}")

    # Essayer de récupérer quelques articles
    print(f"\n📥 Tentative de récupération des articles...")
    try:
        posts_result = connector.get_posts(SITE, per_page=5)
        print(f"✅ {len(posts_result['posts'])} articles récupérés")
        print(f"📊 Total d'articles disponibles: {posts_result['total_posts']}")

        if posts_result["posts"]:
            print(f"\n📰 Premier article:")
            first_post = posts_result["posts"][0]
            print(f"   Titre: {first_post['title']}")
            print(f"   Date: {first_post['date']}")
            print(f"   Auteur: {first_post['author']}")
            print(f"   Lien: {first_post['link']}")
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des articles: {e}")
else:
    print(f"❌ {result['message']}")
    print(f"🔗 URL testée: {result['url']}")
    if result["status_code"]:
        print(f"📊 Code HTTP: {result['status_code']}")

print("\n" + "=" * 60)
