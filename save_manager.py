import json
import os

SAVE_FILE = "savegame.json"

class SaveManager:
    @staticmethod
    def save_game(player, game_state, messages):
        """Sauvegarde l'état complet dans un fichier JSON"""
        
        # 1. On sérialise le Joueur (On transforme l'objet en dictionnaire)
        player_data = {
            "name": player.name,
            "hp": player.hp,
            "inventory": player.inventory
        }
        
        # 2. On sérialise l'État du Jeu
        game_data = {
            "turns_since_last_fight": game_state.turns_since_last_fight,
            "in_combat": game_state.in_combat,
            "current_enemy": game_state.current_enemy # C'est déjà un dict ou None, donc c'est bon
        }
        
        # 3. On sérialise l'Historique (ATTENTION : On retire les images pour éviter de casser le JSON)
        messages_data = []
        for msg in messages:
            clean_msg = {
                "role": msg["role"],
                "content": msg["content"],
                # On ne sauvegarde PAS "image" car ce sont des octets binaires non compatibles JSON
                "has_image": "image" in msg and msg["image"] is not None # On note juste qu'il y avait une image
            }
            messages_data.append(clean_msg)
            
        # 4. On écrit le tout
        full_save = {
            "player": player_data,
            "game": game_data,
            "messages": messages_data
        }
        
        try:
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