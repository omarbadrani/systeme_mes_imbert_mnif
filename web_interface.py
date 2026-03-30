import streamlit as st
import requests
import logging
from datetime import datetime
import pymysql
import json
from pathlib import Path
import time
import threading
import os

# Configuration
DEFAULT_PORT = 8505
BASE_URL = "http://192.168.1.210:5001"
SESSIONS_FILE = Path("sessions.json")


class SessionManager:
    """Gestionnaire des sessions utilisateur"""

    def __init__(self, sessions_file=SESSIONS_FILE):
        self.sessions_file = sessions_file

    def load_sessions(self):
        if not self.sessions_file.exists():
            return {}
        try:
            with open(self.sessions_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def save_sessions(self, sessions):
        with open(self.sessions_file, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2)

    def set_user_session(self, username, access_token, refresh_token, role):
        sessions = self.load_sessions()
        sessions[username] = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "role": role,
            "last_updated": time.time()
        }
        self.save_sessions(sessions)

    def get_user_session(self, username):
        sessions = self.load_sessions()
        return sessions.get(username)


    def clear_user_session(self, username):
        sessions = self.load_sessions()
        if username in sessions:
            del sessions[username]
            self.save_sessions(sessions)


class ConnectionManager:
    """Gestionnaire de connexion et tokens"""

    def __init__(self, base_url=BASE_URL, session_manager=None):
        self.base_url = base_url
        self.session_manager = session_manager or SessionManager()
        self.connection_status = {
            "connected": True,
            "last_check": time.time(),
            "last_token_refresh": time.time()
        }

    def start_background_check(self):
        """Démarre la vérification en arrière-plan"""
        if 'background_thread_started' not in st.session_state:
            try:
                background_thread = threading.Thread(target=self._check_connection_background, daemon=True)
                background_thread.start()
                st.session_state.background_thread_started = True
                logging.info("✅ Thread de vérification démarré")
            except Exception as e:
                logging.error(f"❌ Erreur démarrage thread: {e}")

    def _check_connection_background(self):
        """Vérifie la connexion et rafraîchit le token périodiquement"""
        while True:
            try:
                response = requests.get(f"{self.base_url}/auth/health", timeout=3)
                self.connection_status["connected"] = (response.status_code == 200)

                current_time = time.time()
                if current_time - self.connection_status["last_token_refresh"] > 60:
                    if self.auto_refresh_token():
                        self.connection_status["last_token_refresh"] = current_time
                        logging.info("🔄 Token rafraîchi automatiquement en arrière-plan")

            except Exception as e:
                self.connection_status["connected"] = False
                logging.warning(f"❌ Connexion perdue: {e}")

            self.connection_status["last_check"] = time.time()
            time.sleep(10)

    def auto_refresh_token(self):
        """Rafraîchit le token automatiquement"""
        username = st.session_state.get('username')
        if not username:
            return False

        session_data = self.session_manager.get_user_session(username)
        if not session_data:
            return False

        refresh_token = session_data.get('refresh_token')
        if not refresh_token:
            return False

        url = self.base_url + "/auth/refreshtoken"
        headers = {"Authorization": f"Bearer {refresh_token}"}

        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                response_data = response.json()
                if isinstance(response_data, list) and len(response_data) > 0:
                    data = response_data[0]
                else:
                    data = response_data

                access_token = data.get("access_token")
                username = data.get("username")
                role = data.get("role")
                self.session_manager.set_user_session(username, access_token, refresh_token, role)
                return True
        except Exception as e:
            logging.error(f"❌ Erreur refresh automatique: {e}")

        return False

    def ensure_valid_token(self):
        """S'assure que le token est valide avant une opération"""
        username = st.session_state.get('username')
        if not username:
            return False

        session_data = self.session_manager.get_user_session(username)
        if not session_data:
            return False

        last_updated = session_data.get('last_updated', 0)
        if time.time() - last_updated < 240:
            return True

        return self.auto_refresh_token()

    def make_request(self, method, endpoint, max_retries=2, **kwargs):
        """Fonction de requête avec gestion automatique du token"""

        if not self.ensure_valid_token():
            logging.warning("Token invalide, tentative de rafraîchissement...")

        username = st.session_state.get('username')
        if not username:
            st.error("Session expirée. Veuillez vous reconnecter.")
            return None

        session_data = self.session_manager.get_user_session(username)
        if not session_data:
            st.error("Session introuvable. Veuillez vous reconnecter.")
            return None

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {session_data.get('access_token')}"

        for attempt in range(max_retries):
            try:
                url = self.base_url + endpoint
                response = requests.request(method, url, headers=headers, timeout=10, **kwargs)

                if response.status_code == 401:
                    logging.warning("Token expiré, tentative de rafraîchissement...")
                    if self.auto_refresh_token():
                        session_data = self.session_manager.get_user_session(username)
                        headers["Authorization"] = f"Bearer {session_data.get('access_token')}"
                        response = requests.request(method, url, headers=headers, timeout=10, **kwargs)
                        return response
                    else:
                        st.error("Session expirée. Veuillez vous reconnecter.")
                        return None

                return response

            except requests.exceptions.RequestException as e:
                logging.warning(f"Tentative {attempt + 1} échouée: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    logging.error(f"Échec après {max_retries} tentatives pour {endpoint}")

        return None

    def display_connection_status(self):
        """Affiche le statut de connexion dans la sidebar"""
        status_color = "🟢" if self.connection_status["connected"] else "🔴"
        status_text = "Connecté" if self.connection_status["connected"] else "Déconnecté"

        st.sidebar.markdown(f"{status_color} **Statut:** {status_text}")

        if not self.connection_status["connected"]:
            st.sidebar.warning("⚠️ Reconnexion automatique en cours...")


class DatabaseManager:
    """Gestionnaire de base de données"""

    def __init__(self):
        self.db_config = {
            'host': '192.168.1.210',
            'user': 'omar',
            'password': '1234',
            'database': 'mesimbertmnif',
            'charset': 'utf8mb4',
            'connect_timeout': 5
        }

    def get_connection(self, max_retries=2):
        """Établit une connexion à la base de données"""
        for attempt in range(max_retries):
            try:
                conn = pymysql.connect(**self.db_config)
                logging.info("✅ Connexion DB réussie")
                return conn
            except pymysql.Error as e:
                logging.warning(f"❌ Tentative DB {attempt + 1} échouée: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)

        logging.error(f"❌ Échec connexion DB après {max_retries} tentatives")
        raise pymysql.Error("Impossible de se connecter à la base de données")


class BarcodeProcessor:
    """Processeur de codes-barres"""

    def __init__(self, db_manager, connection_manager):
        self.db_manager = db_manager
        self.connection_manager = connection_manager

    def clean_barcode(self, barcode_text):
        """Nettoie et formate le code-barres"""
        cleaned_barcode = barcode_text.replace(')', '-').replace('!', '-').replace(' ', '')
        cleaned_barcode = '-'.join(filter(None, cleaned_barcode.split('-')))
        logging.info(f"Cleaned barcode: {barcode_text} -> {cleaned_barcode}")
        return cleaned_barcode

    def parse_barcode(self, cleaned_barcode):
        """Parse le code-barres nettoyé"""
        parts = cleaned_barcode.split('-')
        if len(parts) < 3:
            raise ValueError("Format de code-barres invalide")

        num_of = parts[0]
        pointure = parts[1]

        try:
            if len(parts) > 3 and parts[2].isdigit() and '/' not in pointure:
                pointure += '/' + parts[2]
                scans_autorises = int(parts[3]) if len(parts) > 3 else 1
            else:
                scans_autorises = int(parts[2]) if len(parts) > 2 else 1
        except (ValueError, IndexError):
            scans_autorises = 1

        if not num_of.isdigit():
            raise ValueError(f"Numéro OF invalide: {num_of}")

        return num_of, pointure, scans_autorises

    def validate_of_data(self, num_of, pointure):
        """Valide les données OF avec la base de données"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        cursor.execute("""
            SELECT numOF, Pointure, Quantite, Modele, Coloris
            FROM ofs
            WHERE numOF = %s
        """, (num_of,))

        of_data = cursor.fetchone()
        conn.close()

        if not of_data:
            raise ValueError(f"Aucun OF trouvé avec le numéro {num_of}")

        # Validation de la pointure
        db_pointure = of_data['Pointure'].replace(' ', '').lower()
        scanned_pointure = pointure.replace(' ', '').lower()

        if db_pointure != scanned_pointure:
            if '/' in db_pointure and scanned_pointure in db_pointure.split('/'):
                logging.info(f"Sub-size match: scanned {scanned_pointure} is part of {db_pointure}")
            else:
                raise ValueError(
                    f"Pointure scannée ({pointure}) ne correspond pas à celle de l'OF ({of_data['Pointure']})")

        return of_data


class ScanManager:
    """Gestionnaire des scans"""

    def __init__(self, db_manager, connection_manager, barcode_processor):
        self.db_manager = db_manager
        self.connection_manager = connection_manager
        self.barcode_processor = barcode_processor

    def process_scan(self, barcode_text, current_user):
        """Traite un scan de code-barres"""
        return self._process_normal_scan(barcode_text, current_user)

    def _process_normal_scan(self, barcode_text, current_user):
        """Traite un scan normal"""
        try:
            # Nettoyer et parser le code-barres
            cleaned_barcode = self.barcode_processor.clean_barcode(barcode_text)
            num_of, pointure, scans_autorises = self.barcode_processor.parse_barcode(cleaned_barcode)

            # Valider les données OF
            of_data = self.barcode_processor.validate_of_data(num_of, pointure)

            # Traiter le scan
            return self._process_valid_scan(num_of, pointure, scans_autorises, of_data, current_user, barcode_text,
                                            cleaned_barcode)

        except Exception as e:
            logging.error(f"Erreur scan normal: {e}")
            return {"success": False, "message": str(e)}

    def _process_valid_scan(self, num_of, pointure, scans_autorises, of_data, current_user, original_barcode,
                            cleaned_barcode):
        """Traite un scan valide"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        try:
            # Calculer les paramètres du scan
            quantite = int(of_data['Quantite']) if of_data['Quantite'] is not None else 0
            if quantite <= 0:
                raise ValueError(f"Quantité invalide: {of_data['Quantite']}")

            if not isinstance(scans_autorises, int) or scans_autorises <= 0:
                scans_autorises = 1

            paire_par_scan = quantite // scans_autorises
            if paire_par_scan <= 0:
                paire_par_scan = 1

            # Gérer l'entrée de scan
            scan_data = self._get_or_create_scan_data(cursor, num_of, pointure, scans_autorises, paire_par_scan,
                                                      quantite, current_user)

            # Vérifier les limites
            if scan_data['current_scans'] >= scan_data['max_scans']:
                raise ValueError(f"Nombre maximum de scans atteint pour OF {num_of}")

            # Mettre à jour le scan
            result = self._update_scan(cursor, scan_data, num_of, pointure, paire_par_scan, current_user, of_data,
                                       original_barcode, cleaned_barcode)

            conn.commit()
            return result

        finally:
            conn.close()

    def _get_or_create_scan_data(self, cursor, num_of, pointure, scans_autorises, paire_par_scan, quantite,
                                 current_user):
        """Récupère ou crée les données de scan"""
        cursor.execute("""
            SELECT of_number, size, max_scans, current_scans, paire_par_scan, remaining_pairs, last_scan, username
            FROM barcode_scans
            WHERE of_number = %s AND size = %s AND username = %s
        """, (num_of, pointure, current_user['role']))

        scan_data = cursor.fetchone()

        if not scan_data:
            default_remaining_pairs = quantite
            cursor.execute("""
                INSERT INTO barcode_scans (of_number, size, max_scans, current_scans, paire_par_scan, remaining_pairs, username)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (num_of, pointure, scans_autorises, 0, paire_par_scan, default_remaining_pairs, current_user['role']))

            cursor.execute("""
                SELECT of_number, size, max_scans, current_scans, paire_par_scan, remaining_pairs, username
                FROM barcode_scans
                WHERE of_number = %s AND size = %s AND username = %s
            """, (num_of, pointure, current_user['role']))

            scan_data = cursor.fetchone()

        # Mettre à jour paire_par_scan si nécessaire
        if scan_data['paire_par_scan'] != paire_par_scan:
            cursor.execute("""
                UPDATE barcode_scans
                SET paire_par_scan = %s
                WHERE of_number = %s AND size = %s AND username = %s
            """, (paire_par_scan, num_of, pointure, current_user['role']))
            scan_data['paire_par_scan'] = paire_par_scan

        return scan_data

    def _update_scan(self, cursor, scan_data, num_of, pointure, paire_par_scan, current_user, of_data, original_barcode,
                     cleaned_barcode):
        """Met à jour le scan dans la base de données"""
        new_current_scans = scan_data['current_scans'] + 1
        new_remaining_pairs = max(0, scan_data['remaining_pairs'] - scan_data['paire_par_scan'])
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        phase = current_user['role']

        try:
            # Gérer le lancement et la fin de l'OF via API
            if new_current_scans == 1:
                data = [{"numOF": num_of, "chaine": current_user["role"]}]
                response = self.connection_manager.make_request("put", "/manage_ofs/launch_of", json=data)
                if response and response.status_code == 201:
                    logging.info("OF lancé avec succès")

            if new_current_scans == scan_data['max_scans']:
                data = {"numOF": num_of, "chaine": current_user["role"]}
                response = self.connection_manager.make_request("put", "/manage_ofs/update_to_done", json=data)
                if response and response.status_code == 201:
                    logging.info("OF marqué comme terminé")

            # Mettre à jour la table barcode_scans
            cursor.execute("""
                UPDATE barcode_scans
                SET current_scans = %s, remaining_pairs = %s, last_scan = %s, last_phase = %s
                WHERE of_number = %s AND size = %s AND username = %s
            """, (new_current_scans, new_remaining_pairs, current_time, phase, num_of, pointure, current_user['role']))

            # Ajouter à l'historique des scans
            cursor.execute("""
                INSERT INTO scan_history (of_number, size, scan_time, phase, username, original_barcode,
                                        cleaned_barcode, max_scans, current_scans, paire_par_scan,
                                        remaining_pairs, model, color, quantity)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (num_of, pointure, current_time, phase, current_user['role'], original_barcode,
                  cleaned_barcode, scan_data['max_scans'], new_current_scans, scan_data['paire_par_scan'],
                  new_remaining_pairs, of_data['Modele'], of_data['Coloris'], of_data['Quantite']))

            # ENREGISTREMENT DANS LA PRODUCTION - AVEC FALLBACK
            production_saved = self._save_production_with_fallback(
                cursor, num_of, scan_data['paire_par_scan'], of_data['Modele']
            )

            if production_saved:
                return {
                    "success": True,
                    "message": f"Scan de l'OF {num_of} enregistré avec succès!",
                    "scan_info": {
                        "of_data": of_data,
                        "new_current_scans": new_current_scans,
                        "scan_data": scan_data,
                        "new_remaining_pairs": new_remaining_pairs,
                        "phase": phase,
                        "current_time": current_time
                    }
                }
            else:
                return {"success": False, "message": "Erreur lors de l'enregistrement de la production"}

        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour du scan: {e}")
            raise

    def _save_production_with_fallback(self, cursor, num_of, nb_paire, modele):
        """Tente d'enregistrer la production via API, avec fallback direct en base"""

        # Tentative 1: Via l'API
        data = {
            "date": datetime.now().strftime("%Y/%m/%d"),
            "numOf": num_of,
            "nbPaire": nb_paire,
            "modele": modele
        }

        response = self.connection_manager.make_request("post", "/manage_production/save_production", json=data)

        if response and response.status_code == 200:
            logging.info("✅ Production enregistrée via API")
            return True

        # Tentative 2: Fallback direct en base de données
        logging.warning("❌ Échec API production, tentative de fallback direct en base...")
        return self._save_production_direct_db(cursor, num_of, nb_paire, modele)

    def _save_production_direct_db(self, cursor, num_of, nb_paire, modele):
        """Enregistrement direct en base de données en fallback"""
        try:
            current_date = datetime.now().strftime("%Y/%m/%d")

            # Vérifier si une entrée existe déjà pour aujourd'hui
            cursor.execute("""
                SELECT id, nbPaire FROM production 
                WHERE date = %s AND numOf = %s
            """, (current_date, num_of))

            existing = cursor.fetchone()

            if existing:
                # Mettre à jour l'existant
                new_nb_paire = existing['nbPaire'] + nb_paire
                cursor.execute("""
                    UPDATE production 
                    SET nbPaire = %s, modele = %s
                    WHERE date = %s AND numOf = %s
                """, (new_nb_paire, modele, current_date, num_of))
                logging.info(f"✅ Production mise à jour en base directe: OF {num_of}, {new_nb_paire} paires")
            else:
                # Nouvelle entrée
                cursor.execute("""
                    INSERT INTO production (date, numOf, nbPaire, modele)
                    VALUES (%s, %s, %s, %s)
                """, (current_date, num_of, nb_paire, modele))
                logging.info(f"✅ Nouvelle production enregistrée en base directe: OF {num_of}, {nb_paire} paires")

            return True

        except Exception as e:
            logging.error(f"❌ Échec fallback base de données: {e}")
            return False


class UIHelper:
    """Helper pour l'interface utilisateur"""

    @staticmethod
    def show_popup(title, message):
        if "Erreur" in title:
            st.error(f"❌ {title}: {message}")
        elif "Succès" in title:
            st.success(f"✅ {title}: {message}")
        else:
            st.info(f"ℹ️ {title}: {message}")

    @staticmethod
    def display_scan_info(scan_info):
        """Affiche les informations du scan"""
        of_data = scan_info["of_data"]
        new_current_scans = scan_info["new_current_scans"]
        scan_data = scan_info["scan_data"]
        new_remaining_pairs = scan_info["new_remaining_pairs"]
        phase = scan_info["phase"]
        current_time = scan_info["current_time"]

        progress_percentage = (new_current_scans / scan_data['max_scans'] * 100) if scan_data['max_scans'] > 0 else 0

        st.subheader("📋 Informations du Scan")

        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**OF:** {of_data['numOF']}")
            st.write(f"**Pointure:** {of_data['Pointure']}")
            st.write(f"**Quantité:** {of_data['Quantite']}")
            st.write(f"**Modèle:** {of_data['Modele']}")
            st.write(f"**Coloris:** {of_data['Coloris']}")

        with col2:
            st.write(f"**Scans effectués:** {new_current_scans}/{scan_data['max_scans']}")
            st.write(f"**Progrès:** {progress_percentage:.2f}%")
            st.write(f"**Paires par scan:** {scan_data['paire_par_scan']}")
            st.write(f"**Paires restantes:** {new_remaining_pairs}")
            st.write(f"**Phase:** {phase}")
            st.write(f"**Dernier scan:** {current_time}")


class LoginManager:
    """Gestionnaire de connexion"""

    def __init__(self, base_url=BASE_URL, session_manager=None):
        self.base_url = base_url
        self.session_manager = session_manager or SessionManager()

    def display_login_form(self):
        """Affiche le formulaire de connexion"""
        st.title("🔐 Connexion à l'application de production")

        with st.form("login_form"):
            username = st.text_input("Nom d'utilisateur")
            password = st.text_input("Mot de passe", type="password")
            submitted = st.form_submit_button("Se connecter")

            if submitted:
                self._handle_login_submission(username, password)

    def _handle_login_submission(self, username, password):
        """Gère la soumission du formulaire de connexion"""
        if not username:
            st.error("Veuillez entrer un nom d'utilisateur")
        elif not password:
            st.error("Veuillez entrer votre mot de passe")
        else:
            url = self.base_url + "/auth/login"
            data = {"username": username, "password": password}

            try:
                response = requests.post(url, json=data, timeout=10)

                if response.status_code == 200:
                    response_data = response.json()
                    if isinstance(response_data, list) and len(response_data) > 0:
                        data = response_data[0]
                    else:
                        data = response_data

                    self.session_manager.set_user_session(
                        data.get("username"),
                        data.get("access_token"),
                        data.get("refresh_token"),
                        data.get("role")
                    )
                    st.session_state.username = data.get("username")
                    st.rerun()

                elif response.status_code == 401:
                    st.error("Login ou mot de passe incorrect")
                else:
                    st.error("Erreur de connexion")

            except requests.exceptions.RequestException as e:
                st.error("Erreur de connexion au serveur")


class AppStateManager:
    """Gestionnaire de l'état de l'application"""

    def __init__(self):
        self.initialize_session_state()

    def initialize_session_state(self):
        """Initialise les variables d'état de session"""
        if 'current_paire_par_scan' not in st.session_state:
            st.session_state.current_paire_par_scan = 0
        if 'token_refreshed_on_load' not in st.session_state:
            st.session_state.token_refreshed_on_load = False

    def clear_session_state(self):
        """Nettoie l'état de session"""
        st.session_state.clear()


class MainApplication:
    """Application principale"""

    def __init__(self):
        self.session_manager = SessionManager()
        self.connection_manager = ConnectionManager(session_manager=self.session_manager)
        self.db_manager = DatabaseManager()
        self.barcode_processor = BarcodeProcessor(self.db_manager, self.connection_manager)
        self.scan_manager = ScanManager(self.db_manager, self.connection_manager, self.barcode_processor)
        self.ui_helper = UIHelper()
        self.login_manager = LoginManager(session_manager=self.session_manager)
        self.app_state = AppStateManager()

        self._configure_application()

    def _configure_application(self):
        """Configure l'application"""
        if __name__ == "__main__" and not hasattr(st, 'server'):
            os.environ['STREAMLIT_SERVER_PORT'] = str(DEFAULT_PORT)

        logging.basicConfig(level=logging.DEBUG, filename='barcode_scanner_web.log', filemode='a',
                            format='%(asctime)s - %(levelname)s - %(message)s')

        st.set_page_config(page_title="Application Scan Production", layout="wide")

        # Démarrage de la vérification en arrière-plan
        self.connection_manager.start_background_check()

    def run(self):
        """Point d'entrée principal de l'application"""
        if not self._is_user_authenticated():
            self._show_login_interface()
            return

        self._show_main_interface()

    def _is_user_authenticated(self):
        """Vérifie si l'utilisateur est authentifié"""
        return 'username' in st.session_state and self.session_manager.get_user_session(
            st.session_state.get('username'))

    def _show_login_interface(self):
        """Affiche l'interface de connexion"""
        self.connection_manager.display_connection_status()
        self.login_manager.display_login_form()
        st.stop()

    def _show_main_interface(self):
        """Affiche l'interface principale"""
        session_data = self.session_manager.get_user_session(st.session_state.username)
        self.connection_manager.display_connection_status()

        # Sidebar
        self._setup_sidebar(session_data)

        # Contenu principal
        if st.session_state.username.startswith("control"):
            self._show_control_interface(session_data)
        else:
            st.warning("⛔ Accès non autorisé")

    def _setup_sidebar(self, session_data):
        """Configure la sidebar"""
        st.sidebar.title(f"👤 Bienvenue, {st.session_state.username}")
        st.sidebar.write(f"Rôle: {session_data.get('role')}")

        # Rafraîchir le token au chargement
        if not st.session_state.token_refreshed_on_load:
            self.connection_manager.auto_refresh_token()
            st.session_state.token_refreshed_on_load = True

        if st.sidebar.button("🚪 Déconnexion"):
            self.session_manager.clear_user_session(st.session_state.username)
            self.app_state.clear_session_state()
            st.rerun()

    def _show_control_interface(self, session_data):
        """Affiche l'interface pour les utilisateurs 'control'"""
        st.title("📦 Scan de Codes-Barres")

        # Afficher le statut de connexion discret
        self._display_connection_status_indicator()

        # Formulaire de scan
        self._show_scan_form(session_data)

        # Actualisation de l'interface
        time.sleep(1)
        st.rerun()

    def _display_connection_status_indicator(self):
        """Affiche un indicateur discret du statut de connexion"""
        status_placeholder = st.empty()
        if not self.connection_manager.connection_status["connected"]:
            with status_placeholder:
                st.warning("⚠️ Reconnexion en cours...")
        else:
            status_placeholder.empty()

    def _show_scan_form(self, session_data):
        """Affiche le formulaire de scan"""
        with st.form("scan_form", clear_on_submit=True):
            barcode = st.text_input("🔍 Entrez ou scannez le code-barres", key="barcode_input")
            submitted = st.form_submit_button("📥 Scanner")

            if submitted:
                self._handle_scan_submission(barcode, session_data)

    def _handle_scan_submission(self, barcode, session_data):
        """Gère la soumission du formulaire de scan"""
        # Vérification du token avant scan
        if not self.connection_manager.ensure_valid_token():
            st.error("Session expirée. Veuillez vous reconnecter.")
            st.stop()

        current_user = {"username": st.session_state.username, "role": session_data.get('role')}

        if not current_user:
            self.ui_helper.show_popup("Erreur", "Session expirée. Veuillez vous reconnecter.")
        elif not barcode.strip():
            self.ui_helper.show_popup("Erreur", "Veuillez scanner un code-barres")
        else:
            barcode_text = barcode.strip()

            # Traitement du scan
            result = self.scan_manager.process_scan(barcode_text, current_user)

            # Gestion des résultats
            self._handle_scan_result(result)

    def _handle_scan_result(self, result):
        """Gère le résultat du scan"""
        if result.get("success"):
            self.ui_helper.show_popup("Succès", result["message"])
            if "scan_info" in result:
                self.ui_helper.display_scan_info(result["scan_info"])
        else:
            self.ui_helper.show_popup("Erreur", result["message"])


# Point d'entrée de l'application
if __name__ == "__main__":
    app = MainApplication()
    app.run()