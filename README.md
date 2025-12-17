# Un Prompt dont vous êtes le Héros ⚔️

**Prompt Hero** est un jeu de rôle textuel interactif (Text-Based RPG) "dont vous êtes le héros", propulsé par l'Intelligence Artificielle générative.

Ce projet a été développé comme démonstrateur technique explorant l'hybridation entre narration procédurale (LLM) et illustration temps réel (Stable Diffusion), le tout orchestré via une interface web légère.

## 🏗️ Architecture Technique

Le projet repose sur une architecture **Client-Serveur distribuée** pour optimiser les performances d'inférence.

### 1. Le Client (Interface & Logique)
- **Machine :** MacBook Air (Local)
- **Framework :** Streamlit (Python)
- **Rôle :**
  - Gestion de l'état du jeu (State Management).
  - Orchestration des appels API.
  - Interface utilisateur réactive (Chat, Inventaire, Système de combat).
  - Gestion audio (HTML5/JS Injection pour contourner les restrictions Safari).

### 2. Le Serveur d'Inférence (Compute Unit)
- **Machine :** Workstation Ubuntu / GPU **NVIDIA RTX 5080**
- **LLM (Cerveau) :**
  - **Modèle :** `Mistral-Nemo 12B` (via Ollama).
  - **Rôle :** Maître du Donjon, narration, gestion des règles en format JSON strict (Structured Output).
- **Génération d'Image (Yeux) :**
  - **Moteur :** ComfyUI (SDXL Turbo + LoRA Dark Fantasy).
  - **Rôle :** Interprétation des prompts narratifs en illustrations "Graphic Novel" en < 2 secondes.

---

## 📂 Structure du Projet

Le code suit une **Clean Architecture** simplifiée pour garantir la maintenabilité :

```text
prompthero/
├── app.py                  # Point d'entrée de l'application Streamlit
├── assets/                 # Ressources statiques (MP3, Images de fallback)
├── data/                   # Données JSON (Bestiaire, Lorebook)
└── src/                    # Code source modulaire
    ├── config.py           # Configuration globale (Stats armes, IP Serveur)
    ├── engine/             # Cœur du jeu
    │   ├── game.py         # Logique du Maître du Donjon (AI Wrapper)
    │   └── models.py       # Classes Métier (Player, GameState)
    ├── services/           # Adaptateurs externes
    │   ├── image.py        # Client WebSocket pour ComfyUI
    │   └── sound.py        # Gestionnaire audio (Base64 injection)
    └── utils/              # Utilitaires
        ├── lore.py         # Gestionnaire RAG (Bestiaire)
        ├── prompts.py      # Prompts Système & Templates
        └── saves.py        # Sérialisation JSON (Sauvegarde)


Fonctionnalités Clés
Narration IA en JSON : Le moteur ne génère pas juste du texte, mais des données structurées (dégâts, loot, changement d'état).

Bestiaire (léger) : Utilisation d'un "Lorebook" (bestiary.json) pour garantir la cohérence des ennemis rencontrés (prompts visuels fixes).

Immersion Sonore Dynamique : Ambiance auto-adaptative (Exploration vs Combat) avec lecteur persistant (Cross-fading simulé).

Système de Combat UI : Interface dynamique avec boutons d'actions contextuels basés sur l'inventaire.

Illustration Temps Réel : Chaque étape du récit est illustrée à la volée grâce à la RTX 5080.

## Installation & Démarrage
Pré-requis

Python 3.10+

Accès à un serveur Ollama et ComfyUI (ou configuration locale).

1. Installation des dépendances

Bash
pip install -r requirements.txt
2. Configuration

Créez un fichier .env à la racine :

Extrait de code
# IP de votre machine GPU (ou localhost)
COMFY_SERVER=192.168.1.XX:8188
IP_PC_FIXE=192.168.1.XX

# Configuration Modèles
MODEL_LOCAL=mistral-nemo
3. Lancer l'application

Bash
streamlit run app.py

## Ambiance sonore :

# Musique des combats : "depressing, dark ambient music" - Clavier-Music : https://pixabay.com/music/main-title-fearless-final-boss-battle-epic-274997/
# Musique de l'exploration : "Fearless (final boss battle epic)" - Kulakovka : https://pixabay.com/music/solo-piano-depressing-dark-ambient-music-354469/

## Lien de la vidéo : https://youtu.be/nOJex7JNKag

Projet réalisé par Mehdi Al-Ajhoury - PSTB 2025
