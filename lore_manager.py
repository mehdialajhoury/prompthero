import json
import random
import os

class LoreManager:
    def __init__(self):
        self.bestiary = {}
        self.load_data()

    def load_data(self):
        # Chargement du Bestiaire
        try:
            with open(os.path.join("data", "bestiary.json"), "r", encoding="utf-8") as f:
                self.bestiary = json.load(f)
            print(f"📚 LoreManager : {len(self.bestiary)} monstres chargés.")
        except FileNotFoundError:
            print("⚠️ ERREUR : Fichier data/bestiary.json introuvable !")
            self.bestiary = {}

    def get_random_enemy(self):
        if not self.bestiary:
            # Fallback de secours si le fichier est vide/absent
            return {
                "name": "Ombre Générique",
                "hp": 30,
                "damage": 5,
                "desc": "Une forme sombre et indéfinie.",
                "visual_prompt": "dark shadowy figure, undefined monster, smoke form"
            }
        
        # On choisit une clé au hasard (ex: "rat_geant")
        key = random.choice(list(self.bestiary.keys()))
        return self.bestiary[key]