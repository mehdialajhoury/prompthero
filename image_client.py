import json
import urllib.request
import urllib.parse
import random
import uuid
import os
import websocket
from dotenv import load_dotenv

# 1. Configuration et Debug
load_dotenv() 

server_ip = os.getenv("COMFY_SERVER")
COMFY_SERVER = server_ip if server_ip else "localhost:8188"
CLIENT_ID = str(uuid.uuid4())

def queue_prompt(prompt_workflow):
    """Envoie la demande au serveur ComfyUI"""
    p = {"prompt": prompt_workflow, "client_id": CLIENT_ID}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{COMFY_SERVER}/prompt", data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_image(filename, subfolder, folder_type):
    """Télécharge l'image générée"""
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"http://{COMFY_SERVER}/view?{url_values}") as response:
        return response.read()

# --- NOUVEAU STYLE : DARK FANTASY ILLUSTRATION ---
def generate_image_rtx(prompt_text, mode="scenery", workflow_path="image_workflow.json"):
    
    # A. Vérifier serveur
    try:
        urllib.request.urlopen(f"http://{COMFY_SERVER}", timeout=1)
    except:
        print(f"Serveur ComfyUI injoignable sur {COMFY_SERVER}")
        return None

    # B. Charger JSON
    try:
        with open(workflow_path, "r", encoding="utf-8") as f:
            prompt_data = json.load(f)
    except FileNotFoundError:
        print(f"Fichier {workflow_path} introuvable.")
        return None

    # C. CONFIGURATION
    
    # 1. LE LORA (NOUVEAU FICHIER)
    if "2" in prompt_data and "inputs" in prompt_data["2"]:
        # On utilise le nouveau LoRA téléchargé
        prompt_data["2"]["inputs"]["lora_name"] = "dark_fantasy_xl.safetensors"
        prompt_data["2"]["inputs"]["strength_model"] = 0.8 # Un peu moins fort pour laisser passer les couleurs

    # 2. PROMPTS SPÉCIFIQUES (NOUVEAU STYLE)
    if mode == "scenery":
        # --- MODE DÉCOR ---
        # On veut de la couleur, du détail, une ambiance lourde
        style_prefix = "dark fantasy art, oil painting style, atmospheric lighting, ominous dungeon environment, highly detailed, dramatic shadows, gloom"
        # On n'interdit PLUS la couleur
        negative_prompt = "human, person, people, man, woman, character, face, skin, eyes, body, monster, creature, animal, anime, cartoon, 3d render, text, watermark, bright cheerful colors, kawaii"

    elif mode == "character":
        # --- MODE PERSONNAGE/MONSTRE ---
        style_prefix = "dark fantasy character illustration, graphic novel style, dynamic lighting, centered subject, dark background, masterpiece, sharp details, grimdark"
        
        # Base du négatif (On autorise la couleur !)
        negative_prompt = "landscape, scenery, forest, mountain, building, architecture, multiple people, crowd, anime, cartoon, 3d render, blurry, text, watermark, ugly, deformed, cute, bright colors"
        
        prompt_lower = prompt_text.lower()

        # --- A. MONSTER ENFORCER ---
        monster_keywords = ["rat", "wolf", "spider", "snake", "worm", "beast", "creature", "monster", "skeleton", "zombie", "goblin", "orc", "dragon", "bat"]
        if any(kw in prompt_lower for kw in monster_keywords):
            print("👹 Type détecté : MONSTRE (Verrouillage Anti-Humain)")
            negative_prompt += ", human, man, woman, girl, boy, female, male, human face"
            if "skeleton" in prompt_lower:
                negative_prompt += ", skin, flesh"

        # --- B. GENDER ENFORCER ---
        else:
            if any(word in prompt_lower for word in ["man", "male", "boy", "knight", "king", "wizard", "he ", "his ", "prince"]):
                negative_prompt += ", woman, girl, female, lady, empress, witch, breasts"
            elif any(word in prompt_lower for word in ["woman", "female", "girl", "queen", "witch", "sorceress", "she ", "her ", "princess"]):
                negative_prompt += ", man, male, boy, king, wizard, beard"
        
        # --- C. ANOMALIES ---
        if "headless" in prompt_lower or "no head" in prompt_lower:
            negative_prompt += ", head, face, skull, neck, helmet"
    
    else:
        # Fallback
        style_prefix = "dark fantasy illustration"
        negative_prompt = "anime, cartoon, 3d render"

    # Injection des prompts
    prompt_data["5"]["inputs"]["text"] = f"{style_prefix}, {prompt_text}"
    prompt_data["6"]["inputs"]["text"] = negative_prompt

    # Nœud 4 : La Seed
    prompt_data["4"]["inputs"]["seed"] = random.randint(1, 1000000000000)

    # D. WebSocket
    ws = websocket.WebSocket()
    try:
        ws.connect(f"ws://{COMFY_SERVER}/ws?clientId={CLIENT_ID}")
    except:
        print("Erreur de connexion WebSocket")
        return None
    
    # E. Envoi
    print(f"Génération en cours ({mode}): '{prompt_text}'...")
    queue_prompt(prompt_data)

    # F. Attente
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id']:
                    break 
    
    # G. Récupération
    history_url = f"http://{COMFY_SERVER}/history"
    with urllib.request.urlopen(history_url) as response:
        history = json.loads(response.read())
    
    last_prompt_id = list(history.keys())[-1]
    outputs = history[last_prompt_id]['outputs']
    
    if '9' in outputs:
        node_output = outputs['9']
        if 'images' in node_output:
            image_info = node_output['images'][0]
            return get_image(image_info['filename'], image_info['subfolder'], image_info['type'])

    return None