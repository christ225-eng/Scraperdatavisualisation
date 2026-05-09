"""
main.py
-------
Orchestrateur des scrapers gaming.

Étapes :
1. (Re)crée jeu.csv avec uniquement la ligne d'en-tête.
2. Lance chaque scraper dans l'ordre. Chacun ajoute ses lignes au CSV.
3. À la fin, dédoublonne le CSV par (titre, source, plateforme).

Chaque scraper peut aussi être lancé seul :
    python pixelheart_scraper.py
Dans ce cas, il crée jeu.csv s'il n'existe pas, sinon append.

Usage :
    python main.py
"""

import time

from csv_utils import reset_csv, deduplicate, CSV_PATH

# Import de chaque scraper. Chaque module doit exposer une fonction `run()`
# qui scrape ses pages et retourne le nombre de lignes ajoutées au CSV.
import retroplace_scraper
import voxgaming_scraper
import pixelheart_scraper
import dlcompare_scraper
import gameinpocket_scraper


# Liste ordonnée des scrapers à exécuter.
# Format : (nom_affiché, fonction_run)
SCRAPERS = [
    ("Retroplace",   retroplace_scraper.run),
    ("VoxGaming",    voxgaming_scraper.run),
    ("PixelHeart",   pixelheart_scraper.run),
    ("DLCompare",    dlcompare_scraper.run),
    ("GameInPocket", gameinpocket_scraper.run),
]


def main():
    print("=" * 60)
    print("ORCHESTRATEUR — Scrapers Gaming")
    print("=" * 60)

    # 1) Reset du CSV. À ce stade le fichier ne contient que les headers.
    reset_csv()
    print(f"\n[init] CSV initialisé : {CSV_PATH}\n")

    # 2) Exécution séquentielle des scrapers.
    total_brut = 0
    for nom, run_fn in SCRAPERS:
        print(f"\n{'=' * 60}")
        print(f"[{nom}] démarrage")
        print("=" * 60)
        start = time.time()
        try:
            n = run_fn()
            total_brut += n
            duree = time.time() - start
            print(f"\n[{nom}] OK : {n} lignes en {duree:.1f}s")
        except Exception as e:
            print(f"\n[{nom}] ERREUR fatale : {e}")
            # On continue avec le scraper suivant pour ne pas tout perdre
            continue

    # 3) Dédoublonnage final.
    print(f"\n{'=' * 60}")
    print("[finalisation] Dédoublonnage")
    print("=" * 60)
    removed = deduplicate()
    print(f"  Doublons supprimés : {removed}")

    print(f"\n{'=' * 60}")
    print(f"TERMINÉ — {total_brut - removed} lignes finales dans {CSV_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
