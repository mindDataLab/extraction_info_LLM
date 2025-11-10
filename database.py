import os
import psycopg2
import psycopg2.extras
import bcrypt
import streamlit as st
import json
import hashlib # Importation pour le hachage
from urllib.parse import urlparse

# --- Database Connection ---

# Utilise les secrets de Streamlit pour les détails de connexion
def get_db_connection():
    """Établit une connexion à la base de données PostgreSQL."""
    try:
        conn = psycopg2.connect(
            host=st.secrets["postgres"]["host"],
            dbname=st.secrets["postgres"]["dbname"],
            user=st.secrets["postgres"]["user"],
            password=st.secrets["postgres"]["password"],
            port=st.secrets["postgres"]["port"]
        )
        return conn
    except Exception as e:
        st.error(f"Erreur de connexion à la base de données : {e}")
        return None

# --- Schema Initialization ---

def init_db():
    """Initialise la base de données en créant les tables si elles n'existent pas et en ajoutant des colonnes/contraintes si nécessaire."""
    conn = get_db_connection()
    if conn is None:
        st.error("La connexion à la base de données a échoué, impossible d'initialiser.")
        return
        
    try:
        with conn.cursor() as cur:
            # Table pour les utilisateurs
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(80) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Ajout de la colonne custom_system_prompt si elle n'existe pas
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='custom_system_prompt') THEN
                        ALTER TABLE users ADD COLUMN custom_system_prompt TEXT;
                    END IF;
                END
                $$;
            """)

            # Table pour les extractions
            cur.execute("""
                CREATE TABLE IF NOT EXISTS extractions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    original_content TEXT,
                    extracted_data JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                );
            """)
            
            # Ajout de la colonne content_hash si elle n'existe pas
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='extractions' AND column_name='content_hash') THEN
                        ALTER TABLE extractions ADD COLUMN content_hash VARCHAR(64);
                    END IF;
                END
                $$;
            """)

            # Ajout de la contrainte UNIQUE (user_id, content_hash) si elle n'existe pas
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_user_content') THEN
                        ALTER TABLE extractions ADD CONSTRAINT unique_user_content UNIQUE (user_id, content_hash);
                    END IF;
                END
                $$;
            """)

        conn.commit()
    except Exception as e:
        st.error(f"Erreur lors de l'initialisation de la base de données : {e}")
    finally:
        if conn:
            conn.close()

# --- User Management ---

def hash_password(password):
    """Hashe un mot de passe en utilisant bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed_password):
    """Vérifie un mot de passe par rapport à un hash stocké."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def add_user(username, password):
    """Ajoute un nouvel utilisateur à la base de données."""
    conn = get_db_connection()
    if conn is None: return False, "Connexion à la base de données échouée."
    
    password_hash = hash_password(password)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, password_hash)
            )
        conn.commit()
        return True, "Utilisateur créé avec succès."
    except psycopg2.IntegrityError:
        return False, "Ce nom d'utilisateur existe déjà."
    except Exception as e:
        return False, f"Erreur lors de la création de l'utilisateur : {e}"
    finally:
        if conn:
            conn.close()

def get_user(username):
    """Récupère un utilisateur par son nom d'utilisateur."""
    conn = get_db_connection()
    if conn is None: return None
    
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            return user
    except Exception as e:
        st.error(f"Erreur pour récupérer l'utilisateur : {e}")
        return None
    finally:
        if conn:
            conn.close()

def update_user_prompt(user_id, prompt_content):
    """Met à jour le prompt système personnalisé d'un utilisateur."""
    conn = get_db_connection()
    if conn is None: return False, "Connexion à la base de données échouée."

    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET custom_system_prompt = %s WHERE id = %s",
                (prompt_content, user_id)
            )
        conn.commit()
        return True, "Prompt utilisateur mis à jour avec succès."
    except Exception as e:
        return False, f"Erreur lors de la mise à jour du prompt utilisateur : {e}"
    finally:
        if conn:
            conn.close()

# --- Extractions Management ---

def calculate_content_hash(content):
    """Calcule le hash SHA256 du contenu donné."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def add_extraction(user_id, original_content, extracted_data, content_hash):
    """Ajoute ou met à jour un enregistrement d'extraction dans la base de données."""
    conn = get_db_connection()
    if conn is None: return False, "Connexion à la base de données échouée."
    
    try:
        with conn.cursor() as cur:
            if not isinstance(extracted_data, str):
                extracted_data = json.dumps(extracted_data)

            cur.execute("""
                INSERT INTO extractions (user_id, original_content, extracted_data, content_hash)
                VALUES (%s, %s, %s::jsonb, %s)
                ON CONFLICT (user_id, content_hash) DO UPDATE SET
                    original_content = EXCLUDED.original_content,
                    extracted_data = EXCLUDED.extracted_data,
                    created_at = CURRENT_TIMESTAMP
            """,
            (user_id, original_content, extracted_data, content_hash)
            )
        conn.commit()
        return True, "Extraction ajoutée/mise à jour avec succès."
    except Exception as e:
        return False, f"Erreur lors de l'ajout/mise à jour de l'extraction : {e}"
    finally:
        if conn:
            conn.close()

def get_extractions_by_user(user_id):
    """Récupère toutes les extractions pour un utilisateur donné."""
    conn = get_db_connection()
    if conn is None: return []
    
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                "SELECT id, extracted_data, created_at FROM extractions WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,)
            )
            extractions = cur.fetchall()
            return extractions
    except Exception as e:
        st.error(f"Erreur pour récupérer les extractions : {e}")
        return []
    finally:
        if conn:
            conn.close()