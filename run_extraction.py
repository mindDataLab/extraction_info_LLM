import argparse
import csv
import json
import os
import shutil

import requests

import database  # Importe notre nouveau module de base de données

# --- Constantes ---
# L'URL de l'API du LLM peut être configurée via une variable d'environnement
# Par défaut, elle pointe vers un LLM local (ex: LM Studio)
LLM_API_URL = os.getenv("LLM_API_URL", "http://localhost:1234/v1/chat/completions")
SYSTEM_PROMPT_FILE = "system_prompt.txt"
SOURCE_DIR = "a_traiter"
PROCESSED_DIR = "traites"

# --- Fonctions Core ---


def load_system_prompt():
    """Charge le prompt système depuis le fichier."""
    try:
        with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"ERREUR: Le fichier '{SYSTEM_PROMPT_FILE}' est introuvable.")
        return None


def extract_data_from_llm(article_text, system_prompt, max_retries=2):
    """
    Envoie le texte de l'article à l'API du LLM local ou distant et tente d'extraire un JSON valide.
    Inclut une logique de réparation en cas d'échec.
    """
    headers = {"Content-Type": "application/json"}

    # Ajoute la clé API si elle est configurée (pour les services distants)
    llm_api_key = os.getenv("LLM_API_KEY")
    if llm_api_key:
        # Exemple pour une clé Bearer (courant pour OpenAI, Gemini, etc.)
        headers["Authorization"] = f"Bearer {llm_api_key}"
        # Si le service utilise un autre type d'authentification, cela devra être adapté ici.

    history = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": article_text},
    ]

    for attempt in range(max_retries + 1):
        payload = {
            "messages": history,
            "temperature": 0.1,
            "max_tokens": 2000,
            "stream": False,
        }
        try:
            response = requests.post(LLM_API_URL, headers=headers, json=payload)
            response.raise_for_status()

            llm_response_text = response.json()["choices"][0]["message"]["content"]

            # Essayer de parser le JSON
            json_start = llm_response_text.find("{")
            json_end = llm_response_text.rfind("}") + 1
            if json_start != -1:
                json_str = llm_response_text[json_start:json_end]
                return json.loads(json_str)
            else:
                raise ValueError("Aucun objet JSON trouvé dans la réponse.")

        except (json.JSONDecodeError, ValueError) as e:
            print(f"Tentative {attempt + 1}: Erreur de décodage JSON. {e}")
            if attempt < max_retries:
                print("Demande de correction au LLM...")
                history.append({"role": "assistant", "content": llm_response_text})
                history.append(
                    {
                        "role": "user",
                        "content": "Votre réponse précédente n'était pas un JSON valide. Veuillez corriger le format et ne renvoyer que le JSON corrigé, sans texte supplémentaire.",
                    }
                )
            else:
                print("Échec de l'extraction des données après plusieurs tentatives.")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Erreur de connexion à l'API du LLM: {e}")
            return None
    return None


# --- Logique de Traitement par Lots ---


def process_csv(user_id, system_prompt, csv_file):
    """
    Traite un fichier CSV contenant des articles.
    Le CSV doit avoir une colonne 'content' ou 'article' avec le texte.
    """
    print(f"Traitement du fichier CSV: {csv_file}")

    try:
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # Détecter la colonne de contenu
            fieldnames = reader.fieldnames
            content_column = None
            for col in ["content", "article", "text", "texte", "contenu"]:
                if col in fieldnames:
                    content_column = col
                    break

            if not content_column:
                print(f"ERREUR: Aucune colonne de contenu trouvée dans le CSV.")
                print(f"Colonnes disponibles: {', '.join(fieldnames)}")
                print(
                    f"Le CSV doit contenir une colonne nommée: 'content', 'article', 'text', 'texte', ou 'contenu'"
                )
                return

            print(f"Colonne de contenu détectée: '{content_column}'")

            row_count = 0
            success_count = 0
            error_count = 0

            for row_num, row in enumerate(
                reader, start=2
            ):  # Start at 2 (ligne 1 = header)
                article_content = row.get(content_column, "").strip()

                if not article_content:
                    print(f"Ligne {row_num}: Contenu vide, ignoré.")
                    continue

                row_count += 1
                print(
                    f"\n--- Traitement ligne {row_num} ({row_count} articles traités) ---"
                )

                extracted_data = extract_data_from_llm(article_content, system_prompt)

                if extracted_data:
                    content_hash = database.calculate_content_hash(article_content)
                    success, message = database.add_extraction(
                        user_id=user_id,
                        original_content=article_content,
                        extracted_data=json.dumps(extracted_data),
                        content_hash=content_hash,
                    )
                    if success:
                        print(f"✅ Données sauvegardées/mises à jour.")
                        success_count += 1
                    else:
                        print(f"❌ Erreur de sauvegarde: {message}")
                        error_count += 1
                else:
                    print(f"❌ Échec de l'extraction.")
                    error_count += 1

            print(f"\n{'=' * 60}")
            print(f"Traitement terminé:")
            print(f"  - {row_count} articles traités")
            print(f"  - {success_count} succès")
            print(f"  - {error_count} échecs")
            print(f"{'=' * 60}")

    except FileNotFoundError:
        print(f"ERREUR: Fichier '{csv_file}' introuvable.")
    except Exception as e:
        print(f"ERREUR lors de la lecture du CSV: {e}")


def process_batch(user_id, system_prompt):
    """
    Traite tous les fichiers .txt dans le dossier SOURCE_DIR.
    """
    print(f"Lancement du traitement par lots pour l'utilisateur ID: {user_id}...")
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    files_to_process = [f for f in os.listdir(SOURCE_DIR) if f.endswith(".txt")]
    if not files_to_process:
        print("Aucun fichier à traiter dans le dossier 'a_traiter'.")
        return

    for filename in files_to_process:
        filepath = os.path.join(SOURCE_DIR, filename)
        print(f"--- Traitement du fichier: {filename} ---")

        with open(filepath, "r", encoding="utf-8") as f:
            article_content = f.read()

        if not article_content.strip():
            print("Fichier vide, ignoré.")
            continue

        extracted_data = extract_data_from_llm(article_content, system_prompt)

        if extracted_data:
            print("Données extraites avec succès.")
            # Calculer le hash du contenu
            content_hash = database.calculate_content_hash(article_content)

            success, message = database.add_extraction(
                user_id=user_id,
                original_content=article_content,
                extracted_data=json.dumps(extracted_data),
                content_hash=content_hash,
            )
            if success:
                print(
                    f"Données sauvegardées/mises à jour dans la base de données pour l'utilisateur {user_id}."
                )
                # Déplacer le fichier traité
                shutil.move(filepath, os.path.join(PROCESSED_DIR, filename))
                print(f"Fichier déplacé vers '{PROCESSED_DIR}'.")
            else:
                print(f"Erreur lors de la sauvegarde en base de données: {message}")
        else:
            print("Échec de l'extraction des données pour ce fichier.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Script de traitement par lots pour l'extraction de données."
    )
    parser.add_argument(
        "--user",
        type=str,
        required=True,
        help="Nom d'utilisateur pour associer les extractions.",
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="Chemin vers un fichier CSV à traiter (doit contenir une colonne 'content', 'article', 'text', 'texte' ou 'contenu')",
    )
    args = parser.parse_args()

    # Vérifier si l'utilisateur existe
    user = database.get_user(args.user)
    if not user:
        print(
            f"ERREUR: L'utilisateur '{args.user}' n'existe pas. Veuillez d'abord le créer via l'application web."
        )
    else:
        # Déterminer le prompt système à utiliser
        if user["custom_system_prompt"]:
            system_prompt_to_use = user["custom_system_prompt"]
            print(
                f"Utilisation du prompt personnalisé pour l'utilisateur '{args.user}'."
            )
        else:
            system_prompt_to_use = load_system_prompt()
            print(f"Utilisation du prompt par défaut pour l'utilisateur '{args.user}'.")

        if system_prompt_to_use:
            # Si un fichier CSV est fourni, traiter le CSV
            if args.csv:
                process_csv(
                    user_id=user["id"],
                    system_prompt=system_prompt_to_use,
                    csv_file=args.csv,
                )
            else:
                # Sinon, traiter les fichiers txt du dossier a_traiter
                process_batch(user_id=user["id"], system_prompt=system_prompt_to_use)
        else:
            print(
                "ERREUR: Le prompt système est vide. Impossible de lancer le traitement."
            )
