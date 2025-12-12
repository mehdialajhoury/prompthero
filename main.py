import os
import random
import json
from dotenv import load_dotenv
from openai import OpenAI

# ------------------------------------------------------------------
# CENTRE DE CONTRÔLE
# ------------------------------------------------------------------

# True : PC Fixe, False : Groq
UTILISER_PC_FIXE = True 

# Configuration PC FIXE (Local / Ollama)
#IP_PC_FIXE = "192.168.1.30" # IP Locale
IP_PC_FIXE = "100.69.216.3" # IP PC VPN
MODEL_LOCAL = "llama3.1"

# Configuration CLOUD (Groq)
MODEL_DISTANT = "llama-3.3-70b-versatile"

# ------------------------------------------------------------------
# INITIALISATION INTELLIGENTE
# ------------------------------------------------------------------
load_dotenv()

if UTILISER_PC_FIXE:
    print(f"MODE: PC FIXE sur {IP_PC_FIXE}")
    print(f"Modèle: {MODEL_LOCAL}")
    
    client = OpenAI(
        base_url=f"http://{IP_PC_FIXE}:11434/v1",
        api_key="ollama" # Clé fictive
    )
    CURRENT_MODEL = MODEL_LOCAL

else:
    print("MODE: CLOUD (Groq)")
    print(f"Modèle: {MODEL_DISTANT}")
    
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise ValueError("ERREUR : Clé Groq manquante dans le .env")
        
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=groq_key
    )
    CURRENT_MODEL = MODEL_DISTANT

# ------------------------------------------------------------------
# DONNÉES DE JEU
# ------------------------------------------------------------------
WEAPONS_STATS = {
    "Une vieille épée": {"min": 8, "max": 15},
    "Une torche": {"min": 2, "max": 6},
    "Mains nues": {"min": 1, "max": 3}
}

PROBABILITE_BASE = 0.2
MAX_TOURS_SANS_COMBAT = 5
MIN_TOURS_REPIT = 2

# ------------------------------------------------------------------
# CLASSES
# ------------------------------------------------------------------
class Player:
    def __init__(self, name):
        self.name = name
        self.hp = 100
        self.inventory = ["Une vieille épée", "Une torche"] 
    
    def get_weapon_damage(self, weapon_name):
        stats = WEAPONS_STATS.get(weapon_name, WEAPONS_STATS["Mains nues"])
        return random.randint(stats["min"], stats["max"])

    def __str__(self):
        return f"Héros: {self.name} | PV: {self.hp}/100"

class GameState:
    def __init__(self):
        self.turns_since_last_fight = 0
        self.in_combat = False
        self.current_enemy = None

class DungeonMasterAI:
    def __init__(self):
        self.system_prompt = """
        Tu es le Maître du Donjon d'un jeu de rôle.
        Règles IMPÉRATIVES :
        1. BRIÈVETÉ : Fais des paragraphes courts (max 3-4 phrases en exploration).
        2. RYTHME : Ne te perds pas dans les détails inutiles.
        3. INTERDICTION : Ne fais pas agir le joueur à sa place.
        4. INTERDICTION : N'invente pas d'objets trouvés (loot) sans instruction technique.
        5. Finis toujours tes phrases.
        """
        self.history = [{"role": "system", "content": self.system_prompt}]

    def generate_story(self, user_input, system_instruction=None, max_tokens=500): 
        full_content = user_input
        if system_instruction:
            full_content += f"\n\n[INSTRUCTION SYSTÈME IMPÉRATIVE] : {system_instruction}"
        
        self.history.append({"role": "user", "content": full_content})

        try:
            response = client.chat.completions.create(
                model=CURRENT_MODEL,
                messages=self.history,
                temperature=0.7,
                max_tokens=max_tokens 
            )
            narrative = response.choices[0].message.content
            self.history.append({"role": "assistant", "content": narrative})
            return narrative
        except Exception as e:
            return f"Erreur IA ({CURRENT_MODEL}) : {e}"

    def spawn_enemy(self):
        prompt_generation = """
        [TÂCHE INTERNE DU MOTEUR DE JEU]
        Analyse le DERNIER LIEU décrit dans la conversation ci-dessus.
        Invente un ennemi qui vit logiquement à cet endroit.
        
        Réponds UNIQUEMENT avec ce JSON :
        {
            "name": "Nom du monstre",
            "hp": un entier (20-60),
            "damage": un entier (4-10),
            "desc": "courte description physique (5 mots max)"
        }
        """
        temp_messages = self.history + [{"role": "user", "content": prompt_generation}]
        
        try:
            response = client.chat.completions.create(
                model=CURRENT_MODEL,
                messages=temp_messages,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except:
            return {"name": "Rat Géant", "hp": 20, "damage": 4, "desc": "sale et agressif"}

# ------------------------------------------------------------------
# BOUCLE PRINCIPALE
# ------------------------------------------------------------------
def main():
    player = Player("Aventurier")
    dm = DungeonMasterAI()
    game = GameState()
    
    print(f"--- RPG INFINI : UN PROMPT DONT VOUS ÊTES LE HÉROS ---")
    print(f"--- Moteur : {CURRENT_MODEL} ---")
    
    print(dm.generate_story("Je me réveille dans une cellule de prison sombre et humide. Décris l'ambiance."))

    while True:
        # HUD
        print("\n" + "="*50)
        print(f" {player}")
        if game.in_combat:
            print(f" ⚔️  ENNEMI : {game.current_enemy['name']} ({game.current_enemy['desc']}) | PV : {game.current_enemy['hp']}")
        print("="*50)

        # GESTION RENCONTRES
        if not game.in_combat:
            en_repit = game.turns_since_last_fight < MIN_TOURS_REPIT
            condition_combat = (not en_repit) and (
                (random.random() < PROBABILITE_BASE) or 
                (game.turns_since_last_fight >= MAX_TOURS_SANS_COMBAT)
            )

            if condition_combat:
                print("\n... Une présence hostile se fait sentir ...")
                game.current_enemy = dm.spawn_enemy()
                game.in_combat = True
                game.turns_since_last_fight = 0
                
                prompt_intro = f"Un ennemi de type '{game.current_enemy['name']}' surgit ! Décris son apparition brutale."
                print(dm.generate_story(prompt_intro))
            else:
                game.turns_since_last_fight += 1

        # INPUT
        if game.in_combat:
            print(f"Armes : {player.inventory}")
            action = input("Action (Attaquer / Fuir) : ").lower()
        else:
            action = input("Que faites-vous ? (q=quitter) : ").lower()

        if action == "q": break

        # RÉSOLUTION TOUR
        if game.in_combat:
            
            # Fuite
            if "fuir" in action:
                if random.random() < 0.5:
                    game.in_combat = False
                    game.current_enemy = None
                    game.turns_since_last_fight = 0
                    print(dm.generate_story(action, system_instruction="Fuite réussie. Décris la course éperdue.", max_tokens=150))
                    continue
                else:
                    msg_fuite = "TENTATIVE DE FUITE ÉCHOUÉE."
            else:
                msg_fuite = ""

            # Attaque
            arme_utilisee = "Mains nues"
            arme_trouvee = False
            for arme in player.inventory:
                if arme.lower() in action:
                    arme_utilisee = arme
                    arme_trouvee = True
                    break
            
            if not arme_trouvee and len(player.inventory) > 0 and "fuir" not in action:
                arme_utilisee = player.inventory[0]

            degats_joueur = 0
            if "fuir" not in action:
                degats_joueur = player.get_weapon_damage(arme_utilisee)
                game.current_enemy['hp'] -= degats_joueur

            # Mort Ennemi
            if game.current_enemy['hp'] <= 0:
                game.in_combat = False
                game.current_enemy = None
                game.turns_since_last_fight = 0
                
                prompt_victoire = f"""
                VICTOIRE ! Coup fatal ({degats_joueur} dgts).
                1. Décris la mort de l'ennemi.
                2. IMPORTANT : Une fois l'ennemi à terre, décris le silence qui revient.
                3. RAPPELLE IMMÉDIATEMENT la situation précédente (ex: "Le tunnel est toujours là") pour relancer l'aventure.
                """
                print(dm.generate_story(action, system_instruction=prompt_victoire, max_tokens=300))
                continue

            # Riposte Ennemi
            degats_ennemi = 0
            touche = False
            if random.random() < 0.7:
                touche = True
                degats_ennemi = game.current_enemy['damage']
                player.hp -= degats_ennemi

            # Mort Joueur
            if player.hp <= 0:
                print(dm.generate_story("Le joueur prend un coup mortel.", system_instruction="Le joueur est mort. Game Over. Décris la fin tragique."))
                print("\n💀 VOUS ÊTES MORT 💀")
                break

            # Récit Combat (Anti-Hallucination Mathématique)
            pv_avant = game.current_enemy['hp'] + degats_joueur 
            
            contexte_technique = f"""
            [STYLE TÉLÉGRAPHIQUE IMPÉRATIF] :
            1. Décris l'impact en 2 phrases MAX.
            2. Ne fais AUCUN calcul mathématique toi-même.
            3. Fie-toi UNIQUEMENT aux chiffres ci-dessous.
            
            BILAN MATHÉMATIQUE (Déjà calculé, ne pas modifier) :
            - Action Héros : {action} {msg_fuite} (Arme: {arme_utilisee}).
            - Dégâts infligés : {degats_joueur}.
            - RÉSULTAT : L'ennemi passe de {pv_avant} PV à {game.current_enemy['hp']} PV.
            - Riposte Ennemi : {'A touché !' if touche else 'A raté !'} -> Inflige {degats_ennemi} dégâts au héros.
            """
            print(dm.generate_story(action, system_instruction=contexte_technique, max_tokens=150))

        else:
            print(dm.generate_story(action))

if __name__ == "__main__":
    main()