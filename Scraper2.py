import requests
from bs4 import BeautifulSoup
import csv
import time

BASE_URL = "https://www.voxgaming.fr/catalog/xbox-one/page/{}/"
NB_PAGES = 5

headers = {
    "User-Agent": "Mozilla/5.0"
}

with open("jeu.csv", "w", newline="", encoding="utf-8") as fichier:
    writer = csv.writer(fichier)
    writer.writerow(["titre", "prix", "plateforme", "page"])

    for numero_page in range(1, NB_PAGES + 1):

        url = BASE_URL.format(numero_page)

        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        jeux = soup.find_all("a", class_="product-category-card")

        for jeu in jeux:

            titre_tag = jeu.find("div", class_="product-name")
            titre = titre_tag.text.strip() if titre_tag else "N/A"

            prix_tag = jeu.find("span", class_="list-price")
            prix = prix_tag.text.strip() if prix_tag else "N/A"

            plateforme_tag = jeu.find("div", class_="card-footer")
            plateforme = plateforme_tag.text.strip() if plateforme_tag else "N/A"

            writer.writerow([titre, prix, plateforme, numero_page])

        time.sleep(1)

print("CSV créé")