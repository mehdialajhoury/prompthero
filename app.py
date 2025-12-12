import streamlit as st
import os
import random
from dotenv import load_dotenv
from openai import OpenAI

# Import des classes du moteur
from game_engine import Player, GameState, DungeonMasterAI

# Import de la configuration depuis settings.py
import settings

# ------------------------------------------------------------------
# INITIALISATION & CONFIGURATION CLIENT
# ------------------------------------------------------------------
load_dotenv()

if "client_ai" not in st.session_state:
    if settings.UTILISER_PC_FIXE:
        st.session_state.client_ai = OpenAI(
            base_url=f"http://{settings.IP_PC_FIXE}:11434/v1", 
            api_key="ollama"
        )
        st.session_state.current_model = settings.MODEL_LOCAL
        print(f"CONNECTÉ AU PC FIXE ({settings.MODEL_LOCAL})")
    else:
        api_key = os.getenv("GROQ_API_KEY")
        st.session_state.client_ai = OpenAI(
            base_url="https://api.groq.com/openai/v1", 
            api_key=api_key
        )
        st.session_state.current_model = settings.MODEL_DISTANT
        print(f"CONNECTÉ À GROQ ({settings.MODEL_DISTANT})")

# ------------------------------------------------------------------
# FONCTIONS LOGIQUES
# ------------------------------------------------------------------
def init_game():
    if "player" not in st.session_state:
        st.session_state.player = Player("Aventurier")
        st.session_state.dm = DungeonMasterAI()
        st.session_state.game = GameState()
        st.session_state.messages = [] 
        
        intro = st.session_state.dm.generate_story(
            st.session_state.client_ai, 
            st.session_state.current_model, 
            "Je me réveille dans une cellule de prison sombre. Décris l'ambiance."
        )
        st.session_state.messages.append({"role": "assistant", "content": intro})

def process_turn(user_action):
    player = st.session_state.player
    dm = st.session_state.dm
    game = st.session_state.game
    client = st.session_state.client_ai
    model = st.session_state.current_model
    
    st.session_state.messages.append({"role": "user", "content": user_action})

    # --- LOGIQUE DE RENCONTRE ---
    if not game.in_combat:
        en_repit = game.turns_since_last_fight < settings.MIN_TOURS_REPIT
        condition_combat = (not en_repit) and (
            (random.random() < settings.PROBABILITE_BASE) or 
            (game.turns_since_last_fight >= settings.MAX_TOURS_SANS_COMBAT)
        )
        if condition_combat:
            # On passe client/model pour générer l'ennemi (et son image)
            game.current_enemy = dm.spawn_enemy(client, model)
            game.in_combat = True
            game.turns_since_last_fight = 0
            
            # --- AFFICHAGE DE L'IMAGE ---
            if "image" in game.current_enemy and game.current_enemy["image"]:
                # On ajoute un message spécial contenant l'image
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"⚠️ **ALERTE : {game.current_enemy['name']} !**",
                    "image": game.current_enemy["image"] # On stocke les bytes ici
                })
            else:
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"⚠️ **ALERTE : {game.current_enemy['name']} !**"
                })
            # ----------------------------

            intro_monster = dm.generate_story(
                client, model, 
                f"Un ennemi '{game.current_enemy['name']}' surgit ! Décris son apparition."
            )
            # On ajoute le texte de description à la suite
            st.session_state.messages.append({"role": "assistant", "content": intro_monster})
            return 

        else:
            game.turns_since_last_fight += 1

    # --- RESOLUTION DE L'ACTION ---
    response_text = ""
    
    if game.in_combat:
        if "fuir" in user_action.lower():
            if random.random() < 0.5:
                game.in_combat = False
                game.current_enemy = None
                game.turns_since_last_fight = 0
                response_text = dm.generate_story(client, model, user_action, system_instruction="Fuite réussie.", max_tokens=150)
            else:
                degats_ennemi = game.current_enemy['damage']
                player.hp -= degats_ennemi
                response_text = dm.generate_story(client, model, user_action, system_instruction=f"Fuite échouée. Ennemi frappe ({degats_ennemi} dmg).", max_tokens=150)
        else:
            # Attaque
            arme_utilisee = player.inventory[0] 
            for arme in player.inventory:
                if arme.lower() in user_action.lower():
                    arme_utilisee = arme
                    break
            
            degats_joueur = player.get_weapon_damage(arme_utilisee)
            game.current_enemy['hp'] -= degats_joueur

            if game.current_enemy['hp'] <= 0:
                game.in_combat = False
                game.current_enemy = None
                game.turns_since_last_fight = 0
                prompt_victoire = f"VICTOIRE ! Coup fatal ({degats_joueur} dgts). Ennemi mort. Retour au calme."
                response_text = dm.generate_story(client, model, user_action, system_instruction=prompt_victoire, max_tokens=300)
            else:
                degats_ennemi = 0
                touche = False
                if random.random() < 0.7:
                    touche = True
                    degats_ennemi = game.current_enemy['damage']
                    player.hp -= degats_ennemi
                
                if player.hp <= 0:
                    response_text = dm.generate_story(client, model, "Mort", system_instruction="Joueur mort. Game Over.")
                    st.error("💀 VOUS ÊTES MORT")
                    st.stop()

                pv_avant = game.current_enemy['hp'] + degats_joueur
                ctx = f"""
                [STYLE TÉLÉGRAPHIQUE] : Décris échange coups.
                Action: {user_action} ({arme_utilisee}) -> {degats_joueur} dmg.
                Ennemi passe de {pv_avant} à {game.current_enemy['hp']} PV.
                Riposte: {'Touché' if touche else 'Raté'} -> {degats_ennemi} dmg sur héros.
                """
                response_text = dm.generate_story(client, model, user_action, system_instruction=ctx, max_tokens=150)

    else:
        response_text = dm.generate_story(client, model, user_action)

    st.session_state.messages.append({"role": "assistant", "content": response_text})

# ------------------------------------------------------------------
# INTERFACE UTILISATEUR
# ------------------------------------------------------------------
st.set_page_config(page_title="Le Prompt dont vous êtes le Héros", page_icon="⚔️", layout="wide")

init_game()

with st.sidebar:
    st.title("🛡️ État du Héros")
    hp_percent = st.session_state.player.hp / 100
    st.progress(hp_percent, text=f"Santé : {st.session_state.player.hp}/100")
    
    st.subheader("🎒 Inventaire")
    for item in st.session_state.player.inventory:
        st.write(f"- {item}")
    
    st.markdown("---")
    
    if st.session_state.game.in_combat and st.session_state.game.current_enemy:
        st.error(f"⚔️ COMBAT EN COURS")
        en = st.session_state.game.current_enemy
        st.write(f"**{en['name']}**")
        st.caption(en['desc'])
        st.metric("PV Ennemi", f"{en['hp']}")
        
    st.markdown("---")
    st.caption(f"Moteur IA : {st.session_state.current_model}")

st.title("📖 Un Prompt dont vous êtes le Héros")

chat_container = st.container()
with chat_container:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # Si le message contient une image, on l'affiche
            if "image" in msg:
                st.image(msg["image"], caption="Généré par RTX 5080 (Pixel Art)", use_container_width=True)

if prompt := st.chat_input("Que faites-vous ?"):
    process_turn(prompt)
    st.rerun()