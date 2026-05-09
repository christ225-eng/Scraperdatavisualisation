"""
retroplace_scraper.py
---------------------
Scraper pour https://www.retroplace.com (marketplace de jeux d'occasion).

Site statique → requests + BeautifulSoup suffisent.
robots.txt vérifié : /fr/jeux/marketplace est autorisé.

Structure HTML observée :
    .item-card           → carte d'un jeu
        .item-title      → titre
        .price           → prix (souvent absent sur les listings → N/A)
        .item-system     → plateforme
        img              → image (src ou data-src)
        a.item-link      → lien vers la fiche

Le listing ne fournit pas de note, ni de nombre d'avis, ni de date,
ni de disponibilité explicite → ces colonnes valent "N/A".
"""

import time

from bs4 import BeautifulSoup

from csv_utils import (
    append_rows,
    clean,
    ensure_csv_exists,
    fetch,
    pick_image_url,
)


SOURCE = "Retroplace"
BASE_DOMAIN = "https://www.retroplace.com"
BASE_URL = BASE_DOMAIN + "/fr/jeux/marketplace?system_short=ps5&page={}"
NB_PAGES = 5
DELAY_BETWEEN_PAGES = 10  # secondes


def parse_card(card, numero_page):
    """
    Extrait les données d'une carte produit (div.item-card)
    et retourne un dict prêt à être écrit dans le CSV.
    """

    # TITRE
    titre_tag = card.find("div", class_="item-title")
    titre = clean(titre_tag.text) if titre_tag else "N/A"

    # PRIX
    prix_tag = card.find("div", class_="price")
    prix = clean(prix_tag.get_text(" ", strip=True)) if prix_tag else "N/A"

    # PLATEFORME
    plat_tag = card.find("div", class_="item-system")
    plateforme = clean(plat_tag.text) if plat_tag else "N/A"

    # IMAGE — pick_image_url gère le lazy loading et rejette les
    # placeholders base64 inline.
    image = pick_image_url(card.find("img"))

    # LIEN — relatif → on préfixe le domaine
    link_tag = card.find("a", class_="item-link")
    if link_tag and link_tag.get("href"):
        href = link_tag["href"]
        lien = href if href.startswith("http") else BASE_DOMAIN + href
    else:
        lien = "N/A"

    return {
        "titre": titre,
        "prix": prix,
        "plateforme": plateforme,
        "image": image,
        "lien": lien,
        "page": numero_page,
        "source": SOURCE,
        # Champs non disponibles sur le listing Retroplace
        "note": "N/A",
        "nombre_avis": "N/A",
        "date": "N/A",
        "disponibilite": "N/A",
    }


def run():
    """
    Lance le scraping et retourne le nombre total de lignes ajoutées au CSV.
    """
    ensure_csv_exists()
    total = 0

    for numero_page in range(1, NB_PAGES + 1):
        url = BASE_URL.format(numero_page)
        print(f"\n[{SOURCE}] Page {numero_page}/{NB_PAGES} → {url}")

        response = fetch(url)
        if response is None or response.status_code != 200:
            print(f"  Échec page {numero_page} — on passe")
            time.sleep(DELAY_BETWEEN_PAGES)
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.find_all("div", class_="item-card")
        print(f"  Jeux trouvés : {len(cards)}")

        rows = [parse_card(c, numero_page) for c in cards]
        n = append_rows(rows)
        total += n
        print(f"  {n} lignes écrites (cumul : {total})")

        # Pause entre pages — anti-bot et politesse serveur
        time.sleep(DELAY_BETWEEN_PAGES)

    return total


if __name__ == "__main__":
    print(f"=== {SOURCE} (standalone) ===")
    n = run()
    print(f"\nTotal : {n} lignes ajoutées à jeu.csv")
