import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import socketio
import os
import json
from pathlib import Path
import logging
import numpy as np
from threading import Lock
import time
import pygame
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', filename='app.log')
logger = logging.getLogger(__name__)



# Initialisation de pygame pour l'audio
def init_audio():
    try:
        pygame.mixer.init()
        logger.info("Pygame audio initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize audio: {e}")


# Appeler l'initialisation au démarrage
init_audio()

# Chemins des fichiers audio
SCAN_SOUND_PATH = "C:/Users/Administrateur/Downloads/store-scanner-beep-90395.mp3"
SUCCESS_SOUND_PATH = "C:/Users/Administrateur/Downloads/successed-295058.mp3"

# Variables pour suivre l'état des sons
if "last_production_count" not in st.session_state:
    st.session_state.last_production_count = 0
if "objective_100_played" not in st.session_state:
    st.session_state.objective_100_played = False


def play_sound(sound_path):
    """Jouer un son"""
    try:
        if os.path.exists(sound_path):
            pygame.mixer.music.load(sound_path)
            pygame.mixer.music.play()
            logger.info(f"Playing sound: {sound_path}")
        else:
            logger.warning(f"Sound file not found: {sound_path}")
    except Exception as e:
        logger.error(f"Error playing sound: {e}")


def check_and_play_sounds(productions, objectif_total):
    """Vérifier les conditions pour jouer les sons"""
    current_production = 0

    # Calculer la production actuelle
    for p in productions:
        try:
            current_production = max(current_production, int(p.get("nbPaireEncour", 0)))
        except:
            pass

    # Vérifier nouvelle donnée (scan)
    if current_production > st.session_state.last_production_count:
        play_sound(SCAN_SOUND_PATH)
        st.session_state.last_production_count = current_production
        logger.info(f"New scan detected: {current_production} pairs")

    # Vérifier objectif 100% atteint - CORRECTION ICI
    if objectif_total > 0:
        achievement = (current_production / objectif_total * 100)

        # Si on atteint ou dépasse 100% ET que le son n'a pas encore été joué
        if achievement >= 100 and not st.session_state.objective_100_played:
            play_sound(SUCCESS_SOUND_PATH)
            st.session_state.objective_100_played = True
            logger.info("Objective 100% reached! Playing success sound")




# Global lock for thread-safe event queue
socket_events_lock = Lock()
import queue

# File d'attente globale pour les événements Socket.IO
if "SOCKET_EVENT_QUEUE" not in globals():
    SOCKET_EVENT_QUEUE = queue.Queue()


def enqueue_socket_event(event_type, data=None):
    """À appeler dans les callbacks Socket.IO (thread séparé)."""
    try:
        SOCKET_EVENT_QUEUE.put({'event': event_type, 'data': data}, block=False)
    except Exception as e:
        logger.error(f"Erreur enqueue_socket_event: {e}")


def process_socket_events():
    """À appeler dans le thread principal Streamlit pour vider la queue."""
    processed = 0
    while not SOCKET_EVENT_QUEUE.empty():
        evt = SOCKET_EVENT_QUEUE.get()
        if "socket_events" not in st.session_state:
            st.session_state.socket_events = []
        st.session_state.socket_events.append(evt)
        processed += 1
    return processed


# Configuration de la page
st.set_page_config(
    page_title="Application Production",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisation de Socket.IO
sio = socketio.Client(
    reconnection=True,
    reconnection_attempts=5,
    reconnection_delay=1
)
BASE_URL = "http://192.168.1.210:5001"
DEFAULT_PORT = 8056

# Définir le port si lancé directement
if __name__ == "__main__" and not hasattr(st, 'server'):
    os.environ['STREAMLIT_SERVER_PORT'] = str(DEFAULT_PORT)
###########################################################################################
class SessionSynchronizer:
    def __init__(self):
        self.sync_file = Path("session_sync.json")

    def update_session_activity(self, username, app_name, action):
        """Met à jour l'activité de session"""
        data = self.load_sync_data()

        if username not in data:
            data[username] = {}

        data[username][app_name] = {
            "last_activity": time.time(),
            "action": action,
            "timestamp": datetime.now().isoformat()
        }

        self.save_sync_data(data)

    def get_user_sessions(self, username):
        """Récupère les sessions actives d'un utilisateur"""
        data = self.load_sync_data()
        return data.get(username, {})

    def load_sync_data(self):
        if not self.sync_file.exists():
            return {}
        try:
            with open(self.sync_file, "r") as f:
                return json.load(f)
        except:
            return {}

    def save_sync_data(self, data):
        with open(self.sync_file, "w") as f:
            json.dump(data, f, indent=2)
###########################################################################################

# -------------------------
# Classe JsonStore
# -------------------------
class JsonStore:
    def __init__(self, filename):
        self.filename = filename
        Path(os.path.dirname(filename)).mkdir(parents=True, exist_ok=True)

    def exists(self, key):
        if not os.path.exists(self.filename):
            return False
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
            return key in data
        except:
            return False

    def get(self, key):
        if not self.exists(key):
            return None
        with open(self.filename, 'r') as f:
            data = json.load(f)
        return data.get(key)

    def put(self, key, **kwargs):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    data = json.load(f)
            except:
                data = {}
        else:
            data = {}
        data[key] = kwargs
        with open(self.filename, 'w') as f:
            json.dump(data, f)

    def delete(self, key):
        if not self.exists(key):
            return
        with open(self.filename, 'r') as f:
            data = json.load(f)
        data.pop(key, None)
        with open(self.filename, 'w') as f:
            json.dump(data, f)


# -------------------------
# Classe MultiUserStore
# -------------------------
class MultiUserStore:
    def __init__(self):
        self.storage_dir = "user_sessions"
        os.makedirs(self.storage_dir, exist_ok=True)

    def get_user_store(self, username):
        filename = os.path.join(self.storage_dir, f"{username}_session.json")
        return JsonStore(filename)

    def get_current_user_store(self):
        username = st.session_state.get('username')
        if username:
            return self.get_user_store(username)
        return None

    def set_current_user(self, username, user_data):
        st.session_state['username'] = username
        st.session_state['user_data'] = user_data
        user_store = self.get_user_store(username)
        user_store.put('user', **user_data)

    def clear_current_user(self):
        username = st.session_state.get('username')
        if username:
            user_store = self.get_user_store(username)
            user_store.delete('user')
        st.session_state.pop('username', None)
        st.session_state.pop('user_data', None)


# Initialisation globale
multi_store = MultiUserStore()


# -------------------------
# Fonctions HTTP
# -------------------------
def make_request(method, endpoint, **kwargs):
    global multi_store
    if 'username' not in st.session_state:
        logger.error("No active user session")
        st.error("⚠️ Aucune session utilisateur active. Veuillez vous reconnecter.")
        return None

    user_store = multi_store.get_current_user_store()
    if not user_store or not user_store.exists('user'):
        logger.error("Invalid user session")
        st.error("⚠️ Session utilisateur invalide. Veuillez vous reconnecter.")
        return None

    user = user_store.get('user')
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {user['access_token']}"

    # Convert any int64 in json data to Python int
    if 'json' in kwargs:
        kwargs['json'] = convert_int64_to_int(kwargs['json'])

    for attempt in range(3):  # Retry up to 3 times
        try:
            logger.info(f"Making {method} request to {BASE_URL + endpoint} (Attempt {attempt + 1})")
            response = requests.request(method, BASE_URL + endpoint, headers=headers, **kwargs)
            logger.debug(f"Response status: {response.status_code}, content: {response.text}")
            try:
                response_data = response.json()
                if isinstance(response_data, list) and len(response_data) > 1 and response_data[1] == 401:
                    logger.warning("Session expired, attempting to refresh token")
                    res = refresh_token()
                    if res:
                        user = user_store.get('user')
                        logger.info(f"Refreshed user data: {user}")
                        headers["Authorization"] = f"Bearer {user['access_token']}"
                        # Reconvert json data after refresh
                        if 'json' in kwargs:
                            kwargs['json'] = convert_int64_to_int(kwargs['json'])
                        response = requests.request(method, BASE_URL + endpoint, headers=headers, **kwargs)
                        logger.debug(f"Retry response status: {response.status_code}, content: {response.text}")
                        return response
                    else:
                        logger.error("Failed to refresh token")
                        st.error("❌ Impossible de rafraîchir le token. Veuillez vous reconnecter.")
                        return None
                return response
            except ValueError:
                logger.error(f"Invalid JSON response: {response.text}")
                st.error("Réponse serveur invalide")
                return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            if attempt < 2:
                logger.info("Retrying request...")
                time.sleep(1)
                continue
            st.error(f"Erreur de requête après {attempt + 1} tentatives : {e}")
            return None


def convert_int64_to_int(data):
    """Convert numpy int64 to Python int in a dictionary or list."""
    if isinstance(data, dict):
        return {k: convert_int64_to_int(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_int64_to_int(item) for item in data]
    elif isinstance(data, np.int64):
        return int(data)
    return data


def refresh_token():
    global multi_store
    if 'username' not in st.session_state:
        logger.error("No username in session state for token refresh")
        return False

    user_store = multi_store.get_current_user_store()
    if not user_store or not user_store.exists('user'):
        logger.error("User store not found or no user data")
        return False

    user = user_store.get('user')
    refresh_token_value = user.get('refresh_token')
    if not refresh_token_value:
        logger.error("No refresh token available")
        return False

    url = BASE_URL + "/auth/refreshtoken"
    headers = {"Authorization": f"Bearer {refresh_token_value}"}
    try:
        logger.info(f"Refreshing token at {url}")
        response = requests.get(url, headers=headers, timeout=10)
        logger.debug(f"Refresh token response: {response.status_code}, {response.text}")
        response_data = response.json()
        if isinstance(response_data, list) and len(response_data) > 1 and response_data[1] == 200:
            data = response_data[0]
            access_token = data.get("access_token")
            username = data.get("username")
            role = data.get("role")
            if not all([access_token, username, role]):
                logger.error("Incomplete token data")
                st.error("Données de token incomplètes")
                return False
            user_store.put(
                'user',
                username=username,
                access_token=access_token,
                refresh_token=refresh_token_value,
                role=role
            )
            logger.info("Token refreshed successfully")
            return True
        else:
            logger.error(f"Token refresh failed: {response.status_code}, {response.text}")
            st.error(f"Échec du refresh : {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        st.error(f"Erreur lors du refresh : {e}")
        return False


# -------------------------
# Initialisation session Streamlit
# -------------------------
def extract_payload(data, key):
    """Gère les formats [ {…}, 200 ], [ {…} ], ou {…}."""
    if isinstance(data, list):
        if len(data) > 1 and data[1] == 200 and isinstance(data[0], dict):
            return data[0].get(key, [])
        if len(data) > 0 and isinstance(data[0], dict):
            return data[0].get(key, [])
        return []
    if isinstance(data, dict):
        return data.get(key, [])
    return []


def initialize_session_state():
    defaults = {
        'current_screen': "login",
        'selected_models': [],
        'current_model_index': 0,
        'last_model_change': time.time(),
        'checked_rows': [],
        'menu_open': False,
        'socket_connected': False,
        'socket_events': [],
        'last_event_check': 0.0
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


# Call initialize_session_state at the start
initialize_session_state()

# Styles CSS
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: bold; color: #226666; text-align: center; margin-bottom: 2rem; }
    .card { background-color: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); margin-bottom: 1rem; }
    .sidebar .sidebar-content { background-color: #f8f9fa; }
    .metric-card { background-color: #f8f9fa; padding: 1rem; border-radius: 10px; text-align: center; margin: 0.5rem; }
    .chart-container { border: 1px solid #e0e0e0; border-radius: 10px; padding: 1rem; background-color: #ffffff; margin-bottom: 1rem; }
    .subheader { font-size: 1.5rem; color: #226666; font-weight: bold; margin-top: 1rem; }
    .tv-metric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 0.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.2rem;
        animation: fadeInScale 0.5s ease-out;
        transition: transform 0.3s ease, opacity 0.3s ease;
    }
    .tv-metric:hover {
        transform: scale(1.05);
        opacity: 0.95;
    }
    .tv-metric h3 {
        font-size: 0.9rem;
        margin: 0;
        font-weight: 600;
    }
    .tv-metric .value {
        font-size: 1.8rem;
        font-weight: bold;
        margin: 0.2rem 0;
    }
    .tv-metric .delta {
        font-size: 0.9rem;
        font-weight: 500;
    }
    .progress-bar {
        height: 8px;
        background: #e0e0e0;
        border-radius: 4px;
        margin: 0.5rem 0;
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #4CAF50, #8BC34A);
        transition: width 1s ease-in-out;
        animation: progressPulse 2s infinite ease-in-out;
    }
    .section-title {
        font-size: 1.2rem;
        font-weight: bold;
        color: #2c3e50;
        margin: 0.5rem 0;
        border-left: 4px solid #3498db;
        padding-left: 0.5rem;
        animation: slideInLeft 0.5s ease-out;
    }
    .absent-badge {
        background: linear-gradient(135deg, #ff6b6b, #ee5a52);
        color: white;
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        font-size: 1.3rem;
        font-weight: bold;
        margin: 0.3rem;
        display: inline-block;
        text-align: center;
        min-width: 120px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        animation: bounceIn 0.6s ease-out;
        transition: transform 0.3s ease;
    }
    .absent-badge:hover {
        transform: scale(1.05);
        transition: transform 0.2s;
    }
    .absent-section {
        background: linear-gradient(135deg, #f8f9fa, #e9ecef);
        padding: 0.8rem;
        border-radius: 10px;
        margin-top: 0.5rem;
    }
    .chart-container {
        animation: fadeIn 0.5s ease-out;
        transition: opacity 0.5s ease;
    }
    .model-indicator {
        background: linear-gradient(135deg, #3498db, #2980b9);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 1.1rem;
        font-weight: bold;
        text-align: center;
        margin: 1rem 0;
    }
    @keyframes fadeInScale {
        0% { opacity: 0; transform: scale(0.9); }
        100% { opacity: 1; transform: scale(1); }
    }
    @keyframes slideInLeft {
        0% { opacity: 0; transform: translateX(-20px); }
        100% { opacity: 1; transform: translateX(0); }
    }
    @keyframes bounceIn {
        0% { opacity: 0; transform: scale(0.3); }
        50% { opacity: 1; transform: scale(1.1); }
        100% { transform: scale(1); }
    }
    @keyframes progressPulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }
    @keyframes fadeIn {
        0% { opacity: 0; }
        100% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)


# ----------------------
# Socket.IO
# ----------------------
def setup_socket_io():
    if not st.session_state.get('socket_connected', False):
        try:
            sio.connect("http://192.168.1.210:5001")
            st.session_state.socket_connected = True

            @sio.on('connect')
            def on_connect():
                enqueue_socket_event('connect')

            @sio.on('disconnect')
            def on_disconnect():
                enqueue_socket_event('disconnect')

            @sio.on('production_scan')
            def on_production_scan(data):
                enqueue_socket_event('production_scan', data)

            @sio.on('of_lance')
            def on_of_lance(data):
                enqueue_socket_event('of_lance', data)

            @sio.on('worker_absence')
            def on_worker_absence(data):
                enqueue_socket_event('worker_absence', data)

        except Exception as e:
            logger.error(f"Socket connection failed: {e}")


# ----------------------
# Fonctions utilitaires
# ----------------------
def show_popup(title, message, type="info"):
    logger.info(f"Showing popup: {type} - {title}: {message}")
    if type == "error":
        st.error(f"**{title}**: {message}")
    elif type == "success":
        st.success(f"**{title}**: {message}")
    else:
        st.info(f"**{title}**: {message}")


def get_objectif_for_today(ofs):
    jours_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    numero_jour = datetime.today().weekday()
    jour_aujourd_hui = jours_fr[numero_jour]
    obj_mapping = {
        "Lundi": "nbPaireLundi", "Mardi": "nbPaireMardi", "Mercredi": "nbPaireMercredi",
        "Jeudi": "nbPaireJeudi", "Vendredi": "nbPaireVendredi", "Samedi": "nbPaireSamedi"
    }
    try:
        objectif = int(ofs.get(obj_mapping.get(jour_aujourd_hui, "nbPaireLundi"), 0))
        logger.info(f"Calculated objective for today: {objectif}")
        return objectif
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid objective data: {e}")
        st.warning("Objectif du jour invalide, défini à 0")
        return 0


def get_regime_horaire_du_jour(of_data):
    """Récupère le régime horaire spécifique du jour actuel"""
    try:
        jours_fr_to_en = {
            'Lundi': 'Monday',
            'Mardi': 'Tuesday',
            'Mercredi': 'Wednesday',
            'Jeudi': 'Thursday',
            'Vendredi': 'Friday',
            'Samedi': 'Saturday',
            'Dimanche': 'Sunday'
        }

        jour_actuel_en = datetime.today().strftime('%A')  # 'Monday', 'Tuesday', etc.

        # Mapping des colonnes dans vos données
        colonnes_horaire = {
            'Monday': 'horaireLundi',
            'Tuesday': 'horaireMardi',
            'Wednesday': 'horaireMercredi',
            'Thursday': 'horaireJeudi',
            'Friday': 'horaireVendredi',
            'Saturday': 'horaireSamedi'
        }

        colonne_horaire = colonnes_horaire.get(jour_actuel_en)
        if colonne_horaire and colonne_horaire in of_data:
            regime_du_jour = of_data[colonne_horaire]
            logger.info(f"Régime horaire du jour ({jour_actuel_en}): {regime_du_jour}")
            return regime_du_jour
        else:
            logger.warning(f"Aucun horaire trouvé pour {jour_actuel_en}, utilisation du régime général")
            return of_data.get("regimeHoraire", 48)

    except Exception as e:
        logger.error(f"Erreur récupération régime horaire: {e}")
        return of_data.get("regimeHoraire", 48)


def calculer_heure_fin_local(regime_horaire_str):
    """Calcule l'heure de fin localement sans appel API"""
    try:
        logger.info(f"Calculating end time locally for regime: {regime_horaire_str}")

        if not regime_horaire_str:
            logger.warning("No regime horaire provided, using default 16:30")
            return "16:30"

        # Nettoyage de la chaîne
        horaire_str = str(regime_horaire_str).lower().replace('h', '').strip()

        # Conversion en float
        try:
            regime_decimal = float(horaire_str)
        except ValueError:
            logger.warning(f"Invalid regime format: {horaire_str}, using default")
            return "16:30"

        # Calcul des heures et minutes
        heures_entieres = int(regime_decimal)
        minutes = int(round((regime_decimal - heures_entieres) * 60))

        # Heure de début fixe à 07:30
        heure_debut = datetime.strptime("07:30", "%H:%M")
        date_fin = heure_debut + timedelta(hours=heures_entieres, minutes=minutes)

        heure_fin_str = date_fin.strftime("%H:%M")
        logger.info(f"Calculated end time: {heure_fin_str} (from {regime_decimal}h)")

        return heure_fin_str

    except Exception as e:
        logger.error(f"Error in local end time calculation: {e}")
        return "16:30"


# ----------------------
# Chart Functions
# ----------------------
@st.cache_data
def create_production_chart(productions, objectif_total, regime_horaire, modele, user_role):
    logger.info(f"Creating production chart with {len(productions)} productions, objectif: {objectif_total}")
    if not productions:
        logger.warning("No production data available for chart")
        st.warning("Aucune donnée de production disponible pour le graphique.")
        return None

    # Calcul dynamique de l'heure de fin
    start_time = datetime.strptime("07:30", "%H:%M")

    # Récupérer l'heure de fin calculée
    if regime_horaire:
        heure_fin_str = calculer_heure_fin_local(str(regime_horaire))
    else:
        heure_fin_str = "16:30"

    try:
        end_time = datetime.strptime(heure_fin_str, "%H:%M")
    except ValueError:
        end_time = datetime.strptime("16:30", "%H:%M")
        heure_fin_str = "16:30"

    times = []
    values = []
    valid_productions = []

    for p in productions:
        try:
            heure_obj = datetime.strptime(p["horaireScan"], "%H:%M:%S")
            heure_hm = heure_obj.strftime("%H:%M")
            nb_paires = int(p["nbPaireEncour"]) if p.get("nbPaireEncour") is not None else 0
            if nb_paires < 0:
                logger.warning(f"Negative nbPaireEncour detected: {nb_paires}, ignored")
                st.warning(f"Valeur négative détectée pour nbPaireEncour : {nb_paires}, ignorée.")
                continue
            times.append(heure_obj)
            values.append(nb_paires)
            valid_productions.append({"heure": heure_hm, "nb_paires": nb_paires})
        except (ValueError, KeyError, TypeError) as e:
            logger.warning(f"Invalid production data: {e}")
            st.warning(f"Données de production invalides : {str(e)}")
            continue

    if not times:
        times = [start_time, end_time]
        values = [0, 0]
    else:
        times = [start_time] + times + [end_time]
        values = [0] + values + [values[-1]]

    fig, ax = plt.subplots(figsize=(10, 5), dpi=100)

    production_color = 'blue'
    objectif_color = 'red'

    if valid_productions:
        time_labels = [t.strftime("%H:%M") for t in times]
        ax.plot(time_labels, values, '-o', linewidth=2, markersize=8, color=production_color,
                label="Production")
        for i, (x, y) in enumerate(zip(time_labels, values)):
            if i > 0 and i < len(values) - 1:
                ax.annotate(f'{y} paires', (x, y), textcoords="offset points",
                            xytext=(0, 10), ha='center',
                            bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.8))

    ax.plot([time_labels[0], time_labels[-1]], [0, objectif_total], '--',
            linewidth=2, color=objectif_color, label="Objectif")

    # Ajouter l'information de l'heure de fin calculée
    ax.axvline(x=time_labels[-1], color='green', linestyle=':', alpha=0.7,
               label=f"Fin: {heure_fin_str}")

    ax.set_xlabel("Heure")
    ax.set_ylabel("Paires produites")
    ax.set_title(f"Production: {values[-1]}/{objectif_total} paires (Fin: {heure_fin_str})")
    ax.legend(loc='upper left')
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.set_ylim(0, max(max(values), objectif_total) * 1.2)
    plt.xticks(rotation=45)
    plt.tight_layout()
    logger.info(f"Production chart created successfully with end time: {heure_fin_str}")
    return fig


@st.cache_data
def create_pie_chart(stats_data):
    logger.info(f"Creating pie chart with stats: {stats_data}")
    if not stats_data or sum(stats_data) == 0:
        logger.warning("No valid data for pie chart")
        st.warning("Aucune donnée valide pour générer le diagramme circulaire.")
        return None

    labels = ["En attente", "En cours", "Terminés"]
    colors = ["#e9c46a", "#2a9d8f", "#264653"]
    values = stats_data
    total_paires = sum(values)

    def autopct_label(pct, allvals):
        absolute = int(round(pct / 100. * sum(allvals)))
        return f"{pct:.1f}%\n({absolute})"

    fig, ax = plt.subplots(figsize=(5, 5), dpi=100)
    fig.subplots_adjust(left=0.05, right=0.80, top=0.90, bottom=0.05)
    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        colors=colors,
        autopct=lambda pct: autopct_label(pct, values),
        startangle=90,
        shadow=True,
        wedgeprops={'linewidth': 1, 'edgecolor': 'white'},
        textprops={'fontsize': 14, 'color': 'white'},
        labeldistance=1.05,
        pctdistance=0.75
    )
    ax.legend(
        wedges,
        [f"{lbl} : {val} paires" for lbl, val in zip(labels, values)],
        title="Détails",
        loc="upper right",
        bbox_to_anchor=(0.70, 0, 0.5, 1),
        fontsize=14
    )
    ax.text(
        0, -1.35,
        f"Nombre total de paires : {total_paires}",
        ha='center',
        fontsize=14,
        color='black',
        weight='bold'
    )
    ax.set_title("Production total des paires", fontsize=16, weight='bold', pad=10)
    ax.axis('equal')
    plt.tight_layout()
    logger.info("Pie chart created successfully")
    return fig


def create_compact_production_chart(productions, objectif_total, regime_horaire, modele, user_role):
    """Version avec calcul local de l'heure de fin"""
    try:
        logger.info(f"Creating production chart with {len(productions)} productions, objectif: {objectif_total}")

        if not productions:
            logger.warning("No production data available for chart")
            return None

        # Calcul LOCAL de l'heure de fin
        start_time = datetime.strptime("07:30", "%H:%M")

        # Utilisez le régime_horaire directement pour le calcul
        if regime_horaire:
            heure_fin_str = calculer_heure_fin_local(str(regime_horaire))
        else:
            # Fallback basé sur le type de régime (48h = 16:30, autre = 14:30)
            heure_fin_str = "16:30" if regime_horaire == 48 else "14:30"

        try:
            end_time = datetime.strptime(heure_fin_str, "%H:%M")
            logger.info(f"Using calculated end time: {heure_fin_str}")
        except ValueError:
            end_time = datetime.strptime("16:30", "%H:%M")
            heure_fin_str = "16:30"
            logger.warning(f"Invalid end time format, using fallback: {heure_fin_str}")

        times = []
        values = []
        valid_productions = []

        # Traitement des données de production
        for p in productions:
            try:
                if not p or not isinstance(p, dict):
                    continue

                heure_scan = p.get("horaireScan")
                nb_paires = p.get("nbPaireEncour")

                if not heure_scan or nb_paires is None:
                    continue

                heure_obj = datetime.strptime(heure_scan, "%H:%M:%S")
                nb_paires_int = int(nb_paires)

                if nb_paires_int < 0:
                    logger.warning(f"Negative nbPaireEncour detected: {nb_paires_int}, ignored")
                    continue

                times.append(heure_obj)
                values.append(nb_paires_int)
                valid_productions.append({
                    "heure": heure_obj.strftime("%H:%M"),
                    "nb_paires": nb_paires_int
                })

            except (ValueError, KeyError, TypeError) as e:
                logger.warning(f"Invalid production data: {e}, data: {p}")
                continue

        # Construction des données pour le graphique
        if not times:
            times = [start_time, end_time]
            values = [0, 0]
        else:
            times = [start_time] + times + [end_time]
            values = [0] + values + [values[-1]]

        # Création du graphique
        fig, ax = plt.subplots(figsize=(12, 5), dpi=100)
        production_color = '#3498db'
        objectif_color = '#e74c3c'

        if valid_productions:
            time_labels = [t.strftime("%H:%M") for t in times]
            ax.plot(time_labels, values, '-o', linewidth=3, markersize=8, color=production_color,
                    label="Production réelle", alpha=0.8, markerfacecolor='white', markeredgewidth=2)

            # Annotations des points de scan
            for i, (x, y) in enumerate(zip(time_labels, values)):
                if i > 0 and i < len(values) - 1:
                    ax.annotate(f'{y}p',
                                (x, y),
                                textcoords="offset points",
                                xytext=(0, 12),
                                ha='center',
                                va='bottom',
                                fontsize=10,
                                fontweight='bold',
                                bbox=dict(boxstyle='round,pad=0.3',
                                          facecolor='lightyellow',
                                          edgecolor='gray',
                                          alpha=0.8),
                                arrowprops=dict(arrowstyle='->',
                                                connectionstyle='arc3,rad=0.1',
                                                color='gray',
                                                alpha=0.6))

        # Ligne d'objectif
        time_labels = [t.strftime("%H:%M") for t in times]
        ax.plot([time_labels[0], time_labels[-1]], [0, objectif_total], '--',
                linewidth=2, color=objectif_color, label=f"Objectif: {objectif_total} paires")

        # Ligne verticale pour l'heure de fin
        ax.axvline(x=time_labels[-1], color='green', linestyle=':', alpha=0.7,
                   linewidth=2, label=f"Fin prévue: {heure_fin_str}")

        # Configuration du graphique
        ax.set_xlabel("Heure", fontsize=12, fontweight='bold')
        ax.set_ylabel("Paires produites", fontsize=12, fontweight='bold')

        current_production = values[-1] if values else 0
        achievement = (current_production / objectif_total * 100) if objectif_total > 0 else 0

        ax.set_title(
            f"PRODUCTION: {current_production}/{objectif_total} paires ({achievement:.1f}%) - Fin: {heure_fin_str}",
            fontsize=14, fontweight='bold', pad=15)

        ax.legend(loc='upper left', fontsize=11)
        ax.grid(True, linestyle='--', alpha=0.7)

        y_max = max(max(values) if values else 0, objectif_total) * 1.2
        ax.set_ylim(0, y_max if y_max > 0 else 100)

        plt.xticks(rotation=45, fontsize=10)
        plt.yticks(fontsize=10)
        plt.tight_layout()

        logger.info(f"Production chart created successfully with local end time calculation")
        return fig

    except Exception as e:
        logger.error(f"Error creating production chart: {e}")
        # Retourner un graphique d'erreur simple
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.text(0.5, 0.5, 'Erreur de chargement des données',
                horizontalalignment='center', verticalalignment='center',
                transform=ax.transAxes, fontsize=14)
        ax.set_facecolor('#f8f9fa')
        return fig


def create_compact_pie_chart(stats_data):
    """Version agrandie du pie chart"""
    if not stats_data or sum(stats_data) == 0:
        return None

    labels = ["En attente", "En cours", "Terminés"]
    colors = ["#f39c12", "#3498db", "#27ae60"]
    values = stats_data

    fig, ax = plt.subplots(figsize=(6, 5), dpi=100)
    plt.subplots_adjust(left=0.1, right=0.9, top=0.85, bottom=0.15)

    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        colors=colors,
        autopct='%1.0f%%',
        startangle=90,
        wedgeprops={'linewidth': 2, 'edgecolor': 'white'},
        textprops={'fontsize': 12, 'color': 'white', 'weight': 'bold'}
    )

    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_weight('bold')
        autotext.set_fontsize(12)

    for text in texts:
        text.set_fontsize(12)

    ax.set_title("RÉPARTITION OF", fontsize=14, fontweight='bold', pad=20)
    ax.axis('equal')

    return fig


# -------------------------
# Synchronisation de selected_models
# -------------------------
def sync_selected_models(username):
    user_store = multi_store.get_user_store(username)
    user_data = user_store.get('user')
    if not user_data:
        logger.error("No user data found for sync_selected_models")
        return None, None

    # Gestion multi-modèles
    if 'modelesSelectionnes' in user_data:
        if 'selected_models' not in st.session_state or st.session_state['selected_models'] != user_data[
            'modelesSelectionnes']:
            st.session_state['selected_models'] = user_data['modelesSelectionnes']
            logger.info(f"Synchronized selected_models: {st.session_state['selected_models']}")

    return user_store, user_data


# ----------------------
# Écrans de l'application
# ----------------------
def login_screen():
    st.markdown('<div class="main-header">Bienvenue !</div>', unsafe_allow_html=True)
    with st.form("login_form"):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Connexion")
            login_val = st.text_input("Nom d'utilisateur")
            password_val = st.text_input("Mot de passe", type="password")
            login_error = st.empty()
            password_error = st.empty()
            if st.form_submit_button("Se connecter"):
                if not login_val:
                    login_error.error("Veuillez entrer un nom d'utilisateur")
                if not password_val:
                    password_error.error("Veuillez entrer un mot de passe")
                if login_val and password_val:
                    try:
                        logger.info(f"Attempting login for user: {login_val}")
                        response = requests.post(
                            BASE_URL + "/auth/login",
                            json={"username": login_val, "password": password_val}
                        )
                        logger.debug(f"Login response: {response.status_code}, {response.text}")
                        if response.status_code == 200:
                            data = response.json()
                            if isinstance(data, list) and len(data) > 0:
                                data = data[0]
                            elif not isinstance(data, dict):
                                logger.error("Unexpected login response format")
                                st.error("Format de réponse inattendu du serveur")
                                return

                            user_store = multi_store.get_user_store(login_val)
                            user_store.put('user',
                                           username=data.get("username"),
                                           access_token=data.get("access_token"),
                                           refresh_token=data.get("refresh_token"),
                                           role=data.get("role"),
                                           login_time=datetime.now().isoformat())

                            st.session_state.username = login_val
                            st.session_state.user_data = user_store.get('user')
                            st.session_state.current_screen = "main"
                            logger.info(f"User {login_val} logged in successfully")
                            setup_socket_io()
                            st.rerun()
                        else:
                            logger.error(f"Login failed: {response.status_code}, {response.text}")
                            st.error("Nom d'utilisateur ou mot de passe incorrect")
                    except Exception as e:
                        logger.error(f"Login server connection error: {e}")
                        st.error(f"Impossible de se connecter au serveur : {str(e)}")
            st.markdown('</div>', unsafe_allow_html=True)


def main_screen():
    with st.sidebar:
        st.title("Navigation")
        if st.button("🏠 Lancement"):
            st.session_state.current_screen = "launch"
            st.rerun()
        if st.button("🔄 En cours"):
            st.session_state.current_screen = "in_progress"
            st.rerun()
        if st.button("✅ Terminés"):
            st.session_state.current_screen = "done"
            st.rerun()
        if st.button("👥 Absences"):
            st.session_state.current_screen = "absence"
            st.rerun()
        if st.button("📊 Dashboard"):
            st.session_state.current_screen = "dashboard"
            st.rerun()
        if st.button("🚪 Déconnexion"):
            logger.info("User logging out")
            if 'username' in st.session_state:
                st.session_state.clear()
            if st.session_state.get('socket_connected', False):
                sio.disconnect()
                st.session_state.socket_connected = False
            st.session_state.current_screen = "login"
            st.rerun()

    if st.session_state.get('socket_connected', False):
        st.sidebar.success("✅ Connecté en temps réel")
    else:
        st.sidebar.warning("❌ Hors ligne")

    st.title("Tableau de bord principal")
    username = st.session_state.get('username')
    if username:
        user_store = multi_store.get_user_store(username)
        if user_store.exists('user'):
            user_data = user_store.get('user')
            st.write(f"Bienvenue **{user_data['username']}** ({user_data['role']})")

            # Afficher les modèles sélectionnés
            selected_models = st.session_state.get('selected_models', [])
            if selected_models:
                st.write(f"**Modèles sélectionnés:** {', '.join(selected_models)}")
            else:
                st.info("Aucun modèle sélectionné. Allez dans 'Lancement' pour choisir des modèles.")

            logger.info(f"Main screen displayed for user: {user_data['username']}")


def in_progress_screen():
    st.title("OFs en cours")
    if st.button("← Retour"):
        st.session_state.current_screen = "main"
        st.rerun()

    username = st.session_state.get('username')
    if not username:
        logger.error("No user session found in in_progress_screen")
        st.error("Session utilisateur non trouvée")
        return

    user_store = multi_store.get_user_store(username)
    user_data = user_store.get('user')
    user_role = user_data.get('role', '')

    response = make_request("get", "/manage_ofs/get_ofs_en_cours_by_chaine", json={"chaine": user_role})
    if response and response.status_code == 200:
        try:
            response_data = response.json()
            logger.debug(f"OFs en cours response: {response_data}")
            if isinstance(response_data, list) and len(response_data) > 1 and response_data[1] == 200:
                ofs_data = response_data[0].get('ofs', [])
            else:
                ofs_data = response_data[0].get('ofs', []) if response_data else []

            if ofs_data:
                obj = get_objectif_for_today(ofs_data[0])
                st.success(f"Votre objectif pour aujourd'hui est de {obj} paires")
                df = pd.DataFrame(ofs_data)
                st.dataframe(
                    df[['numCommandeOF', 'Pointure', 'Quantite', 'etat', 'SAIS', 'dateLancement_of_chaine']],
                    width="stretch"
                )
            else:
                logger.info("No OFs en cours found")
                st.info("Aucun OF en cours pour le moment")
        except Exception as e:
            logger.error(f"Error processing OFs en cours data: {e}")
            st.error(f"Erreur lors du traitement des données : {e}")
    else:
        logger.error(f"Failed to fetch OFs en cours: {response.status_code if response else 'No response'}")
        show_popup("Erreur", "Impossible de récupérer les OFs en cours", "error")


def done_screen():
    st.title("OFs terminés")
    if st.button("← Retour"):
        st.session_state.current_screen = "main"
        st.rerun()

    username = st.session_state.get('username')
    if not username:
        logger.error("No user session found in done_screen")
        st.error("Session utilisateur non trouvée")
        return

    user_store = multi_store.get_user_store(username)
    user_data = user_store.get('user')
    user_role = user_data.get('role', '')

    selected_date = st.date_input("Sélectionnez une date", value=date.today())
    data = {"date": selected_date.strftime("%d/%m/%Y"), "chaine": user_role}
    response = make_request("get", "/manage_ofs/get_ofs_termine_by_chaine_and_doneDate", json=data)
    if response and response.status_code == 200:
        try:
            response_data = response.json()
            logger.debug(f"OFs terminés response: {response_data}")
            if isinstance(response_data, list) and len(response_data) > 1 and response_data[1] == 200:
                ofs_data = response_data[0].get('ofs', [])
            else:
                ofs_data = response_data[0].get('ofs', []) if response_data else []

            if ofs_data:
                df = pd.DataFrame(ofs_data)
                st.dataframe(
                    df[['numCommandeOF', 'Pointure', 'Quantite', 'etat', 'SAIS', 'dateLancement_of_chaine']],
                    width="stretch"
                )
            else:
                logger.info(f"No OFs terminés for date: {selected_date}")
                st.info(f"Aucun OF terminé pour la date {selected_date.strftime('%d/%m/%Y')}")
        except Exception as e:
            logger.error(f"Error processing OFs terminés data: {e}")
            st.error(f"Erreur lors du traitement des données : {e}")
    else:
        logger.error(f"Failed to fetch OFs terminés: {response.status_code if response else 'No response'}")
        show_popup("Erreur", "Impossible de récupérer les OFs terminés", "error")


def absence_screen():
    st.title("Gestion des absences")
    if st.button("← Retour"):
        st.session_state.current_screen = "main"
        st.rerun()

    username = st.session_state.get('username')
    if not username:
        logger.error("No user session found in absence_screen")
        st.error("Session utilisateur non trouvée")
        return

    response = make_request("get", "/manage_absence/get_all_workers")
    if response and response.status_code == 200:
        try:
            response_data = response.json()
            logger.debug(f"Workers response: {response_data}")
            if isinstance(response_data, list) and len(response_data) > 1 and response_data[1] == 200:
                workers_data = response_data[0].get('workers', [])
            else:
                workers_data = response_data[0].get('workers', []) if response_data else []

            search_text = st.text_input("Rechercher un ouvrier...", help="Tapez pour rechercher")
            if workers_data:
                df = pd.DataFrame(workers_data)
                if search_text:
                    df = df[
                        df['NOM'].str.contains(search_text, case=False, na=False) |
                        df['PRENOM'].str.contains(search_text, case=False, na=False) |
                        df['MATR'].astype(str).str.contains(search_text, na=False)
                        ]

                df_display = df[['MATR', 'NOM', 'PRENOM']].copy()
                df_display['Absent'] = df['ISABSENT'] == 1
                edited_df = st.data_editor(
                    df_display,
                    column_config={
                        "Absent": st.column_config.CheckboxColumn(
                            "Absent",
                            help="Marquer comme absent",
                            default=False,
                        )
                    },
                    disabled=df_display.columns.difference(["Absent"]),
                    hide_index=True,
                    width="stretch"
                )

                if st.button("Enregistrer les modifications"):
                    for index, row in edited_df.iterrows():
                        original_row = df.iloc[index]
                        new_absence = 1 if row['Absent'] else 0
                        if new_absence != original_row['ISABSENT']:
                            data_to_update = {
                                "matr": int(original_row['MATR']),  # Convert to Python int
                                "absence": new_absence
                            }
                            update_response = make_request(
                                "put",
                                "/manage_absence/update_absence_worker",
                                json=data_to_update
                            )
                            try:
                                ok = update_response and update_response.status_code == 201
                            except Exception:
                                ok = False
                            if ok:
                                logger.info(f"Updated absence for {original_row['NOM']} {original_row['PRENOM']}")
                                show_popup("Succès",
                                           f"Statut de {original_row['NOM']} {original_row['PRENOM']} mis à jour",
                                           "success")
                            else:
                                logger.error(
                                    f"Failed to update absence for {original_row['NOM']} {original_row['PRENOM']}")
                                show_popup("succes",
                                           f" mise à jour pour {original_row['NOM']} {original_row['PRENOM']}", "error")
            else:
                logger.info("No workers found")
                st.info("Aucun ouvrier trouvé")
        except Exception as e:
            logger.error(f"Error processing workers data: {e}")
            st.error(f"Erreur lors du traitement des données : {e}")
    else:
        logger.error(f"Failed to fetch workers: {response.status_code if response else 'No response'}")
        show_popup("Erreur", "Impossible de récupérer la liste des ouvriers", "error")


def launch_screen():
    st.title("Lancement des OF")
    if st.button("← Retour"):
        st.session_state.current_screen = "main"
        st.rerun()

    username = st.session_state.get('username')
    if not username:
        logger.error("No user session found in launch_screen")
        st.error("Session utilisateur non trouvée")
        return

    user_store, user_data = sync_selected_models(username)
    if not user_data:
        logger.error("No user data found in launch_screen")
        st.error("Impossible de récupérer les données utilisateur")
        return

    user_role = user_data.get('role', '')

    # Récupération des modèles disponibles
    response = make_request("get", "/manage_ofs/get_all_waiting_models", json={"chaine": user_role})
    modeles = []
    if response and response.status_code == 200:
        try:
            data = response.json()
            logger.debug(f"Waiting models response: {data}")

            # Extraction simple des modèles
            if isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], dict):
                    modeles_data = data[0].get("modeles", [])
                    modeles = [str(item["Modele"]).strip() for item in modeles_data if "Modele" in item]

            # Nettoyage
            modeles = [m for m in modeles if m and m != "None"]
            modeles = list(dict.fromkeys(modeles))

            logger.info(f"Modèles disponibles: {modeles}")

        except Exception as e:
            logger.error(f"Error processing models data: {e}")
            st.error(f"Erreur lors du traitement des données : {e}")

    if modeles:
        # MULTISELECT pour sélectionner plusieurs modèles
        selected_models = st.multiselect(
            "Sélectionnez un ou plusieurs modèles",
            modeles,
            default=st.session_state.get('selected_models', [])
        )

        if st.button("Confirmer la sélection"):
            if selected_models:
                st.session_state.selected_models = selected_models
                st.session_state.current_model_index = 0
                st.session_state.last_model_change = time.time()
                user_data['modelesSelectionnes'] = selected_models
                user_store.put('user', **user_data)
                logger.info(f"Selected models: {selected_models}")
                st.success(f"Modèles sélectionnés: {', '.join(selected_models)}")
                st.rerun()
            else:
                st.warning("Veuillez sélectionner au moins un modèle")
    else:
        logger.info("No models available to launch")
        st.info("Vous n'avez pas de modèle à lancer aujourd'hui")
        return

    # Affichage des OFs pour les modèles sélectionnés
    selected_models = st.session_state.get('selected_models', [])
    if selected_models:
        st.subheader(f"OFs disponibles pour les modèles sélectionnés")

        all_ofs_data = []
        for modele in selected_models:
            logger.info(f"Fetching OFs for model: {modele}")
            response = make_request("get", "/manage_ofs/getofsChainesbychaine", json={"modele": modele})

            if response and response.status_code == 200:
                try:
                    data = response.json()
                    logger.debug(f"OFs response for {modele}: {data}")

                    # Extraction des OFs - CORRECTION ICI
                    ofs_data = []
                    if isinstance(data, list) and len(data) > 0:
                        # Gérer différents formats de réponse
                        if isinstance(data[0], dict):
                            if 'ofs' in data[0]:
                                ofs_data = data[0].get("ofs", [])
                            else:
                                # Si la réponse est directement la liste des OFs
                                ofs_data = data
                        else:
                            ofs_data = data

                    # Ajouter le modèle à chaque OF et logger le détail
                    logger.info(f"OFs trouvés pour {modele}: {len(ofs_data)}")
                    for of in ofs_data:
                        if isinstance(of, dict) and of.get('numCommandeOF'):
                            of['ModeleInterne'] = modele  # Utiliser un nom différent pour éviter les conflits
                            all_ofs_data.append(of)
                            logger.debug(f"OF ajouté: {of.get('numCommandeOF')} - Modèle: {modele}")

                except Exception as e:
                    logger.error(f"Error processing OFs for model {modele}: {e}")
                    st.error(f"Erreur pour le modèle {modele}: {e}")

        # AFFICHAGE AVEC TOUS LES OFs - CORRECTION CRITIQUE
        if all_ofs_data:
            logger.info(f"Total OFs à afficher: {len(all_ofs_data)}")

            # Créer le DataFrame avec toutes les données
            df = pd.DataFrame(all_ofs_data)

            # COLONNES À AFFICHER
            display_columns = ['numCommandeOF', 'Pointure', 'Quantite', 'etat', 'SAIS', 'ModeleInterne']

            # Filtrer les colonnes existantes
            available_columns = [col for col in display_columns if col in df.columns]
            df_display = df[available_columns].copy()
            df_display['Sélectionner'] = False

            # Afficher le nombre total d'OFs trouvés
            st.info(f"**{len(all_ofs_data)} OF(s) trouvé(s) pour les modèles sélectionnés**")

            # Affichage avec la colonne Modèle pour debug
            edited_df = st.data_editor(
                df_display,
                column_config={
                    "Sélectionner": st.column_config.CheckboxColumn("Sélectionner", default=False),
                    "numCommandeOF": "Numéro OF",
                    "Pointure": "Pointure",
                    "Quantite": "Quantité",
                    "etat": "État",
                    "SAIS": "SAIS",
                    "ModeleInterne": "Modèle"  # Afficher le modèle pour vérification
                },
                disabled=df_display.columns.difference(["Sélectionner"]),
                hide_index=True,
                width="stretch"
            )

            # Gestion de la sélection
            selected_ofs = edited_df[edited_df['Sélectionner']]['numCommandeOF'].tolist()

            # Trouver les modèles correspondants aux OFs sélectionnés
            st.session_state.checked_rows = []
            for num_of in selected_ofs:
                # Trouver le modèle correspondant à cet OF
                for of_data in all_ofs_data:
                    if of_data['numCommandeOF'] == num_of:
                        st.session_state.checked_rows.append({
                            "numOF": int(num_of),
                            "chaine": user_role,
                            "modele": of_data['ModeleInterne']  # Modèle interne
                        })
                        logger.info(f"OF sélectionné: {num_of} - Modèle: {of_data['ModeleInterne']}")
                        break

            # Afficher le détail de la sélection
            if selected_ofs:
                st.write(f"**OFs sélectionnés:** {len(selected_ofs)}")
                for of in selected_ofs:
                    st.write(f"- {of}")

            if st.button("Lancer les OF sélectionnés"):
                if st.session_state.checked_rows:
                    logger.info(f"Lancement des OFs: {st.session_state.checked_rows}")
                    response = make_request("put", "/manage_ofs/launch_of", json=st.session_state.checked_rows)
                    if response and response.status_code == 200:
                        logger.info("OFs lancés avec succès")
                        st.success("✅ OFs lancés avec succès !")
                        st.session_state.checked_rows = []
                        st.rerun()
                    else:
                        logger.error(f"Échec lancement OFs: {response.status_code if response else 'No response'}")
                        st.error("❌ Échec du lancement des OFs")
                else:
                    st.warning("⚠️ Veuillez sélectionner au moins un OF")
        else:
            st.info("Aucun OF disponible pour les modèles sélectionnés")
            logger.info("Aucun OF trouvé après agrégation des données")

def dashboard_screen():
    # Style CSS pour le mode TV
    st.markdown("""
    <style>
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
        .tv-metric {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 0.5rem;
            border-radius: 10px;
            color: white;
            text-align: center;
            margin: 0.2rem;
            animation: fadeInScale 0.5s ease-out;
            transition: transform 0.3s ease, opacity 0.3s ease;
        }
        .tv-metric:hover {
            transform: scale(1.05);
            opacity: 0.95;
        }
        .tv-metric h3 {
            font-size: 0.9rem;
            margin: 0;
            font-weight: 600;
        }
        .tv-metric .value {
            font-size: 1.8rem;
            font-weight: bold;
            margin: 0.2rem 0;
        }
        .tv-metric .delta {
            font-size: 0.9rem;
            font-weight: 500;
        }
        .progress-bar {
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            margin: 0.5rem 0;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
            transition: width 1s ease-in-out;
            animation: progressPulse 2s infinite ease-in-out;
        }
        .section-title {
            font-size: 1.2rem;
            font-weight: bold;
            color: #2c3e50;
            margin: 0.5rem 0;
            border-left: 4px solid #3498db;
            padding-left: 0.5rem;
            animation: slideInLeft 0.5s ease-out;
        }
        .absent-badge {
            background: linear-gradient(135deg, #ff6b6b, #ee5a52);
            color: white;
            padding: 0.4rem 0.8rem;
            border-radius: 20px;
            font-size: 1.3rem;
            font-weight: bold;
            margin: 0.3rem;
            display: inline-block;
            text-align: center;
            min-width: 120px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            animation: bounceIn 0.6s ease-out;
            transition: transform 0.3s ease;
        }
        .absent-badge:hover {
            transform: scale(1.05);
        }
        .absent-section {
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            padding: 0.8rem;
            border-radius: 10px;
            margin-top: 0.5rem;
        }
        .chart-container {
            animation: fadeIn 0.5s ease-out;
            transition: opacity 0.5s ease;
        }
        .model-indicator {
            background: linear-gradient(135deg, #3498db, #2980b9);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 1.1rem;
            font-weight: bold;
            text-align: center;
            margin: 1rem 0;
        }
        .chronometer {
            background: linear-gradient(135deg, #e74c3c, #c0392b);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 1.1rem;
            font-weight: bold;
            text-align: center;
            margin: 0.5rem 0;
            animation: pulse 1s infinite;
        }
        .single-model {
            background: linear-gradient(135deg, #27ae60, #219a52);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 1.1rem;
            font-weight: bold;
            text-align: center;
            margin: 1rem 0;
        }
        @keyframes fadeInScale {
            0% { opacity: 0; transform: scale(0.9); }
            100% { opacity: 1; transform: scale(1); }
        }
        @keyframes slideInLeft {
            0% { opacity: 0; transform: translateX(-20px); }
            100% { opacity: 1; transform: translateX(0); }
        }
        @keyframes bounceIn {
            0% { opacity: 0; transform: scale(0.3); }
            50% { opacity: 1; transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        @keyframes progressPulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }
        @keyframes fadeIn {
            0% { opacity: 0; }
            100% { opacity: 1); }
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
    </style>
    """, unsafe_allow_html=True)

    if st.button("← Retour", key="dashboard_back"):
        st.session_state.current_screen = "main"
        st.rerun()

    # Initialisation Socket.IO
    if not st.session_state.get('socket_connected', False):
        try:
            setup_socket_io()
        except Exception as e:
            logger.error(f"Socket connection failed: {e}")

    username = st.session_state.get('username')
    if not username:
        st.error("Session utilisateur non trouvée")
        return

    user_store, user_data = sync_selected_models(username)
    if not user_data:
        st.error("Impossible de récupérer les données utilisateur")
        return

    # Récupération des modèles sélectionnés
    modeles = st.session_state.get('selected_models', [])
    if not modeles:
        st.warning("Veuillez sélectionner au moins un modèle dans l'écran de lancement")
        return

    user_role = user_data.get('role', '')

    # Initialiser le temps restant et le dernier changement si nécessaire
    current_time = time.time()
    if 'last_model_change' not in st.session_state:
        st.session_state.last_model_change = current_time
    if 'time_remaining' not in st.session_state:
        st.session_state.time_remaining = 300  # 5 minutes en secondes
    if 'last_update_time' not in st.session_state:
        st.session_state.last_update_time = current_time

    # Calculer le temps écoulé depuis le dernier changement de modèle
    time_elapsed = current_time - st.session_state.last_model_change
    st.session_state.time_remaining = max(0, 300 - int(time_elapsed))

    # Gestion du changement automatique de modèle toutes les 5 minutes
    if time_elapsed > 300:  # 5 minutes = 300 secondes
        st.session_state.current_model_index = (st.session_state.current_model_index + 1) % len(modeles)
        st.session_state.last_model_change = current_time
        st.rerun()

    # Sélection du modèle courant
    current_model_index = st.session_state.get('current_model_index', 0)
    modele = modeles[current_model_index]

    # Conteneur pour l'affichage du modèle et du chronomètre
    model_display_ph = st.empty()

    # Fonction pour afficher le modèle et le chronomètre
    def display_model_and_timer():
        with model_display_ph.container():
            if len(modeles) == 1:
                # Cas d'un seul modèle sélectionné
                st.markdown(f"""
                <div class="single-model">
                    📋 MODÈLE ACTUEL: {modele}
                </div>
                """, unsafe_allow_html=True)
            else:
                # Cas de plusieurs modèles - afficher le chronomètre
                minutes = st.session_state.time_remaining // 60
                seconds = st.session_state.time_remaining % 60
                time_display = f"{minutes:02d}:{seconds:02d}"

                next_model_index = (current_model_index + 1) % len(modeles)
                next_modele = modeles[next_model_index]

                st.markdown(f"""
                <div class="model-indicator">
                    📋 MODÈLE ACTUEL: {modele}
                </div>
                <div class="chronometer">
                    ⏱️ PROCHAIN MODÈLE DANS: {time_display} | Suivant: {next_modele}
                </div>
                """, unsafe_allow_html=True)

    # Afficher immédiatement le modèle et le chronomètre
    display_model_and_timer()

    # Conteneurs pour mise à jour dynamique
    header_ph = st.empty()
    production_section_ph = st.empty()
    stats_section_ph = st.empty()
    absents_section_ph = st.empty()

    def render_tv_dashboard():
        """Version optimisée pour affichage TV"""
        # Récupération des données pour le modèle courant
        response_obj = make_request("get", "/manage_ofs/getofsChainesbychaine", json={"modele": modele})
        objectif_total = 0
        regime_horaire = None

        if response_obj and response_obj.status_code == 200:
            ofs_data = extract_payload(response_obj.json(), 'ofs')
            if ofs_data:
                objectif_total = get_objectif_for_today(ofs_data[0])
                # Récupère le régime horaire spécifique du jour
                regime_horaire = get_regime_horaire_du_jour(ofs_data[0])

        response_prod = make_request(
            "get",
            "/manage_production/get_production_for_date_by_chaine_modele_date",
            json={
                "date": datetime.today().date().strftime("%Y/%m/%d"),
                "modele": modele,
                "chaine": user_role
            }
        )
        production_totale = 0
        productions = []
        if response_prod and response_prod.status_code == 200:
            productions = extract_payload(response_prod.json(), 'productions')
            for p in productions:
                try:
                    production_totale = max(production_totale, int(p.get("nbPaireEncour", 0)))
                except:
                    pass

        # VÉRIFIER ET JOUER LES SONS
        check_and_play_sounds(productions, objectif_total)

        progression = int((production_totale / objectif_total) * 100) if objectif_total else 0

        # Calcul de l'heure de fin pour l'affichage
        heure_fin_calculee = calculer_heure_fin_local(str(regime_horaire)) if regime_horaire else "16:30"

        with header_ph.container():
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.markdown(f"""
                <div class="tv-metric" style="background: linear-gradient(135deg, #3498db, #2980b9);">
                    <h3>OBJECTIF JOURNALIER</h3>
                    <div class="value">{objectif_total}</div>
                    <div class="delta">paires</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                <div class="tv-metric" style="background: linear-gradient(135deg, #2ecc71, #27ae60);">
                    <h3>PRODUCTION ACTUELLE</h3>
                    <div class="value">{production_totale}</div>
                    <div class="delta">paires</div>
                </div>
                """, unsafe_allow_html=True)

            with col3:
                progression_color = "linear-gradient(135deg, #f39c12, #e67e22)" if progression < 70 else "linear-gradient(135deg, #2ecc71, #27ae60)" if progression >= 90 else "linear-gradient(135deg, #3498db, #2980b9)"
                st.markdown(f"""
                <div class="tv-metric" style="background: {progression_color};">
                    <h3>TAUX DE RÉALISATION</h3>
                    <div class="value">{progression}%</div>
                    <div class="delta">sur objectif</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {progression}%;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col4:
                now = datetime.now().strftime("%H:%M")
                date_str = datetime.now().strftime("%d/%m/%Y")
                st.markdown(f"""
                <div class="tv-metric" style="background: linear-gradient(135deg, #9b59b6, #8e44ad);">
                    <h3>FIN PRÉVUE</h3>
                    <div class="value">{heure_fin_calculee}</div>
                    <div class="delta">{date_str}</div>
                </div>
                """, unsafe_allow_html=True)

        with production_section_ph.container():
            col_prod, col_stats = st.columns([2, 1])

            with col_prod:
                if productions or objectif_total > 0:
                    fig_prod = create_compact_production_chart(productions, objectif_total, regime_horaire, modele,
                                                               user_role)
                    if fig_prod:
                        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                        st.pyplot(fig_prod)
                        st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.info("En attente des données de production...")

            with col_stats:
                num_semaine = ""
                response_ofs = make_request("get", "/manage_ofs/get_ofs_en_cours_by_chaine", json={"chaine": user_role})
                if response_ofs and response_ofs.status_code == 200:
                    ofs_data = extract_payload(response_ofs.json(), 'ofs')
                    if ofs_data:
                        num_of = str(ofs_data[0].get("numCommandeOF", ""))
                        if len(num_of) == 6:
                            num_semaine = num_of[2:4]
                        elif len(num_of) == 8:
                            num_semaine = num_of[4:6]

                response_stats = make_request(
                    "get",
                    "/manage_ofs/get_somme_quantite_per_etat_modele_chaine",
                    json={"numof": num_semaine, "modele": modele}
                )

                if response_stats and response_stats.status_code == 200:
                    stats = extract_payload(response_stats.json(), 'statistics')
                    stat = next((s for s in stats if s["idChaine"] == user_role), None)
                    if stat:
                        fig_pie = create_compact_pie_chart([
                            stat["nb_en_attente"],
                            stat["nb_en_cours"],
                            stat["nb_termine"]
                        ])
                        if fig_pie:
                            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                            st.pyplot(fig_pie)
                            st.markdown('</div>', unsafe_allow_html=True)

                        st.markdown(f"""
                        <div style="text-align: center; margin-top: 0.5rem;">
                            <div style="display: inline-block; margin: 0 0.5rem;">
                                <div style="color: #f39c12; font-weight: bold; font-size: 1.3rem;">{stat['nb_en_attente']}</div>
                                <div style="font-size: 0.9rem;">En attente</div>
                            </div>
                            <div style="display: inline-block; margin: 0 0.5rem;">
                                <div style="color: #3498db; font-weight: bold; font-size: 1.3rem;">{stat['nb_en_cours']}</div>
                                <div style="font-size: 0.9rem;">En cours</div>
                            </div>
                            <div style="display: inline-block; margin: 0 0.5rem;">
                                <div style="color: #27ae60; font-weight: bold; font-size: 1.3rem;">{stat['nb_termine']}</div>
                                <div style="font-size: 0.9rem;">Terminés</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

        with absents_section_ph.container():
            st.markdown('<div class="section-title">👥 PERSONNEL ABSENT</div>', unsafe_allow_html=True)
            response_absents = make_request("get", "/manage_absence/get_absent_workers")
            if response_absents and response_absents.status_code == 200:
                absents = extract_payload(response_absents.json(), 'absentWorkers')
                if absents:
                    st.markdown('<div class="absent-section">', unsafe_allow_html=True)
                    cols = st.columns(4)
                    for i, worker in enumerate(absents):
                        with cols[i % 4]:
                            nom_complet = f"{worker['NOM']} {worker['PRENOM']}"
                            st.markdown(f"""
                            <div class="absent-badge">
                                {nom_complet}
                            </div>
                            """, unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown(f"""
                    <div style="text-align: center; margin-top: 0.5rem;">
                        <div style="color: #e74c3c; font-size: 1.1rem; font-weight: bold;">
                            Total absents : {len(absents)} personne(s)
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.success("✅ Aucun absent aujourd'hui")
            else:
                st.info("Chargement des données d'absence...")

    # Premier rendu
    render_tv_dashboard()

    # Boucle de mise à jour automatique
    last_full_update = time.time()
    for _ in range(43200):  # 12 heures maximum
        if st.session_state.get('current_screen') != 'dashboard':
            break

        current_time = time.time()

        # Mettre à jour le chronomètre en temps réel
        time_elapsed = current_time - st.session_state.last_model_change
        st.session_state.time_remaining = max(0, 300 - int(time_elapsed))

        # Rafraîchir l'affichage du chronomètre chaque seconde
        display_model_and_timer()

        # Vérifier si on doit changer de modèle (5 minutes)
        if time_elapsed > 300:
            st.session_state.current_model_index = (st.session_state.current_model_index + 1) % len(modeles)
            st.session_state.last_model_change = current_time
            st.rerun()

        # Traiter les événements socket et mettre à jour les données toutes les 5 secondes
        events_count = process_socket_events()
        if events_count > 0 or (current_time - last_full_update) >= 5:
            st.session_state.socket_events.clear()
            render_tv_dashboard()
            last_full_update = current_time

        time.sleep(1)


# -------------------------
# Routeur principal
# -------------------------
def main():
    global multi_store
    screens = {
        "login": login_screen,
        "main": main_screen,
        "launch": launch_screen,
        "in_progress": in_progress_screen,
        "done": done_screen,
        "absence": absence_screen,
        "dashboard": dashboard_screen
    }

    # Initialize Socket.IO for all screens except login
    if st.session_state.current_screen != "login" and not st.session_state.get('socket_connected', False):
        setup_socket_io()

    # Process socket events periodically
    process_socket_events()

    current_screen = st.session_state.current_screen
    logger.info(f"Current screen: {current_screen}")
    if current_screen in screens:
        screens[current_screen]()
    else:
        logger.error("Unknown screen detected")
        st.error("Écran inconnu")
        st.session_state.current_screen = "login"
        st.rerun()


if __name__ == "__main__":
    main()