from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QScrollArea, QTableWidget, QTableWidgetItem,
                             QComboBox, QMessageBox, QHeaderView)
from PyQt5.QtGui import QFont, QFontDatabase, QColor
from PyQt5.QtCore import Qt, pyqtSignal
from frontend.Client import make_request
from SessionManager import SessionManager

class ListUserWindow(QWidget):
    switch_screen = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.show_modification = False
        self.users = []
        self.session = SessionManager.get_instance()
        self.init_ui()
        self.on_enter()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setStyleSheet("background-color: #F5F5F5;")  # Lighter background for modern feel

        # Load emoji font
        font_db = QFontDatabase()
        font_id = font_db.addApplicationFont(r"D:\seguiemj.ttf")
        self.emoji_font = QFont(font_db.applicationFontFamilies(font_id)[0], 12) if font_id != -1 else QFont("Arial", 12)

        # Topbar
        topbar = QWidget()
        topbar.setFixedHeight(60)  # Slightly taller for better presence
        topbar.setStyleSheet("background-color: #3380CC; border-bottom: 1px solid #2A6AA8;")
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(20, 0, 20, 0)
        topbar_label = QLabel("👤 Gestion des Utilisateurs")
        topbar_label.setFont(QFont(self.emoji_font.family(), 16, QFont.Bold))
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
        sidebar.setMinimumWidth(200)
        sidebar.setStyleSheet("""
            background-color: #34495e;
            border-right: 1px solid #2c3e50;
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(5, 20, 5, 20)
        sidebar_layout.setSpacing(5)

        buttons = [
            ("➕ Ajouter utilisateur", self.root_to_addUser),
            ("📋 Utilisateurs", self.root_to_listUsers),
            ("🔧 Gestion du rôle", self.root_to_gestionRole),
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

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_layout.addWidget(scroll)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(20, 20, 20, 20)
        scroll_layout.setSpacing(15)
        scroll.setWidget(scroll_content)

        # Search form
        search_form = QWidget()
        search_layout = QHBoxLayout(search_form)
        search_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher par nom")
        self.search_input.setFont(self.emoji_font)
        self.search_input.setFixedHeight(40)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        search_layout.addWidget(self.search_input)

        search_btn = QPushButton("🔍 Rechercher")
        search_btn.setFont(self.emoji_font)
        search_btn.setFixedHeight(40)
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #3380CC;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #2A6AA8;
            }
        """)
        search_btn.clicked.connect(self.chercher_par_nom)
        search_layout.addWidget(search_btn)

        refresh_btn = QPushButton("🔄")
        refresh_btn.setFont(self.emoji_font)
        refresh_btn.setFixedHeight(40)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3380CC;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #2A6AA8;
            }
        """)
        refresh_btn.clicked.connect(self.loadUsers)
        search_layout.addWidget(refresh_btn)
        scroll_layout.addWidget(search_form)

        # Users list label
        users_label = QLabel("📋 Liste des Utilisateurs")
        users_label.setFont(QFont(self.emoji_font.family(), 16, QFont.Bold))
        users_label.setStyleSheet("color: #333333;")
        users_label.setFixedHeight(40)
        scroll_layout.addWidget(users_label)

        # Table (using QTableWidget for better display and functionality)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Nom d'utilisateur", "Rôle", "Autorisation"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setStyleSheet("""
            QHeaderLabel {
                background-color: #F0F0F0;
                color: #333333;
                padding: 8px;
            }
        """)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                gridline-color: #E0E0E0;
            }
            QTableWidget::item {
                padding: 8px;
                color: #333333;
            }
            QTableWidget::item:selected {
                background-color: #E0F0FF;
            }
        """)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setMinimumHeight(300)  # Increased height for better visibility
        scroll_layout.addWidget(self.table)
        # Modification input
        mod_input_form = QWidget()
        mod_input_layout = QHBoxLayout(mod_input_form)
        mod_input_layout.setSpacing(10)

        self.input_user = QLineEdit()
        self.input_user.setPlaceholderText("Entrez l'ID")
        self.input_user.setFont(self.emoji_font)
        self.input_user.setFixedHeight(40)
        self.input_user.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        mod_input_layout.addWidget(self.input_user)

        mod_btn = QPushButton("✏️ Modifier")
        mod_btn.setFont(self.emoji_font)
        mod_btn.setFixedHeight(40)
        mod_btn.setStyleSheet("""
            QPushButton {
                background-color: #3380CC;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #2A6AA8;
            }
        """)
        mod_btn.clicked.connect(self.afficher_detail_user)
        mod_input_layout.addWidget(mod_btn)
        scroll_layout.addWidget(mod_input_form)

        # Modification form
        self.mod_form = QWidget()
        self.mod_form.setVisible(self.show_modification)
        self.mod_form.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 4px; padding: 20px;")
        mod_form_layout = QVBoxLayout(self.mod_form)
        mod_form_layout.setContentsMargins(20, 20, 20, 20)
        mod_form_layout.setSpacing(15)

        mod_label = QLabel("✏️ Modifier Utilisateur")
        mod_label.setFont(QFont(self.emoji_font.family(), 18, QFont.Bold))
        mod_label.setStyleSheet("color: #333333;")
        mod_form_layout.addWidget(mod_label)

        username_row = QHBoxLayout()
        username_row.setSpacing(10)
        username_label = QLabel("Username:")
        username_label.setStyleSheet("color: #333333; font-weight: bold;")
        username_label.setFixedWidth(120)
        self.mod_username = QLineEdit()
        self.mod_username.setFixedHeight(40)
        self.mod_username.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        username_row.addWidget(username_label)
        username_row.addWidget(self.mod_username)
        mod_form_layout.addLayout(username_row)

        password_row = QHBoxLayout()
        password_row.setSpacing(10)
        password_label = QLabel("Nouveau mot de passe:")
        password_label.setStyleSheet("color: #333333; font-weight: bold;")
        password_label.setFixedWidth(120)
        self.new_password = QLineEdit()
        self.new_password.setEchoMode(QLineEdit.Password)
        self.new_password.setPlaceholderText("Saisir le nouveau mot de passe")
        self.new_password.setFixedHeight(40)
        self.new_password.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        password_row.addWidget(password_label)
        password_row.addWidget(self.new_password)
        mod_form_layout.addLayout(password_row)

        role_row = QHBoxLayout()
        role_row.setSpacing(10)
        role_label = QLabel("Rôle:")
        role_label.setStyleSheet("color: #333333; font-weight: bold;")
        role_label.setFixedWidth(120)
        self.mod_role = QComboBox()
        self.mod_role.setFont(self.emoji_font)
        self.mod_role.addItems(["Sélectionner un rôle", "production", "coupe", "piqure1", "piqure2", "piqure3", "montage", "control"])
        self.mod_role.setFixedHeight(40)
        self.mod_role.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        role_row.addWidget(role_label)
        role_row.addWidget(self.mod_role)
        mod_form_layout.addLayout(role_row)

        auth_row = QHBoxLayout()
        auth_row.setSpacing(10)
        auth_label = QLabel("Autorisation:")
        auth_label.setStyleSheet("color: #333333; font-weight: bold;")
        auth_label.setFixedWidth(120)
        self.mod_authorization = QComboBox()
        self.mod_authorization.setFont(self.emoji_font)
        self.mod_authorization.addItems(["autorise", "non autorise"])
        self.mod_authorization.setFixedHeight(40)
        self.mod_authorization.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        auth_row.addWidget(auth_label)
        auth_row.addWidget(self.mod_authorization)
        mod_form_layout.addLayout(auth_row)

        update_btn = QPushButton("✅ Valider Modification")
        update_btn.setFont(self.emoji_font)
        update_btn.setFixedHeight(40)
        update_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        update_btn.clicked.connect(self.updateUser)
        mod_form_layout.addWidget(update_btn)
        scroll_layout.addWidget(self.mod_form)
        scroll_layout.addStretch()

    def on_enter(self):
        try:
            self.show_modification = False
            self.mod_form.setVisible(self.show_modification)
            self.loadUsers()
        except Exception as e:
            print(f"Error in on_enter: {e}")
            self.show_popup("Erreur", f"Erreur lors du chargement initial: {str(e)}")

    def display_users(self, users):
        try:
            print("Displaying users:", users)
            self.table.setRowCount(0)
            self.table.setRowCount(len(users))
            for row, user in enumerate(users):
                self.table.setItem(row, 0, QTableWidgetItem(str(user["id"])))
                self.table.setItem(row, 1, QTableWidgetItem(user["username"]))
                self.table.setItem(row, 2, QTableWidgetItem(user["role"]))
                auth_text = "autorise" if user["authorized"] == 1 else "non autorise"
                self.table.setItem(row, 3, QTableWidgetItem(auth_text))
        except Exception as e:
            print(f"Error in display_users: {e}")
            self.show_popup("Erreur", f"Erreur lors de l'affichage des utilisateurs: {str(e)}")

    def loadUsers(self):
        try:
            print("Loading users")
            response = make_request("get", "/manage_users/getUsers")
            if response.status_code in (200,201):
                self.users = response.json()[0].get("users", [])
                print("Users loaded:", self.users)
                self.display_users(self.users)
            else:
                print(f"Error loading users: {response.status_code}")
                self.show_popup("Erreur", f"Erreur lors du chargement des utilisateurs: {response.status_code}")
        except Exception as e:
            print(f"Error in loadUsers: {e}")
            self.show_popup("Erreur", f"Erreur lors du chargement des utilisateurs: {str(e)}")

    def updateUser(self):
        try:
            id = self.input_user.text().strip()
            username = self.mod_username.text().strip()
            role = self.mod_role.currentText().strip()
            password = self.new_password.text().strip()
            authorized = 1 if self.mod_authorization.currentText() == "autorise" else 0
            if not id or not username or role == "Sélectionner un rôle":
                self.show_popup("Attention", "Veuillez remplir tous les champs obligatoires (ID, username, rôle)")
                return
            data = {"id": id, "username": username, "role": role, "authorized": authorized}
            if password:
                data["pwd"] = password
            print("Updating user:", data)
            response = make_request("put", "/manage_users/updateUser", json=data)
            if response.status_code in(200,201):
                self.show_popup("Succès", "Utilisateur modifié avec succès")
                self.mod_username.clear()
                self.mod_role.setCurrentText("Sélectionner un rôle")
                self.input_user.clear()
                self.new_password.clear()
                self.mod_authorization.setCurrentText("autorise")
                self.show_modification = False
                self.mod_form.setVisible(self.show_modification)
                self.loadUsers()
            elif response.status_code == 401:
                self.show_popup("Attention", "Vous n'êtes pas autorisé pour cette fonction")
            elif response.status_code == 404:
                self.show_popup("Attention", "Utilisateur n'existe pas dans la base")
            else:
                self.show_popup("Erreur", f"Erreur lors de la modification: {response.status_code}")
        except Exception as e:
            print(f"Error in updateUser: {e}")
            self.show_popup("Erreur", f"Erreur lors de la modification de l'utilisateur: {str(e)}")

    def afficher_detail_user(self):
        try:
            id = self.input_user.text().strip()
            if not id:
                self.show_popup("Attention", "Veuillez saisir un ID valide")
                return
            data = {"id": id}
            response = make_request("get", "/manage_users/getUserById", json=data)
            if response.status_code in(200,201):
                self.show_modification = True
                user = response.json()[0].get("user", {})
                self.mod_username.setText(user.get("username", ""))
                self.mod_role.setCurrentText(user.get("role", "Sélectionner un rôle"))
                self.mod_authorization.setCurrentText("autorise" if user.get("authorized", 0) == 1 else "non autorise")
            elif response.status_code == 401:
                self.show_popup("Attention", "Vous n'êtes pas autorisé pour cette fonction")
            elif response.status_code == 404:
                self.show_popup("Attention", "Utilisateur n'existe pas dans la base")
            else:
                self.show_popup("Erreur", f"Erreur lors de la récupération des données: {response.status_code}")
            self.mod_form.setVisible(self.show_modification)
        except Exception as e:
            print(f"Error in afficher_detail_user: {e}")
            self.show_popup("Erreur", f"Erreur lors de la récupération des données: {str(e)}")

    def chercher_par_nom(self):
        try:
            search_text = self.search_input.text().strip().lower()
            print("Searching for:", search_text)
            if search_text:
                filtered_users = [user for user in self.users if search_text in user["username"].lower()]
                self.display_users(filtered_users)
            else:
                self.loadUsers()
        except Exception as e:
            print(f"Error in chercher_par_nom: {e}")
            self.show_popup("Erreur", f"Erreur lors de la recherche: {str(e)}")

    def show_popup(self, title, message):
        popup = QMessageBox()
        popup.setWindowTitle(title)
        popup.setText(message)
        popup.setFont(self.emoji_font)
        popup.setStyleSheet("""
            QMessageBox { background-color: #F5F5F5; }
            QLabel { color: #333333; }
            QPushButton {
                background-color: #3380CC;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #2A6AA8;
            }
        """)
        popup.setStandardButtons(QMessageBox.Ok)
        popup.exec_()

    def root_to_addUser(self):
        self.switch_screen.emit("adduser_screen")

    def root_to_listUsers(self):
        self.switch_screen.emit("list_users_screen")

    def root_to_gestionRole(self):
        self.switch_screen.emit("gestion_role_screen")

    def logout(self):
        self.switch_screen.emit("login_screen")