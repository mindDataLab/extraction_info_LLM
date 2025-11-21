#!/usr/bin/env python3
"""
Script de diagnostic de connexion Supabase
"""

import sys

import psycopg2

# Configuration
PROJECT_REF = "zxlkgdlvovoybiencjzk"
PASSWORD = "samuelKamek971!"

# Toutes les configurations possibles à tester
configurations = [
    # Connexion directe (nécessite IPv6)
    {
        "name": "Connexion directe",
        "host": f"db.{PROJECT_REF}.supabase.co",
        "port": "5432",
        "user": "postgres",
        "dbname": "postgres",
    },
    # Pooler Session mode avec différents formats d'utilisateur
    {
        "name": "Pooler Session - user format 1",
        "host": f"aws-0-eu-central-1.pooler.supabase.com",
        "port": "6543",
        "user": f"postgres.{PROJECT_REF}",
        "dbname": "postgres",
    },
    {
        "name": "Pooler Session - user format 2",
        "host": f"aws-0-eu-central-1.pooler.supabase.com",
        "port": "6543",
        "user": "postgres",
        "dbname": "postgres",
    },
    # Pooler Transaction mode
    {
        "name": "Pooler Transaction - user format 1",
        "host": f"aws-0-eu-central-1.pooler.supabase.com",
        "port": "5432",
        "user": f"postgres.{PROJECT_REF}",
        "dbname": "postgres",
    },
    {
        "name": "Pooler Transaction - user format 2",
        "host": f"aws-0-eu-central-1.pooler.supabase.com",
        "port": "5432",
        "user": "postgres",
        "dbname": "postgres",
    },
]

print("=" * 70)
print("🔍 DIAGNOSTIC DE CONNEXION SUPABASE")
print("=" * 70)
print(f"Project Ref: {PROJECT_REF}")
print(f"IPv6 supporté: Non (d'après les tests précédents)")
print("=" * 70)

successful_config = None

for i, config in enumerate(configurations, 1):
    print(f"\n[{i}/{len(configurations)}] Test: {config['name']}")
    print(f"    Host: {config['host']}")
    print(f"    Port: {config['port']}")
    print(f"    User: {config['user']}")
    print(f"    DB: {config['dbname']}")

    try:
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=PASSWORD,
            dbname=config["dbname"],
            connect_timeout=10,
        )

        print("    ✅ CONNEXION RÉUSSIE!")

        # Tester une requête
        with conn.cursor() as cur:
            cur.execute("SELECT version(), current_user, current_database();")
            version, user, db = cur.fetchone()
            print(f"    📊 Utilisateur: {user}")
            print(f"    📊 Base: {db}")
            print(f"    📊 Version: {version[:60]}...")

            # Vérifier les tables
            cur.execute("""
                SELECT count(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """)
            table_count = cur.fetchone()[0]
            print(f"    📋 Tables publiques: {table_count}")

        conn.close()
        successful_config = config
        print("\n" + "=" * 70)
        print("✨ CONFIGURATION FONCTIONNELLE TROUVÉE!")
        print("=" * 70)
        break

    except psycopg2.OperationalError as e:
        error_msg = str(e)
        if "No route to host" in error_msg:
            print("    ❌ Pas de route (probablement IPv6)")
        elif "Tenant or user not found" in error_msg:
            print("    ⚠️  Serveur accessible mais user/tenant invalide")
        elif "timeout" in error_msg.lower():
            print("    ❌ Timeout de connexion")
        elif "password authentication failed" in error_msg:
            print("    ❌ Mot de passe incorrect")
        else:
            print(f"    ❌ Erreur: {error_msg[:100]}")
    except Exception as e:
        print(f"    ❌ Erreur inattendue: {type(e).__name__}: {str(e)[:80]}")

print("\n" + "=" * 70)

if successful_config:
    print("📝 CONFIGURATION À UTILISER DANS secrets.toml:")
    print("=" * 70)
    print("[postgres]")
    print(f'host = "{successful_config["host"]}"')
    print(f'port = "{successful_config["port"]}"')
    print(f'dbname = "{successful_config["dbname"]}"')
    print(f'user = "{successful_config["user"]}"')
    print(f'password = "{PASSWORD}"')
    print("=" * 70)
    sys.exit(0)
else:
    print("❌ AUCUNE CONFIGURATION FONCTIONNELLE TROUVÉE")
    print("\n💡 Actions recommandées:")
    print("   1. Vérifiez votre dashboard Supabase:")
    print(
        f"      https://supabase.com/dashboard/project/{PROJECT_REF}/settings/database"
    )
    print("   2. Copiez la 'Connection string' exacte depuis la section Database")
    print("   3. Vérifiez que le mot de passe est correct")
    print("   4. Assurez-vous que votre projet Supabase est actif")
    print("=" * 70)
    sys.exit(1)
