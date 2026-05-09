"""
dlcompare_scraper.py
--------------------
Scraper pour https://www.dlcompare.fr (comparateur de prix de jeux dématérialisés).

Site statique → requests + BeautifulSoup.
robots.txt vérifié : seul /teleport/ est bloqué. /jeux est autorisé.

Structure HTML observée :

    <a class="game-list-item" href="..."
       title="Comparer et acheter Forza Horizon 6 sur PC,PS5,Xbox Series X">
        <img class="catalog-img clickable" src="..." alt="Forza Horizon 6">
        <div class="catalog-game-name">
            <div class="name-block">
                <span class="name clickable">Forza Horizon 6</span>
                <span class="pre-order">Date de sortie: 18/05/2026</span>
            </div>
        </div>
        <span class="catalog-game-support">
            <i class="pli pli-pc-12" title="Comparer et acheter ... sur PC"></i>
        </span>
        ...
        <div class="catalog-price">
            <span class="price">38.40</span>
            <span class="currency">€</span>
        </div>
    </a>

Champs récupérables :
- titre : <span class="name clickable">
- prix : <span class="price"> + <span class="currency">
- plateforme : extraite de l'attribut title du <a> (après "sur ...")
- image : <img class="catalog-img">
- lien : href du <a>
- date : <span class="pre-order"> (présent uniquement si pré-commande)
- disponibilite : "Précommande" si .pre-order présent, sinon "Disponible"
- note, nombre_avis : non exposés sur le listing → "N/A"

URL pattern : ?page=N
"""

import re
import time

from bs4 import BeautifulSoup

from csv_utils import (
    append_rows,
    clean,
    ensure_csv_exists,
    fetch,
    pick_image_url,
)


SOURCE = "DLCompare"
BASE_URL = "https://www.dlcompare.fr/jeux?page={}"
NB_PAGES = 5
DELAY_BETWEEN_PAGES = 8


# Regex pour extraire les plateformes depuis le title du <a> :
# "Comparer et acheter <jeu> sur PC,PS5,Xbox Series X"
PLATFORM_RE = re.compile(r"\bsur\s+(.+?)\s*$")

# Regex pour extraire la date depuis "Date de sortie: 18/05/2026"
DATE_RE = re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}")


def extract_platforms_from_title(a_title):
    """
    Récupère la liste des plateformes depuis l'attribut title du <a>.
    Retourne une chaîne séparée par virgules, ou "N/A".
    """
    if not a_title:
        return "N/A"
    m = PLATFORM_RE.search(a_title)
    if not m:
        return "N/A"
    plats = [p.strip() for p in m.group(1).split(",") if p.strip()]
    return ", ".join(plats) if plats else "N/A"


def parse_card(card, numero_page):
    """Extrait un dict depuis un <a class="game-list-item">."""

    # TITRE
    name_tag = card.find("span", class_="name")
    titre = clean(name_tag.text) if name_tag else "N/A"

    # PRIX (chiffre + devise)
    prix_tag = card.find("div", class_="catalog-price")
    if prix_tag:
        # Concatène le prix et la devise en un texte propre
        prix_value = prix_tag.find("span", class_="price")
        currency = prix_tag.find("span", class_="currency")
        if prix_value:
            value = clean(prix_value.text)
            cur = clean(currency.text) if currency else ""
            prix = f"{value} {cur}".strip() if cur != "N/A" else value
        else:
            prix = "N/A"
    else:
        prix = "N/A"

    # PLATEFORME — depuis l'attribut title du <a> (plus fiable que les <i>)
    plateforme = extract_platforms_from_title(card.get("title", ""))

    # IMAGE — DLCompare a une .catalog-img dédiée mais on garde un fallback
    img_tag = card.find("img", class_="catalog-img") or card.find("img")
    image = pick_image_url(img_tag)

    # LIEN — directement le href du <a>
    href = card.get("href")
    lien = href if href else "N/A"

    # DATE + DISPONIBILITÉ — si le span.pre-order est présent c'est une pré-co
    pre_tag = card.find("span", class_="pre-order")
    if pre_tag:
        text = pre_tag.text
        m = DATE_RE.search(text)
        date = m.group(0) if m else clean(text)
        disponibilite = "Précommande"
    else:
        date = "N/A"
        # Si le jeu apparaît sur DLCompare avec un prix, on considère qu'il est
        # disponible chez au moins un revendeur. Sinon on laisse N/A.
        disponibilite = "Disponible" if prix != "N/A" else "N/A"

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
        "date": date,
        "disponibilite": disponibilite,
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
        cards = soup.find_all("a", class_="game-list-item")
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
