"""
pixelheart_scraper.py
---------------------
Scraper pour https://www.pixelheart.eu (boutique WooCommerce de jeux,
spécialisée éditions limitées rétro et néo-rétro).

Site statique → requests + BeautifulSoup.
robots.txt vérifié : seules les pages admin/cart sont bloquées.
La page boutique est explicitement scrapable.

Structure HTML observée (WooCommerce standard) :

    <li class="simple product type-product post-XXX status-publish first
              instock product_cat-playstation-4-fr ...">
        <a class="woocommerce-loop-product__link" href="...">
            <img ...>
            <h2 class="woocommerce-loop-product__title">Titre</h2>
            <span class="price">
                <span class="woocommerce-Price-amount amount">
                    <bdi>54,90<span class="woocommerce-Price-currencySymbol">€</span></bdi>
                </span>
            </span>
        </a>

Champs récupérables :
- titre, prix, image, lien : standard WooCommerce
- plateforme : déduite des classes `product_cat-XXX-fr` du <li>
- disponibilite : déduite des classes `instock` / `outofstock` / `onbackorder`
- note, nombre_avis, date : non exposés sur le listing → "N/A"

URL pattern : /boutique/page/N/
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


SOURCE = "PixelHeart"
BASE_URL = "https://www.pixelheart.eu/boutique/page/{}/"
NB_PAGES = 5
DELAY_BETWEEN_PAGES = 8


# Mapping slug WooCommerce → libellé plateforme propre.
# Les slugs viennent des classes CSS `product_cat-<slug>-fr` du <li>.
# Ordre = priorité : on prend le premier match. Donc on liste d'abord les slugs
# les plus longs/spécifiques (ex: "playstation-4" avant "playstation").
PLATFORM_SLUGS = [
    ("playstation-5",     "PlayStation 5"),
    ("playstation-4",     "PlayStation 4"),
    ("playstation-3",     "PlayStation 3"),
    ("playstation-2",     "PlayStation 2"),
    ("playstation-vita",  "PS Vita"),
    ("playstation",       "PlayStation"),
    ("xbox-series",       "Xbox Series"),
    ("xbox-one",          "Xbox One"),
    ("xbox-360",          "Xbox 360"),
    ("xbox",              "Xbox"),
    ("switch",            "Nintendo Switch"),
    ("nintendo-3ds",      "Nintendo 3DS"),
    ("nintendo-ds",       "Nintendo DS"),
    ("nintendo-64",       "Nintendo 64"),
    ("gamecube",          "GameCube"),
    ("dreamcast",         "Dreamcast"),
    ("saturn",            "Sega Saturn"),
    ("megadrive",         "Mega Drive"),
    ("mega-drive",        "Mega Drive"),
    ("master-system",     "Master System"),
    ("neo-geo",           "Neo Geo"),
    ("amiga",             "Amiga"),
    ("pc-engine",         "PC Engine"),
    ("turbografx",        "TurboGrafx"),
    ("game-boy",          "Game Boy"),
    ("snes",              "Super Nintendo"),
    ("nes",               "NES"),
    ("pc",                "PC"),
]


def extract_platform(li_classes):
    """
    Cherche la plateforme dans la liste des classes CSS du <li>.
    Les classes WooCommerce sont du type product_cat-<slug>-fr.
    Retourne le libellé propre ou "N/A" si rien ne matche.
    """
    cats = [
        c[len("product_cat-"):]
        for c in li_classes
        if c.startswith("product_cat-")
    ]
    for slug in cats:
        for key, label in PLATFORM_SLUGS:
            if key in slug:
                return label
    return "N/A"


def extract_availability(li_classes):
    """
    Déduit la disponibilité depuis les classes WooCommerce :
    - instock      → "Disponible"
    - outofstock   → "Rupture"
    - onbackorder  → "Précommande"
    Sinon "N/A".
    """
    if "outofstock" in li_classes:
        return "Rupture"
    if "onbackorder" in li_classes:
        return "Précommande"
    if "instock" in li_classes:
        return "Disponible"
    return "N/A"


def parse_card(li, numero_page):
    """
    Extrait les données d'un <li class="product ...">.
    Retourne un dict pour le CSV.
    """
    classes = li.get("class", [])

    # TITRE
    titre_tag = li.find("h2", class_="woocommerce-loop-product__title")
    titre = clean(titre_tag.text) if titre_tag else "N/A"

    # PRIX — on prend le premier .price (WooCommerce affiche parfois 2 prix
    # pour les produits en promo : prix barré + prix soldé).
    prix_tag = li.find("span", class_="price")
    prix = clean(prix_tag.get_text(" ", strip=True)) if prix_tag else "N/A"

    # IMAGE — WooCommerce a souvent un srcset ; pick_image_url priorise
    # data-src (lazy) puis src en fallback, en rejetant les data:URIs.
    image = pick_image_url(li.find("img"))

    # LIEN — l'<a> qui enveloppe la carte
    link_tag = li.find("a", class_="woocommerce-loop-product__link")
    if link_tag is None:
        link_tag = li.find("a")  # fallback plus permissif
    lien = link_tag["href"] if link_tag and link_tag.get("href") else "N/A"

    return {
        "titre": titre,
        "prix": prix,
        "plateforme": extract_platform(classes),
        "image": image,
        "lien": lien,
        "page": numero_page,
        "source": SOURCE,
        "note": "N/A",
        "nombre_avis": "N/A",
        "date": "N/A",
        "disponibilite": extract_availability(classes),
    }


def run():
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
        # Liste des produits : <li class="product ..."> dans <ul class="products">
        cards = soup.select("ul.products li.product")
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
