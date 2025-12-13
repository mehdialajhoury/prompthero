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

st.set_page_config(page_title="Le Prompt dont vous êtes le Héros", page_icon="⚔️", layout="wide", initial_sidebar_state="expanded")

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
# CSS Custom Médiéval
# ------------------------------------------------------------------

def apply_custom_style():
    st.markdown("""
        <style>
        /* IMPORT DES POLICES */
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Lora:ital,wght@0,400;0,700;1,400&display=swap');

        /* 1. FOND GÉNÉRAL ET TEXTE */
        .stApp {
            background-color: #0e1117;
            font-family: 'Lora', serif;
        }
        
        .stMarkdown, .stMarkdown p, .stMarkdown li, div[data-testid="stMarkdownContainer"] p {
            color: #ffffff !important;
        }

        /* 2. TITRES (DORÉS) */
        h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            font-family: 'Cinzel', serif !important;
            color: #d4af37 !important;
            text-shadow: 2px 2px 4px #000000;
        }
        
        /* 3. BARRE LATÉRALE */
        [data-testid="stSidebar"] {
            background-color: #1a1a1a;
            border-right: 1px solid #444;
        }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
             color: #bf4040 !important;
        }
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] li, [data-testid="stSidebar"] div {
            color: #e0e0e0 !important;
        }

        /* 4. ZONE DE SAISIE (INPUT) */
        .stChatInput textarea {
            background-color: #1a1a1a !important;
            color: #ffffff !important;
            border: 1px solid #d4af37 !important;
            caret-color: #d4af37 !important;
        }
        .stChatInput textarea::placeholder {
            color: #a0a0a0 !important;
            font-style: italic;
        }
        
        div[data-testid="stBottom"] {
            background-color: #0e1117 !important;
            border-top: 1px solid #333;
        }
        div[data-testid="stBottom"] > div {
            background-color: #0e1117 !important;
        }

        header[data-testid="stHeader"] {
            background-color: transparent !important;
            visibility: hidden;
        }
        
        [data-testid="stChatMessage"] {
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid #333;
            border-radius: 10px;
        }
        [data-testid="stChatMessageAvatar"] {
            background-color: #d4af37 !important;
        }

        .stProgress > div > div > div > div {
            background-color: #bf4040;
        }
        
        [data-testid="stSidebarCollapseButton"] {
            display: none !important;
        }
        
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        </style>
    """, unsafe_allow_html=True)


# ------------------------------------------------------------------
# FONCTIONS LOGIQUES
# ------------------------------------------------------------------
def init_game():
    if "player" not in st.session_state:
        st.session_state.player = Player("Aventurier")
        st.session_state.dm = DungeonMasterAI()
        st.session_state.game = GameState()
        st.session_state.messages = [] 

        # Initialisation via la nouvelle fonction process_game_turn
        # On ne veut pas que l'IA change les PV au démarrage, juste du texte
        game_data, intro_img = st.session_state.dm.process_game_turn(
            st.session_state.client_ai, 
            st.session_state.current_model, 
            "Je me réveille dans une cellule de prison sombre. Décris l'ambiance.",
            st.session_state.player,
            game_mode="scenery"
        )
        
        st.session_state.messages.append({
            "role": "assistant", 
            "content": game_data.get("narrative", ""),
            "image": intro_img 
        })

def process_turn(user_action):
    # Raccourcis
    player = st.session_state.player
    dm = st.session_state.dm
    game = st.session_state.game
    client = st.session_state.client_ai
    model = st.session_state.current_model
    
    st.session_state.messages.append({"role": "user", "content": user_action})

    condition_combat = False 

    # --- 1. LOGIQUE DE RENCONTRE (Début du combat) ---
    if not game.in_combat:
        en_repit = game.turns_since_last_fight < settings.MIN_TOURS_REPIT
        
        condition_combat = (not en_repit) and (
            (random.random() < settings.PROBABILITE_BASE) or 
            (game.turns_since_last_fight >= settings.MAX_TOURS_SANS_COMBAT)
        )

        if condition_combat:
            game.current_enemy = dm.spawn_enemy(client, model)
            game.in_combat = True
            game.turns_since_last_fight = 0
            
            st.session_state.messages.append({
                "role": "assistant", 
                "content": f"⚠️ **ALERTE : {game.current_enemy['name']} !**"
            })

            description_physique = game.current_enemy['desc']
            prompt_narratif = (
                f"Un ennemi '{game.current_enemy['name']}' surgit ! "
                f"Il ressemble à ceci : {description_physique}. "
                f"Décris son apparition."
            )

            # On utilise process_game_turn, mais on sait que c'est une intro de combat
            game_data, intro_img = dm.process_game_turn(
                client, model, 
                prompt_narratif,
                player,
                game_mode="character" 
            )
            
            st.session_state.messages.append({
                "role": "assistant", 
                "content": game_data.get("narrative", ""), 
                "image": intro_img
            })
            return 

        else:
            game.turns_since_last_fight += 1


    # --- 2. RÉSOLUTION DE L'ACTION ---
    
    system_instruction = None
    gen_img = True
    forced_mode = None
    
    # === SI COMBAT EN COURS ===
    if game.in_combat:
        gen_img = False # Pas d'image à chaque coup d'épée
        
        if "fuir" in user_action.lower():
            if random.random() < 0.5:
                game.in_combat = False
                game.current_enemy = None
                game.turns_since_last_fight = 0
                system_instruction = "Le joueur a réussi à fuir le combat."
            else:
                degats_ennemi = game.current_enemy['damage']
                player.hp -= degats_ennemi
                system_instruction = f"La fuite a échoué. L'ennemi a frappé et infligé {degats_ennemi} dégâts."
        else:
            # Combat physique (Calculs Python)
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
                system_instruction = f"VICTOIRE. L'ennemi est mort (Coup fatal : {degats_joueur} dmg). Le calme revient."
            else:
                degats_ennemi = 0
                touche = False
                if random.random() < 0.7:
                    touche = True
                    degats_ennemi = game.current_enemy['damage']
                    player.hp -= degats_ennemi
                
                pv_restant = game.current_enemy['hp']
                system_instruction = (
                    f"COMBAT EN COURS. Joueur attaque ({arme_utilisee}) : {degats_joueur} dégâts. "
                    f"Ennemi ({pv_restant} PV restants) riposte : {'Touché' if touche else 'Raté'} ({degats_ennemi} dégâts reçus)."
                )

    # === APPEL AU MOTEUR JSON (Pour Narrative + Gestion Inventaire Exploration) ===
    # En combat, system_instruction contient les dégâts calculés.
    # En exploration, system_instruction est None, l'IA décide tout.
    
    game_data, response_img = dm.process_game_turn(
        client, model, 
        user_action, 
        player,
        system_instruction=system_instruction, 
        generate_image=gen_img,
        game_mode=forced_mode
    )

    # === APPLICATION DES EFFETS JSON ===
    # 1. Mise à jour PV (Venant de l'IA - ex: piège, potion)
    # Note : En combat, les dégâts sont déjà appliqués par Python ci-dessus.
    # L'IA devrait renvoyer hp_change=0 en combat si elle suit bien les consignes,
    # ou on peut additionner si c'est un effet bonus.
    hp_change = game_data.get("hp_change", 0)
    if hp_change != 0:
        player.hp += hp_change

    # 2. Inventaire (VERSION CORRIGÉE ET INTELLIGENTE)
    items_added = game_data.get("inventory_add", [])
    if items_added:
        # On nettoie un peu l'entrée (ex: éviter d'ajouter "Une torche" si on a déjà "Torche")
        player.inventory.extend(items_added)
        
    items_removed_request = game_data.get("inventory_remove", [])
    items_actually_removed = [] # On va stocker ce qu'on a VRAIMENT supprimé

    if items_removed_request:
        for target_word in items_removed_request:
            # On cherche l'objet réel dans l'inventaire qui ressemble à la demande
            # Ex: Si demande "Torche" et inventaire ["Une torche"], on trouve "Une torche"
            item_to_delete = None
            for real_item in player.inventory:
                if target_word.lower() in real_item.lower(): # Comparaison insensible à la casse
                    item_to_delete = real_item
                    break
            
            # Si on a trouvé une correspondance, on supprime
            if item_to_delete:
                player.inventory.remove(item_to_delete)
                items_actually_removed.append(item_to_delete)
            else:
                # Debug optionnel : L'IA a demandé de supprimer un truc qu'on a pas
                print(f"DEBUG: L'IA veut supprimer '{target_word}' mais introuvable dans {player.inventory}")

    # 3. Construction Message Final
    final_text = game_data.get("narrative", "")
    
    # Notifications (Feedback UI)
    notifications = []
    if hp_change < 0: notifications.append(f"💔 Dégâts (IA): {hp_change}")
    if hp_change > 0: notifications.append(f"💚 Soins: +{hp_change}")
    if items_added: notifications.append(f"🎒 Trouvé: {', '.join(items_added)}")
    if items_actually_removed: 
        notifications.append(f"🗑️ Perdu : {', '.join(items_actually_removed)}")
    
    if notifications:
        final_text += "\n\n" + " | ".join(notifications)
        
    # Vérification Mort
    if player.hp <= 0 or game_data.get("game_state") == "dead":
        final_text += "\n\n💀 **VOUS ÊTES MORT**"
        st.error("GAME OVER")
        # st.stop() # Optionnel

    # Ajout final au chat
    st.session_state.messages.append({
        "role": "assistant", 
        "content": final_text,
        "image": response_img
    })

# ------------------------------------------------------------------
# INTERFACE UTILISATEUR
# ------------------------------------------------------------------
apply_custom_style() 
init_game()

with st.sidebar:
    st.title("🛡️ État du Héros")
    hp_display = max(0, st.session_state.player.hp) # Eviter barre négative
    hp_percent = hp_display / 100
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
        if msg["role"] == "user":
            avatar_icon = "🗡️"
        else:
            avatar_icon = "🧙‍♂️"
        
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(msg["content"])
            if "image" in msg and msg["image"] is not None:
                st.image(msg["image"], caption="Généré par RTX 5080")

if prompt := st.chat_input("Que faites-vous ?"):
    process_turn(prompt)
    st.rerun()