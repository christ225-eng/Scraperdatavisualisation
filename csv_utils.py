"""
csv_utils.py
------------
Helpers partagés par tous les scrapers :
- gestion du CSV unique `jeu.csv` (headers, append, dedup)
- requête HTTP robuste (timeout, retries, anti-bot soft)
- nettoyage texte

Toutes les fonctions ici sont *pures* : pas de scraping, juste de l'I/O CSV
et du HTTP. Ça permet à chaque scraper de rester très court et lisible.
"""

import csv
import os
import sys
import time

import requests


# Force la sortie console en UTF-8. Sous Windows, stdout est par défaut en
# cp1252 qui ne supporte pas certains caractères (→, →, etc.) et fait planter
# tout print() qui en contient.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# Colonnes obligatoires du CSV (ordre garanti)
COLUMNS = [
    "titre",
    "prix",
    "plateforme",
    "image",
    "lien",
    "page",
    "source",
    "note",
    "nombre_avis",
    "date",
    "disponibilite",
]

# Chemin du CSV partagé
CSV_PATH = "jeu.csv"

# Headers HTTP par défaut. Un User-Agent réaliste réduit le risque d'être
# bloqué par les protections anti-bot basiques.
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/webp,*/*;q=0.8"
    ),
}


def reset_csv(path=CSV_PATH):
    """
    (Re)crée le CSV avec uniquement la ligne d'en-tête.
    À appeler une seule fois au début, depuis main.py.
    """
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(COLUMNS)


def ensure_csv_exists(path=CSV_PATH):
    """
    Si le CSV n'existe pas encore, le crée avec les headers.
    Permet à chaque scraper de tourner aussi en standalone.
    """
    if not os.path.exists(path):
        reset_csv(path)


def append_rows(rows, path=CSV_PATH):
    """
    Ajoute des lignes au CSV en mode append.

    `rows` est un itérable de dict. Chaque dict doit contenir au plus les clés
    de COLUMNS ; toute clé absente sera remplacée par "N/A".

    Retourne le nombre de lignes écrites.
    """
    count = 0
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow([
                _safe(row.get(col)) for col in COLUMNS
            ])
            count += 1
    return count


def deduplicate(path=CSV_PATH):
    """
    Supprime les doublons en place. Clé d'unicité : (titre, source, plateforme).
    Retourne le nombre de doublons supprimés.
    """
    if not os.path.exists(path):
        return 0

    with open(path, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    if len(rows) < 2:
        return 0

    header = rows[0]
    data = rows[1:]

    # Index des colonnes utilisées comme clé d'unicité
    i_titre = header.index("titre")
    i_src = header.index("source")
    i_plat = header.index("plateforme")

    seen = set()
    unique = []
    for r in data:
        key = (r[i_titre], r[i_src], r[i_plat])
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)

    removed = len(data) - len(unique)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(unique)

    return removed


def fetch(url, max_retries=3, backoff=5.0, headers=None):
    """
    GET HTTP robuste :
    - timeout 30s
    - retries sur erreur réseau, 429 (rate limit) et 503
    - backoff linéaire entre tentatives

    Retourne l'objet Response (succès ou échec non récupérable),
    ou None si toutes les tentatives ont échoué.
    """
    if headers is None:
        headers = DEFAULT_HEADERS

    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(url, headers=headers, timeout=30)
            print(f"  Status code : {r.status_code}")

            # 200 : tout va bien
            if r.status_code == 200:
                return r

            # 404 : la page n'existe pas, inutile de retenter
            if r.status_code == 404:
                print(f"  404 — page inexistante, on passe")
                return r

            # 429 / 503 : on attend plus longtemps puis on retente
            if r.status_code in (429, 503):
                wait = backoff * attempt
                print(f"  Rate limit / blocage temporaire — attente {wait}s")
                time.sleep(wait)
                continue

            # Autres codes : on retourne tel quel (le caller décide)
            return r

        except requests.exceptions.Timeout:
            print(f"  Timeout (essai {attempt}/{max_retries})")
        except requests.exceptions.RequestException as e:
            print(f"  Erreur requête : {e}")

        time.sleep(backoff)

    return None


def clean(text):
    """
    Nettoie un texte :
    - None ou vide → "N/A"
    - strip + espaces multiples → un seul espace
    """
    if text is None:
        return "N/A"
    s = " ".join(str(text).split())
    return s if s else "N/A"


def clean_price(text):
    """
    Garde uniquement la première valeur numérique + symbole monétaire.
    Ex: "  À partir de 38.40 € TTC " -> "38.40 €"
    """
    if not text:
        return "N/A"
    s = " ".join(str(text).split())
    return s if s else "N/A"


def pick_image_url(img_tag):
    """
    Choisit la meilleure URL d'image depuis un tag <img>.

    Priorité : data-src > data-original > data-lazy-src > src.
    Rejette toute valeur qui commence par "data:" (placeholder base64
    inline utilisé par les sites avec lazy loading) — ces URIs peuvent
    peser plusieurs dizaines de Ko et exploseraient la taille du CSV.
    """
    if img_tag is None:
        return "N/A"

    for attr in ("data-src", "data-original", "data-lazy-src", "src"):
        value = img_tag.get(attr)
        if value and not value.startswith("data:"):
            return value
    return "N/A"


def _safe(value):
    """
    Remplace None et "" par "N/A" lors de l'écriture CSV.
    """
    if value is None:
        return "N/A"
    s = str(value).strip()
    return s if s else "N/A"
