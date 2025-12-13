import streamlit as st
import os
import base64
import streamlit.components.v1 as components

class SoundManager:
    @staticmethod
    def get_absolute_path(filename):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, "assets", "sounds", filename)

    @staticmethod
    def play_ambiance(game_state):
        # 1. Préparation
        track_name = "combat" if game_state.in_combat else "exploration"
        filename = f"{track_name}.mp3"
        file_path = SoundManager.get_absolute_path(filename)

        if not os.path.exists(file_path):
            print(f"⚠️ Audio manquant : {file_path}")
            return

        # 2. Encodage Base64
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            b64 = base64.b64encode(data).decode()
            mime_type = "audio/mpeg"
        except Exception as e:
            print(f"Erreur lecture audio: {e}")
            return

        # 3. SCRIPT JAVASCRIPT AVEC "AUTO-UNLOCK"
        js_code = f"""
            <script>
            (function() {{
                var audioId = 'global-persistent-player';
                var b64Data = '{b64}';
                var mimeType = '{mime_type}';
                var parentDoc = window.parent.document;
                
                // 1. Gestion du lecteur
                var player = parentDoc.getElementById(audioId);
                
                if (!player) {{
                    player = parentDoc.createElement('audio');
                    player.id = audioId;
                    player.style.display = 'none';
                    player.loop = true;
                    player.autoplay = true;
                    player.volume = 0.3;
                    parentDoc.body.appendChild(player);
                }}
                
                // 2. Mise à jour de la source (si changement)
                var newSource = 'data:' + mimeType + ';base64,' + b64Data;
                if (!player.src || player.src.substring(0, 100) !== newSource.substring(0, 100)) {{
                    player.src = newSource;
                    
                    var playPromise = player.play();
                    
                    if (playPromise !== undefined) {{
                        playPromise.then(_ => {{
                            console.log("Audio: Lecture démarrée.");
                        }}).catch(error => {{
                            console.log("Audio: Autoplay bloqué. Attente interaction...");
                            
                            // --- LE CORRECTIF EST ICI ---
                            // Si le navigateur bloque, on attend le premier clic n'importe où
                            var unlockAudio = function() {{
                                player.play();
                                // Une fois lancé, on retire l'écouteur pour ne pas spammer
                                parentDoc.removeEventListener('click', unlockAudio);
                                parentDoc.removeEventListener('keydown', unlockAudio);
                            }};
                            
                            // On écoute les clics ou les touches clavier sur toute la page
                            parentDoc.addEventListener('click', unlockAudio);
                            parentDoc.addEventListener('keydown', unlockAudio);
                        }});
                    }}
                }} else {{
                    // Si c'est la même musique mais qu'elle est en pause (ex: démarrage bloqué)
                    if (player.paused) {{
                        player.play().catch(e => {{
                             // Si ça échoue encore, on réapplique le fix d'interaction
                            var unlockAudio = function() {{ player.play(); parentDoc.removeEventListener('click', unlockAudio); }};
                            parentDoc.addEventListener('click', unlockAudio);
                        }});
                    }}
                }}
            }})();
            </script>
        """

        components.html(js_code, height=0, width=0)