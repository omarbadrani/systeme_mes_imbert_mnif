from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QMessageBox
from PyQt5.QtCore import Qt
import logging
from frontend.SessionManager import SessionManager
from frontend.screens.LaunchScreen import LaunchWindow
from frontend.screens.dashboard import DashboardWindow
from frontend.screens.OfsEnCoursScreen import OfsEnCoursWindow
from frontend.screens.login import LoginWindow
from frontend.screens.addUser import AddUserWindow
from frontend.screens.listUser import ListUserWindow
from frontend.screens.RoleManagementScreen import RoleManagementWindow
from frontend.screens.UpdateLaunchScreen import UpdateLaunchWindow
import requests


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.session = SessionManager.get_instance()
        self.screen_map = {}  # Dictionnaire pour mapper les noms d'écrans aux indices du QStackedWidget
        self.screens = {
            "login_screen": {"class": LoginWindow, "instance": None},
            "launch_screen": {"class": LaunchWindow, "instance": None},
            "dashboard_screen": {"class": DashboardWindow, "instance": None},
            "update_launch_screen": {"class": UpdateLaunchWindow, "instance": None},
            "ofs_en_cours_screen": {"class": OfsEnCoursWindow, "instance": None},
            "adduser_screen": {"class": AddUserWindow, "instance": None},
            "list_users_screen": {"class": ListUserWindow, "instance": None},
            "gestion_role_screen": {"class": RoleManagementWindow, "instance": None},
        }
        self.current_screen = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("MES Application")
        self.main_widget = QStackedWidget()
        self.setCentralWidget(self.main_widget)
        self.setStyleSheet("background-color: rgba(242, 242, 242, 255);")

        # Initialiser l'écran de connexion
        if not self.initialize_screen("login_screen"):
            logging.critical("Failed to initialize login screen. Exiting application.")
            QMessageBox.critical(self, "Erreur critique",
                                 "Impossible d'initialiser l'écran de connexion. L'application va se fermer.")
            QApplication.quit()
            return
        self.current_screen = "login_screen"
        logging.debug("MainWindow initialized. Starting with login screen")
        self.showMaximized()  # Afficher en plein écran après initialisation

    def initialize_screen(self, screen_name):
        """Initialise un écran s'il n'existe pas déjà."""
        if screen_name not in self.screens:
            logging.error(
                f"Screen '{screen_name}' not found in configuration. Available screens: {list(self.screens.keys())}")
            return False

        if self.screens[screen_name]["instance"] is None:
            try:
                logging.debug(f"Creating instance of {screen_name}")
                self.screens[screen_name]["instance"] = self.screens[screen_name]["class"]()
                if self.screens[screen_name]["instance"] is None:
                    raise RuntimeError(f"Failed to create instance of {screen_name}")
                if hasattr(self.screens[screen_name]["instance"], 'switch_screen'):
                    self.screens[screen_name]["instance"].switch_screen.connect(self.switch_to_screen)
                    logging.debug(f"Connected switch_screen signal for {screen_name}")
                else:
                    logging.warning(f"Screen '{screen_name}' does not have a switch_screen signal.")
                self.screen_map[screen_name] = self.main_widget.addWidget(self.screens[screen_name]["instance"])
                logging.debug(f"Screen '{screen_name}' initialized and added at index {self.screen_map[screen_name]}")
                return True
            except Exception as e:
                logging.error(f"Failed to initialize screen '{screen_name}': {str(e)}")
                QMessageBox.critical(self, "Erreur", f"Impossible de charger l'écran '{screen_name}': {str(e)}")
                return False
        return True

    def switch_to_screen(self, screen_name):
        """Change vers l'écran spécifié par son nom."""
        logging.debug(
            f"Received switch_screen signal for screen: '{screen_name}' from {self.sender().__class__.__name__ if self.sender() else 'Unknown'}")

        # Solution de secours pour l'erreur de typo
        if screen_name == "ofs_encours_screen":
            logging.warning(
                "Received deprecated screen name 'ofs_encours_screen', redirecting to 'ofs_en_cours_screen'")
            screen_name = "ofs_en_cours_screen"

        if screen_name == self.current_screen:
            logging.debug(f"Ignoring redundant switch to current screen: {screen_name}")
            return

        if screen_name not in self.screens:
            logging.error(
                f"Screen '{screen_name}' not found in configuration. Available screens: {list(self.screens.keys())}")
            QMessageBox.critical(self, "Erreur",
                                 f"L'écran '{screen_name}' n'existe pas. Vérifiez le nom dans le signal émis par {self.sender().__class__.__name__ if self.sender() else 'Unknown'}.")
            return

        if not self.initialize_screen(screen_name):
            logging.error(f"Failed to initialize screen '{screen_name}'")
            QMessageBox.critical(self, "Erreur", f"Impossible de charger l'écran '{screen_name}'.")
            return

        try:
            screen_index = self.screen_map[screen_name]
            self.main_widget.setCurrentIndex(screen_index)
            self.current_screen = screen_name
            logging.debug(f"Successfully switched to screen '{screen_name}' at index {screen_index}")
            if hasattr(self.screens[screen_name]["instance"], 'on_enter'):
                logging.debug(f"Calling on_enter for {screen_name}")
                self.screens[screen_name]["instance"].on_enter()
        except Exception as e:
            logging.error(f"Error switching to screen '{screen_name}': {str(e)}")
            QMessageBox.critical(self, "Erreur", f"Erreur lors du changement vers l'écran '{screen_name}': {str(e)}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    app = QApplication([])
    window = MainWindow()
    app.exec_()