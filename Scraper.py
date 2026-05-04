import requests
from bs4 import BeautifulSoup
import csv
import time

BASE_URL = "https://www.retroplace.com/fr/jeux/marketplace?system_short=ps5&page={}"
NB_PAGES = 5

headers = {
    "User-Agent": "Mozilla/5.0"
}



with open("jeu.csv", "w", newline="", encoding="utf-8") as fichier:
    writer = csv.writer(fichier)
    writer.writerow(["titre", "plateforme", "image", "lien"])
    
    for numero_page in range(1, NB_PAGES + 1):
        url = BASE_URL.format(numero_page)
        print(f"Scraping page {numero_page}...")
        
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.find_all("div", class_="item-card")



        for jeu in cards:

    
            titre_tag = jeu.find("div", class_="item-title")
            titre = titre_tag.text.strip() if titre_tag else "N/A"

    
            plateforme_tag = jeu.find("div", class_="item-system")
            plateforme = plateforme_tag.text.strip() if plateforme_tag else "N/A"

    
            img_tag = jeu.find("img")
            image = img_tag.get("src") or img_tag.get("data-src") if img_tag else "N/A"

    
            link_tag = jeu.find("a", class_="item-link")
            lien = "https://www.retroplace.com" + link_tag["href"] if link_tag else "N/A"
        
            writer.writerow([titre, plateforme, image, lien])
            
        time.sleep(1)    
        

        

        
    