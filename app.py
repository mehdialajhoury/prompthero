import streamlit as st
import os
import random
from dotenv import load_dotenv
from openai import OpenAI

# IMPORTS ARCHITECTURE
import src.config as settings
from src.engine.models import Player, GameState
from src.engine.game import DungeonMasterAI
from src.utils.saves import SaveManager
from src.services.sound import SoundManager
from src.ui.styles import apply_custom_style

# ------------------------------------------------------------------
# INITIALISATION
# ------------------------------------------------------------------
load_dotenv()
st.set_page_config(page_title="Le Prompt dont vous êtes le Héros", page_icon="⚔️", layout="wide", initial_sidebar_state="expanded")

# Client AI
if "client_ai" not in st.session_state:
    if settings.UTILISER_PC_FIXE:
        st.session_state.client_ai = OpenAI(base_url=f"http://{settings.IP_PC_FIXE}:11434/v1", api_key="ollama")
        st.session_state.current_model = settings.MODEL_LOCAL
        print(f"CONNECTÉ AU PC FIXE ({settings.MODEL_LOCAL})")
    else:
        st.session_state.client_ai = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.getenv("GROQ_API_KEY"))
        st.session_state.current_model = settings.MODEL_DISTANT
        print(f"CONNECTÉ À GROQ ({settings.MODEL_DISTANT})")

# Style CSS
apply_custom_style()

# ------------------------------------------------------------------
# FONCTIONS LOGIQUES
# ------------------------------------------------------------------
def init_game():
    if "player" not in st.session_state:
        st.session_state.player = Player("Aventurier")
        st.session_state.dm = DungeonMasterAI()
        st.session_state.game = GameState()
        st.session_state.messages = [] 

        # Initialisation
        game_data, img = st.session_state.dm.process_game_turn(
            st.session_state.client_ai, 
            st.session_state.current_model, 
            "Je me réveille dans une cellule de prison sombre. Je sens un courant d'air frais qui vient d'une grille mal fixée. Décris l'ambiance en français.",
            st.session_state.player,
            game_mode="scenery"
        )
        
        st.session_state.messages.append({
            "role": "assistant", 
            "content": game_data.get("narrative", ""),
            "image": img,
            # On récupère le titre visuel, ou un titre par défaut
            "caption": game_data.get("visual_label", "Introduction")
        })

def process_turn(user_action):
    # Raccourcis
    player = st.session_state.player
    dm = st.session_state.dm
    game = st.session_state.game
    client = st.session_state.client_ai
    model = st.session_state.current_model
    
    # STATS : On compte un tour de plus
    game.total_turns += 1
    
    st.session_state.messages.append({"role": "user", "content": user_action})

    condition_combat = False 
    
    # Variables tampons pour éviter les UnboundLocalError
    final_narrative = ""
    final_image = None
    final_caption = None

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

            # Intro combat
            game_data, img = dm.process_game_turn(
                client, model, 
                prompt_narratif,
                player,
                game_mode="character" 
            )
            
            # On ajoute directement et ON QUITTE LA FONCTION (Return)
            st.session_state.messages.append({
                "role": "assistant", 
                "content": game_data.get("narrative", ""), 
                "image": img,
                "caption": f"Apparition : {game.current_enemy['name']}"
            })
            return 


    # --- 2. RÉSOLUTION DE L'ACTION (Si pas de nouvelle rencontre) ---
    game.turns_since_last_fight += 1
    
    system_instruction = None
    gen_img = True
    forced_mode = None
    combat_recap = "" 
    
    # === SI COMBAT EN COURS ===
    if game.in_combat:
        gen_img = False 
        
        if "fuir" in user_action.lower():
            if random.random() < 0.5:
                game.in_combat = False
                game.current_enemy = None
                game.turns_since_last_fight = 0
                system_instruction = "Le joueur a réussi à fuir le combat."
            else:
                degats_ennemi = game.current_enemy['damage']
                player.hp -= degats_ennemi
                
                # STATS : Dégâts reçus (fuite ratée)
                game.damage_taken += degats_ennemi
                
                system_instruction = f"La fuite a échoué. L'ennemi a frappé et infligé {degats_ennemi} dégâts."
                combat_recap = f"\n\n💔 **Fuite ratée ! Dégâts reçus : {degats_ennemi}**"
        else:
            # Combat physique
            arme_utilisee = player.inventory[0] 
            for arme in player.inventory:
                if arme.lower() in user_action.lower():
                    arme_utilisee = arme
                    break
            
            degats_joueur = player.get_weapon_damage(arme_utilisee)
            game.current_enemy['hp'] -= degats_joueur
            
            # STATS : Dégâts infligés
            game.damage_dealt += degats_joueur

            if game.current_enemy['hp'] <= 0:
                game.in_combat = False
                game.current_enemy = None
                game.turns_since_last_fight = 0
                
                # STATS : Ennemi vaincu
                game.enemies_defeated += 1
                
                system_instruction = f"VICTOIRE. L'ennemi est mort (Coup fatal : {degats_joueur} dmg). Le calme revient."
                combat_recap = f"\n\n🏆 **VICTOIRE !** (Dégâts finaux : {degats_joueur})"
            else:
                degats_ennemi = 0
                touche = False
                if random.random() < 0.7:
                    touche = True
                    degats_ennemi = game.current_enemy['damage']
                    player.hp -= degats_ennemi
                    
                    # STATS : Dégâts reçus (riposte)
                    game.damage_taken += degats_ennemi
                
                pv_ennemi_restant = game.current_enemy['hp']
                system_instruction = (
                f"RÉSULTAT MÉCANIQUE DU TOUR : Le joueur inflige {degats_joueur} dégâts (Arme équipée: {arme_utilisee}). "
                f"L'ennemi a maintenant {pv_ennemi_restant} PV. "
                f"Riposte ennemie : {'Touché' if touche else 'Raté'} ({degats_ennemi} dégâts au joueur)."
            )
                
                # Recap
                combat_recap = f"\n\n📊 **BILAN DU TOUR**"
                combat_recap += f"\n⚔️ Vous infligez : **{degats_joueur}** dégâts"
                if touche:
                    combat_recap += f"\n🛡️ Vous recevez : **{degats_ennemi}** dégâts"
                else:
                    combat_recap += f"\n💨 Vous esquivez l'attaque !"
                combat_recap += f"\n❤️ Vos PV : **{player.hp}** | 💀 PV Ennemi : **{pv_ennemi_restant}**"

    # === APPEL AU MOTEUR JSON ===
    
    game_data, final_image = dm.process_game_turn(
        client, model, 
        user_action, 
        player,
        system_instruction=system_instruction, 
        generate_image=gen_img,
        game_mode=forced_mode
    )

    # === APPLICATION DES EFFETS JSON ===
    hp_change = game_data.get("hp_change", 0)
    if hp_change != 0:
        player.hp += hp_change
        
        # STATS : Dégâts de piège (si négatif)
        if hp_change < 0:
            game.damage_taken += abs(hp_change)
            
        if player.hp > 100: player.hp = 100

    if player.hp < 0: player.hp = 0

    items_added = game_data.get("inventory_add", [])
    if items_added:
        player.inventory.extend(items_added)
        
    items_removed_request = game_data.get("inventory_remove", [])
    items_actually_removed = [] 
    if items_removed_request:
        for target_word in items_removed_request:
            item_to_delete = None
            for real_item in player.inventory:
                if target_word.lower() in real_item.lower(): 
                    item_to_delete = real_item
                    break
            if item_to_delete:
                player.inventory.remove(item_to_delete)
                items_actually_removed.append(item_to_delete)

    # 3. Construction Message Final
    final_narrative = game_data.get("narrative", "")
    
    notifications = []
    if hp_change < 0 and not game.in_combat: notifications.append(f"💔 Dégâts (Piège/Autre): {hp_change}")
    if hp_change > 0: notifications.append(f"💚 Soins: +{hp_change}")
    if items_added: notifications.append(f"🎒 Trouvé: {', '.join(items_added)}")
    if items_actually_removed: notifications.append(f"🗑️ Perdu: {', '.join(items_actually_removed)}")
    
    if notifications:
        final_narrative += "\n\n" + " | ".join(notifications)
        
    if combat_recap:
        final_narrative += combat_recap

    # Récupération de la légende pour l'image
    final_caption = game_data.get("visual_label", None)

    # Vérification Mort
    if player.hp <= 0 or game_data.get("game_state") == "dead":
        final_narrative += "\n\n💀 **VOUS ÊTES MORT**"
        player.hp = 0 

    # Ajout final au chat
    st.session_state.messages.append({
        "role": "assistant", 
        "content": final_narrative,
        "image": final_image,
        "caption": final_caption
    })

# ------------------------------------------------------------------
# INTERFACE UTILISATEUR
# ------------------------------------------------------------------
init_game()

# SideBar
with st.sidebar:
    st.title("🛡️ État du Héros")
    current_hp = st.session_state.player.hp
    bar_value = max(0.0, min(1.0, current_hp / 100))
    st.progress(bar_value, text=f"Santé : {current_hp}/100")
    
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
    
    st.subheader("💾 Système")
    col_save, col_load = st.columns(2)
    
    with col_save:
        if st.session_state.player.hp > 0:
            if st.button("Sauver", use_container_width=True):
                success, msg = SaveManager.save_game(
                    st.session_state.player,
                    st.session_state.game,
                    st.session_state.messages
                )
                if success: st.success("Sauvegardé !")
                else: st.error("Erreur")
    
    with col_load:
        if st.button("Charger", use_container_width=True):
            data, msg = SaveManager.load_game()
            if data:
                st.session_state.player.name = data["player"]["name"]
                st.session_state.player.hp = data["player"]["hp"]
                st.session_state.player.inventory = data["player"]["inventory"]
                st.session_state.game.turns_since_last_fight = data["game"]["turns_since_last_fight"]
                st.session_state.game.in_combat = data["game"]["in_combat"]
                st.session_state.game.current_enemy = data["game"]["current_enemy"]
                
                # STATS : Restauration des statistiques
                st.session_state.game.total_turns = data["game"].get("total_turns", 0)
                st.session_state.game.damage_dealt = data["game"].get("damage_dealt", 0)
                st.session_state.game.damage_taken = data["game"].get("damage_taken", 0)
                st.session_state.game.enemies_defeated = data["game"].get("enemies_defeated", 0)
                
                st.session_state.messages = data["messages"]
                st.success("Chargé !")
                st.rerun() 
            else:
                st.error(msg)
    
    SoundManager.play_ambiance(st.session_state.game)
        
    st.markdown("---")
    st.caption(f"Moteur IA : {st.session_state.current_model}")

st.title("📖 Un Prompt dont vous êtes le Héros")

# Affichage des messages
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
                # Récupération propre de la légende
                caption_text = msg.get("caption", None)
                st.image(msg["image"], caption=caption_text)

# Zone d'actions
if st.session_state.player.hp <= 0:
    st.error("💀 VOUS ÊTES MORT. L'AVENTURE EST TERMINÉE.")

    # On affiche le score
    stats = st.session_state.game
    st.markdown(f"""
    ### ⚰️ Fin de l'Aventure
    | Statistique | Valeur |
    |---|---|
    | ⏳ **Tours survécus** | {stats.total_turns} |
    | 💀 **Monstres vaincus** | {stats.enemies_defeated} |
    | ⚔️ **Dégâts infligés** | {stats.damage_dealt} |
    | 💔 **Dégâts subis** | {stats.damage_taken} |
    """)

    if st.button("🔄 Recommencer l'aventure", use_container_width=True):
        del st.session_state.player
        st.rerun()

else:
    if st.session_state.game.in_combat:
        st.markdown("### ⚔️ Actions de Combat")
        cols = st.columns(len(st.session_state.player.inventory) + 1)
        
        with cols[0]:
            if st.button("🏃 Fuir le combat", key="btn_flee", use_container_width=True):
                process_turn("Je tente de fuir !")
                st.rerun()

        for index, item_name in enumerate(st.session_state.player.inventory):
            stats = settings.WEAPONS_STATS.get(item_name, settings.WEAPONS_STATS["Mains nues"])
            degats_txt = f"{stats['min']}-{stats['max']} dmg"
            
            with cols[index + 1]:
                label = f"🗡️ {item_name}\n({degats_txt})"
                if st.button(label, key=f"btn_weapon_{index}", use_container_width=True):
                    process_turn(f"J'attaque avec {item_name} !")
                    st.rerun()

    placeholder_text = "Que faites-vous ?"
    if st.session_state.game.in_combat:
        placeholder_text = "Ou décrivez une action créative (ex: 'Je lui jette du sable')..."

    if prompt := st.chat_input(placeholder_text):
        process_turn(prompt)
        st.rerun()