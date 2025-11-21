"""
WordPress Multisite Connector
Permet de se connecter à un WordPress multisite et récupérer les articles
par sous-repertoire/verticale
"""

from datetime import datetime
from typing import Dict, List, Optional

import requests


class WordPressConnector:
    """Connecteur pour WordPress REST API avec support multisite"""

    def __init__(
        self,
        base_domain: str,
        auth_user: Optional[str] = None,
        auth_password: Optional[str] = None,
        use_subdirectory: bool = False,
    ):
        """
        Initialize WordPress connector

        Args:
            base_domain: Domaine de base (ex: "example.com" ou "mind.eu.com")
            auth_user: Username WordPress (optionnel, pour articles privés)
            auth_password: Mot de passe ou Application Password WordPress
            use_subdirectory: True si multisite en sous-répertoires (ex: domain.com/site1),
                            False si en sous-domaines (ex: site1.domain.com)
        """
        self.base_domain = base_domain.rstrip("/")
        self.use_subdirectory = use_subdirectory
        self.auth = None
        if auth_user and auth_password:
            self.auth = (auth_user, auth_password)

    def get_subdomains(self) -> List[str]:
        """
        Retourne la liste des sous-domaines configurés
        Note: Cette méthode doit être configurée manuellement car WordPress
        multisite n'expose pas automatiquement la liste des sites via API

        Returns:
            Liste des sous-domaines (ex: ["tech", "finance", "health"])
        """
        # Cette liste sera configurée via l'interface Streamlit
        # ou stockée en base de données
        return []

    def get_posts(
        self,
        subdomain: str,
        per_page: int = 20,
        page: int = 1,
        search: str = "",
        categories: List[int] = None,
        after: str = None,
        before: str = None,
    ) -> Dict:
        """
        Récupère les articles d'un sous-domaine spécifique

        Args:
            subdomain: Sous-domaine à interroger (ex: "tech" pour tech.example.com)
            per_page: Nombre d'articles par page (max 100)
            page: Numéro de page
            search: Terme de recherche (optionnel)
            categories: Liste d'IDs de catégories (optionnel)
            after: Date ISO 8601 - articles après cette date (optionnel)
            before: Date ISO 8601 - articles avant cette date (optionnel)

        Returns:
            Dict avec 'posts' (liste d'articles) et 'total_pages'
        """
        # Construire l'URL selon le type de multisite
        if self.use_subdirectory:
            site_url = f"https://{self.base_domain}/{subdomain}"
        else:
            site_url = f"https://{subdomain}.{self.base_domain}"
        api_url = f"{site_url}/wp-json/wp/v2/posts"

        # Paramètres de la requête
        params = {
            "per_page": min(per_page, 100),  # WordPress limite à 100
            "page": page,
            "_embed": True,  # Inclut les métadonnées (featured image, auteur, etc.)
        }

        if search:
            params["search"] = search

        if categories:
            params["categories"] = ",".join(map(str, categories))

        if after:
            params["after"] = after

        if before:
            params["before"] = before

        try:
            response = requests.get(api_url, params=params, auth=self.auth, timeout=30)
            response.raise_for_status()

            posts = response.json()
            total_pages = int(response.headers.get("X-WP-TotalPages", 1))
            total_posts = int(response.headers.get("X-WP-Total", 0))

            # Formater les posts pour faciliter l'affichage
            formatted_posts = []
            for post in posts:
                formatted_posts.append(self._format_post(post))

            return {
                "posts": formatted_posts,
                "total_pages": total_pages,
                "total_posts": total_posts,
                "current_page": page,
            }

        except requests.exceptions.RequestException as e:
            raise Exception(f"Erreur de connexion à WordPress: {str(e)}")

    def _format_post(self, post: Dict) -> Dict:
        """
        Formate un article WordPress pour l'affichage

        Args:
            post: Article brut de l'API WordPress

        Returns:
            Article formaté
        """
        # Extraire le contenu HTML et le nettoyer
        content = post.get("content", {}).get("rendered", "")
        excerpt = post.get("excerpt", {}).get("rendered", "")

        # Extraire l'image mise en avant
        featured_image = None
        if "_embedded" in post and "wp:featuredmedia" in post["_embedded"]:
            media = post["_embedded"]["wp:featuredmedia"][0]
            featured_image = media.get("source_url")

        # Extraire l'auteur
        author_name = "Inconnu"
        if "_embedded" in post and "author" in post["_embedded"]:
            author = post["_embedded"]["author"][0]
            author_name = author.get("name", "Inconnu")

        # Extraire les catégories
        categories = []
        if "_embedded" in post and "wp:term" in post["_embedded"]:
            terms = post["_embedded"]["wp:term"]
            if terms and len(terms) > 0:
                categories = [cat["name"] for cat in terms[0]]

        return {
            "id": post.get("id"),
            "title": post.get("title", {}).get("rendered", "Sans titre"),
            "content": content,
            "excerpt": excerpt,
            "date": post.get("date"),
            "modified": post.get("modified"),
            "link": post.get("link"),
            "author": author_name,
            "categories": categories,
            "featured_image": featured_image,
            "status": post.get("status", "publish"),
        }

    def get_post_by_id(self, subdomain: str, post_id: int) -> Dict:
        """
        Récupère un article spécifique par son ID

        Args:
            subdomain: Sous-domaine
            post_id: ID de l'article

        Returns:
            Article formaté
        """
        if self.use_subdirectory:
            site_url = f"https://{self.base_domain}/{subdomain}"
        else:
            site_url = f"https://{subdomain}.{self.base_domain}"
        api_url = f"{site_url}/wp-json/wp/v2/posts/{post_id}"

        try:
            response = requests.get(
                api_url, params={"_embed": True}, auth=self.auth, timeout=30
            )
            response.raise_for_status()
            post = response.json()
            return self._format_post(post)

        except requests.exceptions.RequestException as e:
            raise Exception(f"Erreur lors de la récupération de l'article: {str(e)}")

    def get_categories(self, subdomain: str) -> List[Dict]:
        """
        Récupère les catégories disponibles sur un sous-domaine

        Args:
            subdomain: Sous-domaine

        Returns:
            Liste des catégories avec ID et nom
        """
        if self.use_subdirectory:
            site_url = f"https://{self.base_domain}/{subdomain}"
        else:
            site_url = f"https://{subdomain}.{self.base_domain}"
        api_url = f"{site_url}/wp-json/wp/v2/categories"

        try:
            response = requests.get(
                api_url, params={"per_page": 100}, auth=self.auth, timeout=30
            )
            response.raise_for_status()

            categories = response.json()
            return [
                {"id": cat["id"], "name": cat["name"], "count": cat["count"]}
                for cat in categories
            ]

        except requests.exceptions.RequestException as e:
            raise Exception(f"Erreur lors de la récupération des catégories: {str(e)}")

    def test_connection(self, subdomain: str) -> Dict:
        """
        Teste la connexion à un sous-domaine WordPress

        Args:
            subdomain: Sous-domaine à tester

        Returns:
            Dict avec 'success' (bool), 'message' (str), 'url' (str), 'status_code' (int ou None)
        """
        if self.use_subdirectory:
            site_url = f"https://{self.base_domain}/{subdomain}"
        else:
            site_url = f"https://{subdomain}.{self.base_domain}"
        api_url = f"{site_url}/wp-json/wp/v2"

        try:
            response = requests.get(api_url, timeout=10, auth=self.auth)
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Connexion réussie",
                    "url": api_url,
                    "status_code": 200,
                }
            else:
                return {
                    "success": False,
                    "message": f"Erreur HTTP {response.status_code}",
                    "url": api_url,
                    "status_code": response.status_code,
                }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "message": f"Impossible de se connecter à {site_url}. Vérifiez que le domaine existe.",
                "url": api_url,
                "status_code": None,
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "message": f"Délai d'attente dépassé lors de la connexion à {site_url}",
                "url": api_url,
                "status_code": None,
            }
        except requests.exceptions.SSLError:
            return {
                "success": False,
                "message": f"Erreur SSL. Le certificat de {site_url} est peut-être invalide.",
                "url": api_url,
                "status_code": None,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Erreur: {str(e)}",
                "url": api_url,
                "status_code": None,
            }

    def strip_html_tags(self, html_text: str) -> str:
        """
        Nettoie le HTML pour extraire uniquement le texte

        Args:
            html_text: Texte HTML

        Returns:
            Texte brut sans balises HTML
        """
        import re

        # Supprime les balises HTML
        clean = re.compile("<.*?>")
        text = re.sub(clean, "", html_text)
        # Décode les entités HTML
        import html

        text = html.unescape(text)
        # Nettoie les espaces multiples
        text = re.sub(r"\s+", " ", text).strip()
        return text
