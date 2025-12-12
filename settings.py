# settings.py

# ========================================
# CONFIGURATION TECHNIQUE (INFRASTRUCTURE)
# ========================================
UTILISER_PC_FIXE = True 
IP_PC_FIXE = "192.168.1.30" # Votre IP locale
MODEL_LOCAL = "llama3.1"
MODEL_DISTANT = "llama-3.3-70b-versatile"

# =====================================
# CONFIGURATION DU GAME DESIGN (RÈGLES)
# =====================================

# Statistiques des armes (Min Dégâts, Max Dégâts)
WEAPONS_STATS = {
    "Une vieille épée": {"min": 8, "max": 15},
    "Une torche": {"min": 2, "max": 6},
    "Mains nues": {"min": 1, "max": 3}
}

# Probabilités et Rythme
PROBABILITE_BASE = 0.2          # 20% de chance de rencontre par tour
MAX_TOURS_SANS_COMBAT = 5       # Combat forcé au bout de 5 tours
MIN_TOURS_REPIT = 2             # Tours de calme garantis après une victoire