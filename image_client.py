import json
import urllib.request
import urllib.parse
import random
import uuid
import os
import websocket
from dotenv import load_dotenv

# 1. Configuration et Debug
load_dotenv() # Charge le fichier .env

# --- DEBUG ---
server_ip = os.getenv("COMFY_SERVER")
print(f"DEBUG - Valeur brute dans .env : {server_ip}")
# ------------------------------------------

# Vérication de l'url du serveur ComfyUI
COMFY_SERVER = server_ip if server_ip else "localhost:8188"

print(f"DEBUG - Adresse finale utilisée : {COMFY_SERVER}")

CLIENT_ID = str(uuid.uuid4())

def queue_prompt(prompt_workflow):
    """Envoie la demande au serveur ComfyUI"""
    p = {"prompt": prompt_workflow, "client_id": CLIENT_ID}
    data = json.dumps(p).encode('utf-8')
    # On envoie une requête POST
    req = urllib.request.Request(f"http://{COMFY_SERVER}/prompt", data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_image(filename, subfolder, folder_type):
    """Télécharge l'image générée"""
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"http://{COMFY_SERVER}/view?{url_values}") as response:
        return response.read()

def generate_image_rtx(prompt_text, workflow_path="image_workflow.json"):
    """Fonction principale à appeler depuis le jeu"""
    
    # A. Vérifier si le serveur est en ligne (Optionnel mais propre)
    try:
        urllib.request.urlopen(f"http://{COMFY_SERVER}", timeout=1)
    except:
        print(f"Serveur ComfyUI injoignable sur {COMFY_SERVER}")
        return None

    # B. Charger le workflow JSON
    try:
        with open(workflow_path, "r", encoding="utf-8") as f:
            prompt_data = json.load(f)
    except FileNotFoundError:
        print(f"Fichier {workflow_path} introuvable.")
        return None

    # C. INJECTION DES VARIABLES
    
    # Nœud 5 : Prompt Positif
    # On ajoute "pixel art" pour renforcer le style
    full_prompt = f"pixel art, {prompt_text}, high quality, 16-bit style"
    prompt_data["5"]["inputs"]["text"] = full_prompt

    # Nœud 6 : Prompt Négatif
    prompt_data["6"]["inputs"]["text"] = "photorealistic, 3d render, vector, smooth, blur, noisy, text, watermark, photo, realism, camera"

    # Nœud 4 : La Seed (Graine)
    # On met un nombre aléatoire géant pour que l'image change à chaque fois
    prompt_data["4"]["inputs"]["seed"] = random.randint(1, 1000000000000)

    # D. Connexion WebSocket (Pour attendre la fin du calcul)
    ws = websocket.WebSocket()
    try:
        ws.connect(f"ws://{COMFY_SERVER}/ws?clientId={CLIENT_ID}")
    except:
        print("Erreur de connexion WebSocket")
        return None
    
    # E. Envoyer l'ordre au GPU
    print(f"Génération en cours sur GPU : '{prompt_text}'...")
    queue_prompt(prompt_data)

    # F. Attendre que le GPU ait terminé
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id']:
                    break # Le calcul est terminé !
    
    # G. Récupérer l'image
    # On demande l'historique pour trouver le nom du fichier créé
    history_url = f"http://{COMFY_SERVER}/history"
    with urllib.request.urlopen(history_url) as response:
        history = json.loads(response.read())
    
    # On prend la toute dernière tâche
    last_prompt_id = list(history.keys())[-1]
    outputs = history[last_prompt_id]['outputs']
    
    # On cherche la sortie du Nœud 9 (SaveImage)
    if '9' in outputs:
        node_output = outputs['9']
        if 'images' in node_output:
            image_info = node_output['images'][0]
            # On télécharge les octets de l'image
            return get_image(image_info['filename'], image_info['subfolder'], image_info['type'])

    return None