import json
import os

# Le chemin change un peu car on est dans src/utils/
# On veut sauvegarder à la racine du projet
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAVE_FILE = os.path.join(BASE_DIR, "data", "savegame.json")

class SaveManager:
    @staticmethod
    def save_game(player, game_state, messages):
        """Sauvegarde l'état complet dans un fichier JSON"""
        
        # 1. On sérialise le Joueur
        player_data = {
            "name": player.name,
            "hp": player.hp,
            "inventory": player.inventory
        }
        
        # 2. On sérialise l'État du Jeu

        clean_enemy = None
        if game_state.current_enemy:
            clean_enemy = game_state.current_enemy.copy() # Copie pour ne pas modifier l'original
            if "image" in clean_enemy:
                del clean_enemy["image"] # On supprime les données binaires de l'image
        
        game_data = {
            "turns_since_last_fight": game_state.turns_since_last_fight,
            "in_combat": game_state.in_combat,
            "current_enemy": clean_enemy 
        }
        
        # 3. On sérialise l'Historique
        messages_data = []
        for msg in messages:
            clean_msg = {
                "role": msg["role"],
                "content": msg["content"],
                "caption": msg.get("caption"), # On garde la légende
                # On ne sauvegarde PAS l'image
                "has_image": "image" in msg and msg["image"] is not None 
            }
            messages_data.append(clean_msg)
            
        # 4. On écrit le tout
        full_save = {
            "player": player_data,
            "game": game_data,
            "messages": messages_data
        }
        
        try:
            # On s'assure que le dossier data existe
            os.makedirs(os.path.dirname(SAVE_FILE), exist_ok=True)
            
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(full_save, f, indent=4, ensure_ascii=False)
            return True, "Sauvegarde réussie !"
        except Exception as e:
            return False, f"Erreur de sauvegarde : {e}"

    @staticmethod
    def load_game():
        """Charge le fichier JSON et retourne les données"""
        if not os.path.exists(SAVE_FILE):
            return None, "Aucun fichier de sauvegarde trouvé."
            
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data, "Chargement réussi !"
        except Exception as e:
            return None, f"Fichier corrompu : {e}"