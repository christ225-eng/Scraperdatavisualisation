"""
gameinpocket_scraper.py
-----------------------
Scraper pour https://www.gameinpocket.com (portail de jeux HTML5 jouables
en navigateur — gaming, mais modèle freemium et non e-commerce stricto sensu).

Site statique → requests + BeautifulSoup.
robots.txt vérifié : aucune restriction (User-agent: * / Disallow: ).

Structure HTML observée :

    <li class="detail_li">
        <a href="https://www.gameinpocket.com/detail/<Game_Name>.html">
            <img class="lazyLoad" data-src="https://img.gamemonetize.com/.../512x384.jpg">
        </a>
        <div class="mengceng">
            <p>Game Name</p>
        </div>
    </li>

Le site n'a pas de pagination classique : la home liste un grand nombre de
jeux sur une seule page. On scrape donc :
    - page 1 : la home
    - page 2 et suivantes : les pages "label" (catégories) qui ont la même
      structure HTML.

Champs récupérables : titre, image, lien.
Tous les autres champs (prix, plateforme, note, etc.) sont N/A
(prix = "Gratuit", plateforme = "HTML5/Web" sont fixés sémantiquement).
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


SOURCE = "GameInPocket"
BASE_DOMAIN = "https://www.gameinpocket.com"

# Chaque entrée = une "page" (au sens du CSV) à scraper.
# La home contient le plus gros catalogue ; les pages label ajoutent des
# jeux thématiques avec la même structure HTML.
PAGES = [
    BASE_DOMAIN + "/",
    BASE_DOMAIN + "/label",
]
DELAY_BETWEEN_PAGES = 5


def parse_card(li, numero_page):
    """Extrait un dict depuis un <li class="detail_li">."""

    # LIEN — premier <a> dans le <li>
    a_tag = li.find("a")
    if a_tag and a_tag.get("href"):
        href = a_tag["href"]
        lien = href if href.startswith("http") else BASE_DOMAIN + href
    else:
        lien = "N/A"

    # TITRE — dans <div class="mengceng"><p>...</p></div>
    title_tag = li.find("div", class_="mengceng")
    if title_tag:
        # le <p> peut être absent, on prend le texte du div en fallback
        p = title_tag.find("p")
        titre = clean(p.text if p else title_tag.text)
    else:
        titre = "N/A"

    # IMAGE — lazy loading via class="lazyLoad" et data-src
    image = pick_image_url(li.find("img"))

    return {
        "titre": titre,
        # Modèle économique du site : tous les jeux sont jouables gratuitement
        "prix": "Gratuit",
        # Tous les jeux du portail tournent en HTML5 dans le navigateur
        "plateforme": "HTML5/Web",
        "image": image,
        "lien": lien,
        "page": numero_page,
        "source": SOURCE,
        "note": "N/A",
        "nombre_avis": "N/A",
        "date": "N/A",
        # Si le jeu apparaît dans le listing, il est jouable
        "disponibilite": "Disponible",
    }


def run():
    ensure_csv_exists()
    total = 0

    for numero_page, url in enumerate(PAGES, start=1):
        print(f"\n[{SOURCE}] Page {numero_page}/{len(PAGES)} → {url}")

        response = fetch(url)
        if response is None or response.status_code != 200:
            print(f"  Échec page {numero_page} — on passe")
            time.sleep(DELAY_BETWEEN_PAGES)
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.find_all("li", class_="detail_li")
        print(f"  Cartes brutes trouvées : {len(cards)}")

        # On filtre les cartes parasites (placeholders, bandeaux structurels)
        # qui n'ont pas de vrai lien produit ou pas de titre.
        rows = []
        for c in cards:
            row = parse_card(c, numero_page)
            if row["titre"] == "N/A":
                continue
            if "/detail/" not in row["lien"]:
                continue
            rows.append(row)
        print(f"  Jeux valides après filtrage : {len(rows)}")

        n = append_rows(rows)
        total += n
        print(f"  {n} lignes écrites (cumul : {total})")

        time.sleep(DELAY_BETWEEN_PAGES)

    return total


if __name__ == "__main__":
    print(f"=== {SOURCE} (standalone) ===")
    n = run()
    print(f"\nTotal : {n} lignes ajoutées à jeu.csv")
