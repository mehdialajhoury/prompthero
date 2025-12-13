import random
import json
import settings
from prompts import SYSTEM_PROMPT, format_player_action

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
        # On charge le prompt JSON depuis le fichier externe
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]

    # --- AUTO-DÉTECTION DU MODE VISUEL ---
    def detect_scene_mode(self, client, model, text):
        check_prompt = """
        Analyse ce texte. Décrit-il l'apparition d'une AUTRE entité vivante (monstre, PNJ) ?
        Si OUI -> Réponds "CHARACTER". Si NON -> Réponds "SCENERY".
        Réponds uniquement par le mot-clé.
        """
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": check_prompt}, {"role": "user", "content": text}],
                temperature=0.1, max_tokens=10
            )
            result = response.choices[0].message.content.strip().upper()
            return "character" if "CHARACTER" in result else "scenery"
        except:
            return "scenery"

    # --- NOUVELLE FONCTION PRINCIPALE (Retourne JSON + Image) ---
    def process_game_turn(self, client, model, user_input, player_obj, system_instruction=None, generate_image=True, game_mode=None):
        
        # 1. Préparation du prompt via prompts.py
        user_content = format_player_action(user_input, player_obj.hp, player_obj.inventory, system_instruction)
        self.history.append({"role": "user", "content": user_content})

        # 2. Appel LLM en MODE JSON
        game_data = {}
        try:
            response = client.chat.completions.create(
                model=model,
                messages=self.history,
                temperature=0.7,
                max_tokens=1000,
                response_format={"type": "json_object"} # Force le JSON
            )
            json_str = response.choices[0].message.content
            game_data = json.loads(json_str) # Conversion texte -> Dict Python
            
            # On ajoute le JSON brut à l'historique pour garder le contexte
            self.history.append({"role": "assistant", "content": json_str})

        except Exception as e:
            print(f"Erreur JSON : {e}")
            # Fallback de sécurité
            game_data = {
                "narrative": f"Une confusion trouble vos sens... (Erreur : {e})",
                "hp_change": 0,
                "inventory_add": [],
                "inventory_remove": [],
                "game_state": "exploration"
            }

        # 3. Nettoyage et Extraction Narrative
        narrative_text = game_data.get("narrative", "")
        
        # Correctif Anti-Hallucination
        replacements = {"coldre": "froid", "dispay": "disparu"}
        for wrong, good in replacements.items():
            narrative_text = narrative_text.replace(wrong, good)
        game_data["narrative"] = narrative_text

        # 4. Génération de l'IMAGE
        image_bytes = None
        if generate_image:
            try:
                if game_mode:
                    current_mode = game_mode
                else:
                    current_mode = self.detect_scene_mode(client, model, narrative_text)
                
                print(f"Analyse Scène : {current_mode.upper()}")
                
                english_prompt = self.create_visual_prompt(client, model, narrative_text[:400], mode=current_mode)
                print(f"Prompt ({current_mode}) : {english_prompt}")
                
                image_bytes = generate_image_rtx(english_prompt, mode=current_mode)
            except Exception as e:
                print(f"Erreur Image : {e}")

        return game_data, image_bytes

    def spawn_enemy(self, client, model):
        prompt_generation = """
        [MOTEUR DE JEU] Analyse le DERNIER LIEU. Invente un ennemi logique.
        Réponds UNIQUEMENT JSON : 
        {
            "name": "Nom (Français)", 
            "hp": int(20-60), 
            "damage": int(4-10), 
            "desc": "Description PHYSIQUE visuelle précise (ex: un squelette en armure rouillée)"
        }
        """
        temp_msgs = self.history + [{"role": "user", "content": prompt_generation}]
        
        enemy_data = {"name": "Rat", "hp": 20, "damage": 4, "desc": "un rat géant aux yeux rouges"} 
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=temp_msgs,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            enemy_data = json.loads(response.choices[0].message.content)
            
            # Image de l'ennemi
            description_monstre = f"{enemy_data['name']}, {enemy_data['desc']}"
            print(f"Génération illustration monstre ({enemy_data['name']})...")
            
            english_prompt = self.create_visual_prompt(client, model, description_monstre, mode="character")
            enemy_image = generate_image_rtx(english_prompt, mode="character")
            
            if enemy_image:
                enemy_data["image"] = enemy_image
            
        except Exception as e:
            print(f"Erreur JSON monstre: {e}")

        return enemy_data
    
    def create_visual_prompt(self, client, model, narrative_fr, mode="scenery"):
        
        if mode == "scenery":
            role_description = "Tu es directeur artistique Dark Fantasy."
            constraints = """
            3. Règle d'or : INTERDICTION ABSOLUE de mentionner des personnages. Décris un lieu inanimé.
            4. Focalise-toi sur : l'ambiance colorée (lueur rouge, ténèbres bleutées), les textures.
            """
            context_prefix = "Description d'un LIEU VIDE : "
            fallback_prompt = "dark dungeon, ominous red lighting, oil painting style, detailed environment"
            
        elif mode == "character":
            role_description = "Tu es illustrateur de couverture de roman Dark Fantasy."
            constraints = """
            3. Règle d'or : Décris UNIQUEMENT le sujet principal.
            4. Mentionne les couleurs dominantes (armure noire, cape rouge, yeux verts).
            5. Si anomalie (sans tête), utilise la syntaxe (headless:1.5).
            """
            context_prefix = "Description physique du SUJET PRINCIPAL : "
            fallback_prompt = "dark fantasy warrior, red cape, glowing eyes, masterpiece illustration"

        system_prompt = f"""
        {role_description}
        TA MISSION : Traduis le texte français en une description visuelle ANGLAISE pour une illustration couleur style "Graphic Novel".
        
        RÈGLES IMPÉRATIVES :
        1. Réponds UNIQUEMENT avec les mots-clés descriptifs anglais.
        2. Style visuel : "Dark Fantasy Art", "Graphic Novel", "Oil Painting", "Grimdark".
        3. N'utilise PLUS "sepia" ou "ink drawing". Utilise des termes de couleur et de lumière.
        {constraints}
        """
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{context_prefix}{narrative_fr}"}
                ],
                temperature=0.3, 
                max_tokens=120
            )
            content = response.choices[0].message.content.strip()
            
            # SÉCURITÉ ANTI-REFUS
            refusal_keywords = ["je m'excuse", "je ne peux pas", "i cannot", "apologize", "unable", "désolé"]
            if any(keyword in content.lower() for keyword in refusal_keywords):
                print(f"⚠️ ALERTE : Refus IA. Fallback.")
                return fallback_prompt
            
            return content
            
        except Exception as e:
            print(f"Erreur Traduction Prompt : {e}")
            return fallback_prompt