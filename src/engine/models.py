import random
# Note: On a besoin d'importer config pour les stats des armes, 
# mais attention aux imports circulaires.
# Pour l'instant, on va importer config ici.
import src.config as settings

class Player:
    def __init__(self, name):
        self.name = name
        self.hp = 100
        self.inventory = ["Une vieille épée", "Une torche"] 
    
    def get_weapon_damage(self, weapon_name):
        # On utilise le nouveau chemin de config
        stats = settings.WEAPONS_STATS.get(weapon_name, settings.WEAPONS_STATS["Mains nues"])
        return random.randint(stats["min"], stats["max"])

class GameState:
    def __init__(self):
        self.turns_since_last_fight = 0
        self.in_combat = False
        self.current_enemy = None
        # On stocke le dernier prompt visuel.
        self.last_visual_context = ""

        # --- STATISTIQUES (Score) ---
        self.total_turns = 0          # Nombre de tours joués
        self.damage_dealt = 0         # Total dégâts infligés
        self.damage_taken = 0         # Total dégâts reçus
        self.enemies_defeated = 0     # Nombre de monstres tués