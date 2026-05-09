"""
voxgaming_scraper.py
--------------------
Scraper pour https://www.voxgaming.fr (boutique gaming FR).

Site statique → requests + BeautifulSoup.
robots.txt vérifié : /catalog autorisé.

Structure HTML observée :
    a.product-category-card        → carte d'un produit (le <a> est la carte)
        .product-name              → titre
        span.list-price            → prix
        .card-footer               → contient la plateforme
        img                        → image
        href de l'a                → lien (peut être relatif)

Spécificité : la page 1 a une URL différente (sans le paramètre ?page=).

Le listing ne fournit pas de note / nb_avis / date / dispo explicite → "N/A".
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


SOURCE = "VoxGaming"
BASE_DOMAIN = "https://www.voxgaming.fr"
PAGE_1_URL = BASE_DOMAIN + "/catalog/xbox-one/"
PAGE_N_URL = BASE_DOMAIN + "/catalog/xbox-one/?page={}"
NB_PAGES = 5
DELAY_BETWEEN_PAGES = 10


def url_for_page(n):
    """Page 1 a une URL spéciale, les autres suivent le pattern ?page=N."""
    return PAGE_1_URL if n == 1 else PAGE_N_URL.format(n)


def parse_card(card, numero_page):
    """Extrait un dict de données depuis un <a class="product-category-card">."""

    # TITRE
    titre_tag = card.find("div", class_="product-name")
    titre = clean(titre_tag.text) if titre_tag else "N/A"

    # PRIX
    prix_tag = card.find("span", class_="list-price")
    prix = clean(prix_tag.text) if prix_tag else "N/A"

    # PLATEFORME — extrait depuis le card-footer
    plat_tag = card.find("div", class_="card-footer")
    plateforme = clean(plat_tag.text) if plat_tag else "N/A"

    # IMAGE — VoxGaming utilise des placeholders base64 inline pour le lazy
    # loading. pick_image_url les rejette et privilégie data-src.
    image = pick_image_url(card.find("img"))

    # LIEN — `card` est lui-même le <a>
    href = card.get("href")
    if href:
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
        "note": "N/A",
        "nombre_avis": "N/A",
        "date": "N/A",
        "disponibilite": "N/A",
    }


def run():
    ensure_csv_exists()
    total = 0

    for numero_page in range(1, NB_PAGES + 1):
        url = url_for_page(numero_page)
        print(f"\n[{SOURCE}] Page {numero_page}/{NB_PAGES} → {url}")

        response = fetch(url)
        if response is None or response.status_code != 200:
            print(f"  Échec page {numero_page} — on passe")
            time.sleep(DELAY_BETWEEN_PAGES)
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.find_all("a", class_="product-category-card")
        print(f"  Jeux trouvés : {len(cards)}")

        rows = [parse_card(c, numero_page) for c in cards]
        n = append_rows(rows)
        total += n
        print(f"  {n} lignes écrites (cumul : {total})")

        time.sleep(DELAY_BETWEEN_PAGES)

    return total


if __name__ == "__main__":
    print(f"=== {SOURCE} (standalone) ===")
    n = run()
    print(f"\nTotal : {n} lignes ajoutées à jeu.csv")
