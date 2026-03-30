import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QComboBox, QScrollArea,
                             QMessageBox, QFrame)
from PyQt5.QtGui import QFont, QFontDatabase, QColor
from PyQt5.QtCore import Qt, pyqtSignal
from frontend.Client import make_request

class AddUserWindow(QWidget):
    switch_screen = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_roles()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setStyleSheet("background-color: rgba(242, 242, 242, 255);")

        # Load emoji font
        font_db = QFontDatabase()
        font_id = font_db.addApplicationFont(r"D:\seguiemj.ttf")
        self.emoji_font = QFont(font_db.applicationFontFamilies(font_id)[0], 12) if font_id != -1 else QFont("Arial", 12)

        # Topbar
        topbar = QWidget()
        topbar.setFixedHeight(50)
        topbar.setStyleSheet("background-color: rgba(51, 128, 204, 255);")
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(10, 0, 10, 0)
        topbar_label = QLabel("👤 Gestion des Utilisateurs")
        topbar_label.setFont(QFont(self.emoji_font.family(), 14, QFont.Bold))
        topbar_label.setStyleSheet("color: white;")
        topbar_layout.addWidget(topbar_label)
        main_layout.addWidget(topbar)

        # Main content (sidebar + content)
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(content_widget)

        # Sidebar
        sidebar = QWidget()
        sidebar.setMinimumWidth(150)
        sidebar.setStyleSheet("""
            background-color: #34495e;
            border-right: 1px solid #2c3e50;
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(5, 20, 5, 20)
        sidebar_layout.setSpacing(10)

        buttons = [
            ("➕ Ajouter utilisateur", self.root_to_add_user),
            ("📋 Utilisateurs", self.root_to_list_users),
            ("🔧 Gestion du rôle", self.root_to_gestion_role),
            ("🚪 Déconnexion", self.logout)
        ]
        for text, callback in buttons:
            btn = QPushButton(text)
            btn.setFont(QFont("Arial", 11))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3d566e;
                    color: white;
                    border: none;
                    padding: 10px;
                    text-align: left;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #4b6584;
                }
            """)
            btn.clicked.connect(callback)
            sidebar_layout.addWidget(btn)
        sidebar_layout.addStretch()
        content_layout.addWidget(sidebar)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_layout.addWidget(scroll)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        scroll_layout.setSpacing(20)
        scroll.setWidget(scroll_content)

        # Worker section
        worker_section = QFrame()
        worker_layout = QVBoxLayout(worker_section)
        worker_layout.setSpacing(8)

        worker_label = QLabel("👷‍♂️ Ajouter un Ouvrier")
        worker_label.setFont(QFont(self.emoji_font.family(), 18))
        worker_label.setStyleSheet("color: rgba(51, 77, 153, 255);")
        worker_label.setFixedHeight(40)
        worker_layout.addWidget(worker_label)

        self.nom_ouvrier = QLineEdit()
        self.nom_ouvrier.setPlaceholderText("Nom 👤")
        self.nom_ouvrier.setFont(self.emoji_font)
        self.nom_ouvrier.setFixedHeight(40)
        worker_layout.addWidget(self.nom_ouvrier)

        self.prenom_ouvrier = QLineEdit()
        self.prenom_ouvrier.setPlaceholderText("Prénom 🧾")
        self.prenom_ouvrier.setFont(self.emoji_font)
        self.prenom_ouvrier.setFixedHeight(40)
        worker_layout.addWidget(self.prenom_ouvrier)

        self.matricule_ouvrier = QLineEdit()
        self.matricule_ouvrier.setPlaceholderText("Matricule 🆔")
        self.matricule_ouvrier.setFont(self.emoji_font)
        self.matricule_ouvrier.setFixedHeight(40)
        worker_layout.addWidget(self.matricule_ouvrier)

        worker_btn = QPushButton("✅ Ajouter Ouvrier")
        worker_btn.setFont(self.emoji_font)
        worker_btn.setFixedHeight(50)
        worker_btn.setStyleSheet("background-color: rgba(0, 179, 153, 255); color: white;")
        worker_btn.clicked.connect(self.ajouter_ouvrier)
        worker_layout.addWidget(worker_btn)

        scroll_layout.addWidget(worker_section)

        # User section
        user_section = QFrame()
        user_layout = QVBoxLayout(user_section)
        user_layout.setSpacing(8)

        user_label = QLabel("👨‍💼 Ajouter un Utilisateur")
        user_label.setFont(QFont(self.emoji_font.family(), 14))
        user_label.setStyleSheet("color: rgba(51, 77, 153, 255);")
        user_label.setFixedHeight(40)
        user_layout.addWidget(user_label)

        self.nom_utilisateur = QLineEdit()
        self.nom_utilisateur.setPlaceholderText("Nom d'utilisateur 👤")
        self.nom_utilisateur.setFont(self.emoji_font)
        self.nom_utilisateur.setFixedHeight(40)
        user_layout.addWidget(self.nom_utilisateur)

        self.username_error = QLabel("")
        self.username_error.setFont(QFont(self.emoji_font.family(), 12))
        self.username_error.setStyleSheet("color: red;")
        user_layout.addWidget(self.username_error)

        self.motdepasse_utilisateur = QLineEdit()
        self.motdepasse_utilisateur.setPlaceholderText("Mot de passe 🔐")
        self.motdepasse_utilisateur.setFont(self.emoji_font)
        self.motdepasse_utilisateur.setFixedHeight(40)
        self.motdepasse_utilisateur.setEchoMode(QLineEdit.Password)
        user_layout.addWidget(self.motdepasse_utilisateur)

        self.password_error = QLabel("")
        self.password_error.setFont(QFont(self.emoji_font.family(), 12))
        self.password_error.setStyleSheet("color: red;")
        user_layout.addWidget(self.password_error)

        self.role_utilisateur = QComboBox()
        self.role_utilisateur.addItem("Sélectionner un rôle")
        self.role_utilisateur.setFont(self.emoji_font)
        self.role_utilisateur.setFixedHeight(40)
        self.role_utilisateur.currentTextChanged.connect(lambda text: print(f"Rôle sélectionné : {text}"))
        user_layout.addWidget(self.role_utilisateur)

        self.message = QLabel("")
        self.message.setFont(QFont(self.emoji_font.family(), 12, QFont.Bold))
        self.message.setStyleSheet("color: red;")
        user_layout.addWidget(self.message)

        user_btn = QPushButton("➕ Ajouter Utilisateur")
        user_btn.setFont(self.emoji_font)
        user_btn.setFixedHeight(50)
        user_btn.setStyleSheet("background-color: rgba(77, 153, 204, 255); color: white;")
        user_btn.clicked.connect(self.ajouter_utilisateur)
        user_layout.addWidget(user_btn)

        scroll_layout.addWidget(user_section)
        scroll_layout.addStretch()

    def load_roles(self):
        try:
            print("Loading roles")
            response = make_request("get", "/manage_chaine_roles/getAllRoles")
            if response.status_code in(200,201):
                roles = response.json()[0].get("roles", [])
                print("Roles loaded:", roles)
                self.role_utilisateur.clear()
                self.role_utilisateur.addItem("Sélectionner un rôle")
                for role in roles:
                    self.role_utilisateur.addItem(role["id"])
            else:
                print(f"Error loading roles: {response.status_code}")
                self.show_popup("Erreur", f"Erreur lors du chargement des rôles: {response.status_code}")
                self.role_utilisateur.clear()
                self.role_utilisateur.addItems(["Sélectionner un rôle", "production", "gestion des utilisateurs", "control"])
        except Exception as e:
            print(f"Error in load_roles: {e}")
            self.show_popup("Erreur", f"Erreur lors du chargement des rôles: {str(e)}")
            self.role_utilisateur.clear()
            self.role_utilisateur.addItems(["Sélectionner un rôle", "production", "gestion des utilisateurs", "control"])

    def ajouter_ouvrier(self):
        try:
            first_name = self.nom_ouvrier.text().strip()
            last_name = self.prenom_ouvrier.text().strip()
            matricule = self.matricule_ouvrier.text().strip()
            if not first_name or not last_name or not matricule:
                self.message.setText("⚠️ Remplissez tous les champs pour l'ouvrier")
                return
            data = {
                "MATR": matricule,
                "NOM": first_name,
                "PRENOM": last_name,
            }
            response = make_request("post", "/manage_users/addWorker", json=data)
            if response.status_code in(200,201):
                self.message.setText("✅ Ouvrier ajouté avec succès !")
                self.nom_ouvrier.clear()
                self.prenom_ouvrier.clear()
                self.matricule_ouvrier.clear()
                self.show_popup("Succès", "✅ Ouvrier ajouté avec succès !")
            elif response.status_code == 409:
                self.message.setText("⚠️ Cet ouvrier existe déjà !")
                self.show_popup("Attention", "Cet ouvrier existe déjà !")
            else:
                self.message.setText(f"❌ Erreur: {response.status_code}")
                self.show_popup("Erreur", f"Erreur lors de l'ajout de l'ouvrier: {response.status_code}")
        except Exception as e:
            print(f"Error in ajouter_ouvrier: {e}")
            self.message.setText("❌ Erreur lors de l'ajout de l'ouvrier")
            self.show_popup("Erreur", f"Erreur lors de l'ajout de l'ouvrier: {str(e)}")

    def ajouter_utilisateur(self):
        try:
            username = self.nom_utilisateur.text().strip()
            password = self.motdepasse_utilisateur.text().strip()
            role = self.role_utilisateur.currentText().strip()
            if not username:
                self.username_error.setText("Veuillez entrer un nom d'utilisateur")
                return
            self.username_error.setText("")
            if not password:
                self.password_error.setText("Veuillez entrer un mot de passe")
                return
            self.password_error.setText("")
            if role == "Sélectionner un rôle":
                self.message.setText("Veuillez sélectionner un rôle")
                return
            self.message.setText("")
            data = {
                "username": username,
                "password": password,
                "role": role,
                "authorized": 1,
            }
            response = make_request("post", "/manage_users/addUser", json=data)
            if response.status_code in(200,201):
                self.message.setText("✅ Utilisateur ajouté avec succès !")
                self.nom_utilisateur.clear()
                self.motdepasse_utilisateur.clear()
                self.role_utilisateur.setCurrentText("Sélectionner un rôle")
                self.show_popup("Succès", "✅ Utilisateur ajouté avec succès !")
            elif response.status_code == 409:
                self.message.setText("⚠️ Cet utilisateur existe déjà !")
                self.show_popup("Attention", "Cet utilisateur existe déjà !")
            else:
                self.message.setText(f"❌ Erreur: {response.status_code}")
                self.show_popup("Erreur", f"Erreur lors de l'ajout de l'utilisateur: {response.status_code}")
        except Exception as e:
            print(f"Error in ajouter_utilisateur: {e}")
            self.message.setText("❌ Erreur lors de l'ajout de l'utilisateur")
            self.show_popup("Erreur", f"Erreur lors de l'ajout de l'utilisateur: {str(e)}")

    def show_popup(self, title, message):
        popup = QMessageBox()
        popup.setWindowTitle(title)
        popup.setText(message)
        popup.setFont(self.emoji_font)
        popup.setStyleSheet("""
            QMessageBox { background-color: rgba(242, 242, 242, 255); }
            QLabel { color: black; }
            QPushButton {
                background-color: rgba(102, 179, 255, 255);
                color: white;
                padding: 5px;
                min-width: 80px;
            }
        """)
        popup.setStandardButtons(QMessageBox.Ok)
        popup.exec_()

    def root_to_add_user(self):
        self.switch_screen.emit("adduser_screen")

    def root_to_list_users(self):
        self.switch_screen.emit("list_users_screen")

    def root_to_gestion_role(self):
        self.switch_screen.emit("gestion_role_screen")

    def logout(self):
        self.switch_screen.emit("login_screen")