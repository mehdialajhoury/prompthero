import random
import json
import settings

# Import de la génération d'image
from image_client import generate_image_rtx

# ------------------------------------------------------------------
# CLASSES DU JEU
# ------------------------------------------------------------------
class Player:
    def __init__(self, name):
        self.name = name
        self.hp = 100
        self.inventory = ["Une vieille épée", "Une torche"] 
    
    def get_weapon_damage(self, weapon_name):
        stats = settings.WEAPONS_STATS.get(weapon_name, settings.WEAPONS_STATS["Mains nues"])
        return random.randint(stats["min"], stats["max"])

class GameState:
    def __init__(self):
        self.turns_since_last_fight = 0
        self.in_combat = False
        self.current_enemy = None

class DungeonMasterAI:
    def __init__(self):
        self.system_prompt = """
        Tu es le Maître du Donjon. Règles : BRIÈVETÉ (max 3 phrases), RYTHME, 
        ne joue pas à la place du joueur, n'invente pas de loot, finis tes phrases.
        """
        self.history = [{"role": "system", "content": self.system_prompt}]

    def generate_story(self, client, model, user_input, system_instruction=None, max_tokens=500):
        full_content = user_input
        if system_instruction:
            full_content += f"\n\n[INSTRUCTION SYSTÈME IMPÉRATIVE] : {system_instruction}"
        
        self.history.append({"role": "user", "content": full_content})

        try:
            response = client.chat.completions.create(
                model=model,
                messages=self.history,
                temperature=0.7,
                max_tokens=max_tokens 
            )
            narrative = response.choices[0].message.content
            self.history.append({"role": "assistant", "content": narrative})
            return narrative
        except Exception as e:
            return f"Erreur IA : {e}"

    def spawn_enemy(self, client, model):
        prompt_generation = """
        [MOTEUR DE JEU] Analyse le DERNIER LIEU. Invente un ennemi logique.
        Réponds UNIQUEMENT JSON : {"name": "Nom", "hp": int(20-60), "damage": int(4-10), "desc": "courte desc"}
        """
        temp_msgs = self.history + [{"role": "user", "content": prompt_generation}]
        
        enemy_data = {"name": "Rat", "hp": 20, "damage": 4, "desc": "agressif"} # Valeur par défaut
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=temp_msgs,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            enemy_data = json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Erreur JSON monstre: {e}")

        # --- GÉNÉRATION D'IMAGE ---
        # Description visuelle
        description_visuelle = f"monster, {enemy_data['name']}, {enemy_data['desc']}, dungeon background, fantasy rpg, pixel art"
        
        # On appelle le GPU
        print("Demande image au serveur...")
        image_bytes = generate_image_rtx(description_visuelle)
        
        # On stocke l'image DANS le dictionnaire de l'ennemi
        if image_bytes:
            enemy_data["image"] = image_bytes
        # ------------------------------------

        return enemy_data