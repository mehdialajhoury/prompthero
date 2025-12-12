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

    # Retourne un tuple (texte, image_bytes)
    def generate_story(self, client, model, user_input, system_instruction=None, max_tokens=500, generate_image=True):
        full_content = user_input
        if system_instruction:
            full_content += f"\n\n[INSTRUCTION SYSTÈME IMPÉRATIVE] : {system_instruction}"
        
        self.history.append({"role": "user", "content": full_content})

        # 1. Génération du TEXTE
        narrative = "..."
        try:
            response = client.chat.completions.create(
                model=model,
                messages=self.history,
                temperature=0.7,
                max_tokens=max_tokens 
            )
            narrative = response.choices[0].message.content
            self.history.append({"role": "assistant", "content": narrative})
        except Exception as e:
            return f"Erreur IA : {e}", None

        # 2. Génération de l'IMAGE
        image_bytes = None
        if generate_image:
            try:
                # Traduction du prompt en anglais
                print("Traduction du prompt visuel...")
                
                # On ne traduit que les 300 premiers caractères pour aller vite
                english_prompt = self.create_visual_prompt(client, model, narrative[:300])
                
                print(f"Prompt envoyé au GPU : {english_prompt}")
                
                # On envoie ce prompt anglais propre au GPU
                image_bytes = generate_image_rtx(english_prompt)
                # ------------------------
            except Exception as e:
                print(f"Erreur Image : {e}")

        return narrative, image_bytes

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

        return enemy_data
    
        # Fonction de traduction du prompt pour la génération visuelle
    def create_visual_prompt(self, client, model, narrative_fr):
        system_prompt = """
        Tu es un expert en Prompt Engineering pour Stable Diffusion.
        TA MISSION : Traduis le texte français fourni en une description visuelle courte et percutante en ANGLAIS.
        RÈGLES :
        1. Réponds UNIQUEMENT avec la description en anglais.
        2. Sois descriptif : mentionne l'éclairage, les objets, l'ambiance.
        3. Ajoute des mots clés de style : "pixel art, dark atmosphere".
        4. Ne mets pas de phrases comme "Here is the prompt", juste les mots-clés.
        """
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Description: {narrative_fr}"}
                ],
                temperature=0.3, # Température basse pour être précis
                max_tokens=100
            )
            return response.choices[0].message.content
        except:
            return "pixel art, dungeon, dark atmosphere" # Fallback au cas où