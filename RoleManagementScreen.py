from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QScrollArea, QGridLayout, QComboBox,
                             QMessageBox, QFrame, QHeaderView, QTableWidget,
                             QTableWidgetItem, QAbstractItemView, QSizePolicy)
from PyQt5.QtGui import QFont, QFontDatabase, QDoubleValidator, QIntValidator, QColor, QPalette
from PyQt5.QtCore import Qt, pyqtSignal, QSize

from frontend.Client import make_request
from frontend.SessionManager import SessionManager


class RoleManagementWindow(QWidget):
    switch_screen = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.show_modification = False
        self.session = SessionManager.get_instance()
        self.roles = []
        self.modeles = []
        self.init_ui()
        self.on_enter()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setStyleSheet("""
            background-color: #f5f7fa;
            color: #333333;
        """)

        # Load emoji font
        font_db = QFontDatabase()
        font_id = font_db.addApplicationFont(r"D:\seguiemj.ttf")
        self.emoji_font = QFont(font_db.applicationFontFamilies(font_id)[0], 12) if font_id != -1 else QFont("Arial",
                                                                                                             12)

        # Topbar - Modern design
        topbar = QWidget()
        topbar.setFixedHeight(60)
        topbar.setStyleSheet("""
            background-color: #2c3e50;
            border-radius: 0px;
        """)
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(20, 0, 20, 0)

        topbar_label = QLabel("🔧 Gestion des Chaînes")
        topbar_label.setFont(QFont(self.emoji_font.family(), 16, QFont.Bold))
        topbar_label.setStyleSheet("color: white;")
        topbar_layout.addWidget(topbar_label)

        topbar_layout.addStretch()

        # Add user info/logout button if needed
        main_layout.addWidget(topbar)

        # Main content
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        main_layout.addWidget(content_widget)

        # Sidebar - Modern design
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

        # Main content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        content_layout.addWidget(scroll)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(20, 20, 20, 20)
        scroll_layout.setSpacing(20)
        scroll.setWidget(scroll_content)

        # Search section - Modern design
        search_frame = QFrame()
        search_frame.setStyleSheet("""
            background-color: white;
            border-radius: 8px;
            padding: 15px;
        """)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher par ID de chaîne...")
        self.search_input.setFont(QFont("Arial", 11))
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        search_layout.addWidget(self.search_input)

        search_btn = QPushButton("🔍 Rechercher")
        search_btn.setFont(self.emoji_font)
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        search_btn.clicked.connect(self.chercher_par_nom)
        search_layout.addWidget(search_btn)

        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.setFont(self.emoji_font)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        refresh_btn.clicked.connect(self.loadRoles)
        search_layout.addWidget(refresh_btn)

        scroll_layout.addWidget(search_frame)

        # Table section - Improved with larger size
        table_frame = QFrame()
        table_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
        """)
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(15, 15, 15, 15)
        table_layout.setSpacing(15)

        # Table title
        table_title = QLabel("📋 Liste des Chaînes")
        table_title.setFont(QFont(self.emoji_font.family(), 14, QFont.Bold))
        table_title.setStyleSheet("color: #2c3e50;")
        table_layout.addWidget(table_title)

        # Create the table with larger size
        self.roles_table = QTableWidget()
        self.roles_table.setMinimumHeight(400)  # Increased height
        self.roles_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.roles_table.setColumnCount(1)
        self.roles_table.setHorizontalHeaderLabels(["ID Chaîne"])
        self.roles_table.horizontalHeader().setHighlightSections(False)
        self.roles_table.verticalHeader().setVisible(False)
        self.roles_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.roles_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.roles_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.roles_table.setSortingEnabled(True)
        self.roles_table.setShowGrid(False)
        self.roles_table.setAlternatingRowColors(True)

        # Table style
        self.roles_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                alternate-background-color: #f9f9f9;
            }
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 10px;
                border-bottom: 1px solid #f0f0f0;
                color: #333;
            }
            QTableWidget::item:selected {
                background-color: #d6eaf8;
                color: black;
            }
        """)

        # Column width adjustment
        header = self.roles_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        # Add table to a scrollable container
        table_container = QScrollArea()
        table_container.setWidgetResizable(True)
        table_container.setWidget(self.roles_table)
        table_container.setMinimumHeight(450)
        table_layout.addWidget(table_container)

        scroll_layout.addWidget(table_frame, stretch=1)  # Takes more vertical space

        # Add/Delete role section - Modern design
        role_management_frame = QFrame()
        role_management_frame.setStyleSheet("""
            background-color: white;
            border-radius: 8px;
            padding: 15px;
        """)
        role_layout = QHBoxLayout(role_management_frame)
        role_layout.setSpacing(10)

        self.input_role = QLineEdit()
        self.input_role.setPlaceholderText("ID de chaîne")
        self.input_role.setFont(QFont("Arial", 11))
        self.input_role.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        role_layout.addWidget(self.input_role)

        add_btn = QPushButton("➕ Ajouter")
        add_btn.setFont(self.emoji_font)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        add_btn.clicked.connect(self.addRole)
        role_layout.addWidget(add_btn)

        delete_btn = QPushButton("🗑 Supprimer")
        delete_btn.setFont(self.emoji_font)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        delete_btn.clicked.connect(self.supprimer_chaine)
        role_layout.addWidget(delete_btn)

        scroll_layout.addWidget(role_management_frame)

        # Configuration section - Modern design
        config_frame = QFrame()
        config_frame.setStyleSheet("""
            background-color: white;
            border-radius: 8px;
            padding: 15px;
        """)
        config_layout = QVBoxLayout(config_frame)

        config_label = QLabel("⚙️ Configurer l'objectif")
        config_label.setFont(QFont(self.emoji_font.family(), 16, QFont.Bold))
        config_label.setStyleSheet("color: #2c3e50; margin-bottom: 15px;")
        config_layout.addWidget(config_label)

        # Chain and model selection - Modern design
        selection_frame = QFrame()
        selection_frame.setStyleSheet("border: none;")
        selection_layout = QHBoxLayout(selection_frame)
        selection_layout.setSpacing(20)

        chain_group = QFrame()
        chain_group.setStyleSheet("border: none;")
        chain_layout = QVBoxLayout(chain_group)
        chain_layout.setSpacing(5)

        chain_label = QLabel("Sélectionner une chaîne:")
        chain_label.setFont(QFont("Arial", 11, QFont.Bold))
        chain_layout.addWidget(chain_label)

        self.chaine_id = QComboBox()
        self.chaine_id.setFont(QFont("Arial", 11))
        self.chaine_id.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                min-width: 200px;
            }
        """)
        self.chaine_id.currentTextChanged.connect(self.on_chaine_select)
        chain_layout.addWidget(self.chaine_id)
        selection_layout.addWidget(chain_group)

        model_group = QFrame()
        model_group.setStyleSheet("border: none;")
        model_layout = QVBoxLayout(model_group)
        model_layout.setSpacing(5)

        model_label = QLabel("Sélectionner un modèle:")
        model_label.setFont(QFont("Arial", 11, QFont.Bold))
        model_layout.addWidget(model_label)

        self.model_id = QComboBox()
        self.model_id.setFont(QFont("Arial", 11))
        self.model_id.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                min-width: 200px;
            }
        """)
        self.model_id.currentTextChanged.connect(self.on_model_select)
        model_layout.addWidget(self.model_id)
        selection_layout.addWidget(model_group)

        selection_layout.addStretch()
        config_layout.addWidget(selection_frame)

        # Regimes section - Modern design
        regimes_frame = QFrame()
        regimes_frame.setStyleSheet("border: none;")
        regimes_layout = QHBoxLayout(regimes_frame)
        regimes_layout.setSpacing(20)

        # Regime 42H - Modern card design
        regime_42 = QFrame()
        regime_42.setStyleSheet("""
            background-color: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #ddd;
        """)
        regime_42_layout = QVBoxLayout(regime_42)
        regime_42_layout.setContentsMargins(15, 15, 15, 15)
        regime_42_layout.setSpacing(10)

        regime_42_label = QLabel("⏰ Régime 42H")
        regime_42_label.setFont(QFont(self.emoji_font.family(), 14, QFont.Bold))
        regime_42_label.setStyleSheet("color: #2c3e50;")
        regime_42_layout.addWidget(regime_42_label)

        # Table-like layout for days
        days_grid = QGridLayout()
        days_grid.setHorizontalSpacing(15)
        days_grid.setVerticalSpacing(8)

        # Header
        days_grid.addWidget(QLabel("Jour"), 0, 0)
        days_grid.addWidget(QLabel("Heures/Jour"), 0, 1)
        days_grid.addWidget(QLabel("Paires/Jour"), 0, 2)

        # Style for header labels
        for i in range(3):
            header_item = days_grid.itemAtPosition(0, i).widget()
            header_item.setFont(QFont("Arial", 10, QFont.Bold))
            header_item.setStyleSheet("color: #7f8c8d;")

        days_42 = [
            ("Lundi", "input_heure_lundi_42", "input_lundi_42", "7"),
            ("Mardi", "input_heure_mardi_42", "input_mardi_42", "7"),
            ("Mercredi", "input_heure_mercredi_42", "input_mercredi_42", "7"),
            ("Jeudi", "input_heure_jeudi_42", "input_jeudi_42", "7"),
            ("Vendredi", "input_heure_vendredi_42", "input_vendredi_42", "7"),
            ("Samedi", "input_heure_samedi_42", "input_samedi_42", "7")
        ]

        float_validator = QDoubleValidator()
        int_validator = QIntValidator()

        for row, (day, heure_id, paire_id, default_heure) in enumerate(days_42, 1):
            day_label = QLabel(day)
            day_label.setFont(QFont("Arial", 10))
            days_grid.addWidget(day_label, row, 0)

            heure_input = QLineEdit()
            heure_input.setObjectName(heure_id)
            heure_input.setText(default_heure)
            heure_input.setValidator(float_validator)
            heure_input.setStyleSheet("""
                QLineEdit {
                    padding: 5px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }
            """)
            days_grid.addWidget(heure_input, row, 1)

            paire_input = QLineEdit()
            paire_input.setObjectName(paire_id)
            paire_input.setValidator(int_validator)
            paire_input.setStyleSheet("""
                QLineEdit {
                    padding: 5px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }
            """)
            days_grid.addWidget(paire_input, row, 2)

            setattr(self, heure_id, heure_input)
            setattr(self, paire_id, paire_input)

        regime_42_layout.addLayout(days_grid)
        regimes_layout.addWidget(regime_42)

        # Regime 48H - Modern card design
        regime_48 = QFrame()
        regime_48.setStyleSheet("""
            background-color: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #ddd;
        """)
        regime_48_layout = QVBoxLayout(regime_48)
        regime_48_layout.setContentsMargins(15, 15, 15, 15)
        regime_48_layout.setSpacing(10)

        regime_48_label = QLabel("⏰ Régime 48H")
        regime_48_label.setFont(QFont(self.emoji_font.family(), 14, QFont.Bold))
        regime_48_label.setStyleSheet("color: #2c3e50;")
        regime_48_layout.addWidget(regime_48_label)

        # Table-like layout for days
        days_grid_48 = QGridLayout()
        days_grid_48.setHorizontalSpacing(15)
        days_grid_48.setVerticalSpacing(8)

        # Header
        days_grid_48.addWidget(QLabel("Jour"), 0, 0)
        days_grid_48.addWidget(QLabel("Heures/Jour"), 0, 1)
        days_grid_48.addWidget(QLabel("Paires/Jour"), 0, 2)

        # Style for header labels
        for i in range(3):
            header_item = days_grid_48.itemAtPosition(0, i).widget()
            header_item.setFont(QFont("Arial", 10, QFont.Bold))
            header_item.setStyleSheet("color: #7f8c8d;")

        days_48 = [
            ("Lundi", "input_heure_lundi_48", "input_lundi_48", "8.5"),
            ("Mardi", "input_heure_mardi_48", "input_mardi_48", "8.5"),
            ("Mercredi", "input_heure_mercredi_48", "input_mercredi_48", "8.5"),
            ("Jeudi", "input_heure_jeudi_48", "input_jeudi_48", "8.5"),
            ("Vendredi", "input_heure_vendredi_48", "input_vendredi_48", "8.5"),
            ("Samedi", "input_heure_samedi_48", "input_samedi_48", "5.5")
        ]

        for row, (day, heure_id, paire_id, default_heure) in enumerate(days_48, 1):
            day_label = QLabel(day)
            day_label.setFont(QFont("Arial", 10))
            days_grid_48.addWidget(day_label, row, 0)

            heure_input = QLineEdit()
            heure_input.setObjectName(heure_id)
            heure_input.setText(default_heure)
            heure_input.setValidator(float_validator)
            heure_input.setStyleSheet("""
                QLineEdit {
                    padding: 5px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }
            """)
            days_grid_48.addWidget(heure_input, row, 1)

            paire_input = QLineEdit()
            paire_input.setObjectName(paire_id)
            paire_input.setValidator(int_validator)
            paire_input.setStyleSheet("""
                QLineEdit {
                    padding: 5px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }
            """)
            days_grid_48.addWidget(paire_input, row, 2)

            setattr(self, heure_id, heure_input)
            setattr(self, paire_id, paire_input)

        regime_48_layout.addLayout(days_grid_48)
        regimes_layout.addWidget(regime_48)

        config_layout.addWidget(regimes_frame)

        # Save button - Modern design
        save_btn = QPushButton("💾 Enregistrer la configuration")
        save_btn.setFont(QFont(self.emoji_font.family(), 12))
        save_btn.setFixedHeight(45)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        save_btn.clicked.connect(self.enregistrer)
        config_layout.addWidget(save_btn, alignment=Qt.AlignCenter)

        scroll_layout.addWidget(config_frame)
        scroll_layout.addStretch()


    def on_enter(self):
        try:
            self.loadRoles()
            self.loadModels()
            if self.roles:
                self.chaine_id.setCurrentText(str(self.roles[-1]["id"]))
        except Exception as e:
            print(f"Error in on_enter: {e}")
            self.show_popup("Erreur", f"Erreur lors du chargement initial: {str(e)}")

    def display_roles(self, roles):
        try:
            self.roles_table.setRowCount(len(roles))
            self.roles_table.clearContents()

            for row, role in enumerate(roles):
                item = QTableWidgetItem(str(role["id"]))
                item.setTextAlignment(Qt.AlignCenter)
                item.setFont(QFont("Arial", 11))
                self.roles_table.setItem(row, 0, item)

            # Ajustement automatique de la hauteur des lignes
            self.roles_table.resizeRowsToContents()

            # Option: tri initial par ID
            self.roles_table.sortItems(0, Qt.AscendingOrder)

        except Exception as e:
            print(f"Error in display_roles: {e}")
            self.show_popup("Erreur", f"Erreur lors de l'affichage des chaînes: {str(e)}")

    def loadRoles(self):
        try:
            print("Loading roles")
            response = make_request("get", "/manage_chaine_roles/getAllRoles")
            if response.status_code == 200:
                self.roles = response.json()[0].get("roles", [])
                print("Roles loaded:", self.roles)
                self.display_roles(self.roles)  # Utilise la nouvelle méthode
                str_roles = [str(r["id"]) for r in self.roles]
                self.chaine_id.clear()
                self.chaine_id.addItems(str_roles if str_roles else ["Aucune chaîne"])
            else:
                print(f"Error loading roles: {response.status_code}")
                self.show_popup("Erreur", f"Erreur lors du chargement des chaînes: {response.status_code}")
                self.chaine_id.clear()
                self.chaine_id.addItem("Aucune chaîne")
        except Exception as e:
            print(f"Error in loadRoles: {e}")
            self.show_popup("Erreur", f"Erreur lors du chargement des chaînes: {str(e)}")
            self.chaine_id.clear()
            self.chaine_id.addItem("Aucune chaîne")

    def loadModels(self):
        try:
            print("Loading models")
            response = make_request("get", "/manage_chaine_roles/get_all_models")
            if response.status_code == 200:
                self.modeles = [model["nom_modele"] for model in response.json()[0].get("modeles", [])]
                print("Models loaded:", self.modeles)
                self.model_id.clear()
                self.model_id.addItems(self.modeles if self.modeles else ["Aucun modèle"])
            else:
                print(f"Error loading models: {response.status_code}")
                self.show_popup("Erreur", f"Erreur lors du chargement des modèles: {response.status_code}")
                self.model_id.clear()
                self.model_id.addItem("Aucun modèle")
        except Exception as e:
            print(f"Error in loadModels: {e}")
            self.show_popup("Erreur", f"Erreur lors du chargement des modèles: {str(e)}")
            self.model_id.clear()
            self.model_id.addItem("Aucun modèle")

    def addRole(self):
        try:
            role = self.input_role.text().strip()
            if not role:
                self.show_popup("Attention", "Veuillez introduire un ID de chaîne valide")
                return
            data = {"id": role}
            response = make_request("post", "/manage_chaine_roles/addchaineOrRole", json=data)
            if response.status_code == 200:
                self.show_popup("Succès", "✅ Chaîne ajoutée avec succès !")
                self.input_role.clear()
                self.loadRoles()
            elif response.status_code == 409:
                self.show_popup("Attention", "Cette chaîne existe déjà !")
            else:
                self.show_popup("Erreur", f"Erreur lors de l'ajout de la chaîne: {response.status_code}")
        except Exception as e:
            print(f"Error in addRole: {e}")
            self.show_popup("Erreur", f"Erreur lors de l'ajout de la chaîne: {str(e)}")

    def supprimer_chaine(self):
        try:
            chaine = self.input_role.text().strip()
            if not chaine:
                self.show_popup("Attention", "Veuillez introduire un ID de chaîne valide")
                return
            data = {"id": chaine}
            response = make_request("delete", "/manage_chaine_roles/deletechaine", json=data)
            if response.status_code == 200:
                self.show_popup("Succès", "✅ Chaîne supprimée avec succès !")
                self.input_role.clear()
                self.loadRoles()
            elif response.status_code == 404:
                self.show_popup("Attention", "Cette chaîne n'existe pas !")
            else:
                self.show_popup("Erreur", f"Erreur lors de la suppression de la chaîne: {response.status_code}")
        except Exception as e:
            print(f"Error in supprimer_chaine: {e}")
            self.show_popup("Erreur", f"Erreur lors de la suppression de la chaîne: {str(e)}")

    def enregistrer(self):
        try:
            chaine = self.chaine_id.currentText()
            model = self.model_id.currentText()
            if not chaine or chaine == "Aucune chaîne" or not model or model == "Aucun modèle":
                self.show_popup("Attention", "Veuillez sélectionner une chaîne et un modèle valides")
                return
            data = {
                "modele": model,
                "chaine": chaine,
                "listeRegimeHoraire": [
                    {
                        "regime": 42,
                        "joursSemaine": {
                            "horaireLundi": self.input_heure_lundi_42.text(),
                            "nbPaireLundi": self.input_lundi_42.text(),
                            "horaireMardi": self.input_heure_mardi_42.text(),
                            "nbPaireMardi": self.input_mardi_42.text(),
                            "horaireMercredi": self.input_heure_mercredi_42.text(),
                            "nbPaireMercredi": self.input_mercredi_42.text(),
                            "horaireJeudi": self.input_heure_jeudi_42.text(),
                            "nbPaireJeudi": self.input_jeudi_42.text(),
                            "horaireVendredi": self.input_heure_vendredi_42.text(),
                            "nbPaireVendredi": self.input_vendredi_42.text(),
                            "horaireSamedi": self.input_heure_samedi_42.text(),
                            "nbPaireSamedi": self.input_samedi_42.text()
                        }
                    },
                    {
                        "regime": 48,
                        "joursSemaine": {
                            "horaireLundi": self.input_heure_lundi_48.text(),
                            "nbPaireLundi": self.input_lundi_48.text(),
                            "horaireMardi": self.input_heure_mardi_48.text(),
                            "nbPaireMardi": self.input_mardi_48.text(),
                            "horaireMercredi": self.input_heure_mercredi_48.text(),
                            "nbPaireMercredi": self.input_mercredi_48.text(),
                            "horaireJeudi": self.input_heure_jeudi_48.text(),
                            "nbPaireJeudi": self.input_jeudi_48.text(),
                            "horaireVendredi": self.input_heure_vendredi_48.text(),
                            "nbPaireVendredi": self.input_vendredi_48.text(),
                            "horaireSamedi": self.input_heure_samedi_48.text(),
                            "nbPaireSamedi": self.input_samedi_48.text()
                        }
                    }
                ]
            }
            response = make_request("post", "/manage_chaine_roles/addOrUpdatePlanification", json=data)
            if response.status_code in (200,201):
                self.show_popup("Succès", "✅ Planification enregistrée avec succès !")
                self.loadRoles()
            elif response.status_code == 409:
                self.show_popup("Attention", "Planification existe déjà pour cette chaîne et ce modèle")
            else:
                self.show_popup("Erreur", f"Erreur lors de l'enregistrement: {response.status_code}")
        except Exception as e:
            print(f"Error in enregistrer: {e}")
            self.show_popup("Erreur", f"Erreur lors de l'enregistrement: {str(e)}")

    def get_plan_by_modelAndChaine(self, chaine, modele):
        try:
            print(f"Fetching plan for chaine: {chaine}, modele: {modele}")
            data = {"chaine": chaine, "modele": modele}
            response = make_request("get", "/manage_chaine_roles/getPlanBymodelChaine", json=data)
            if response.status_code == 200:
                plan = response.json()[0].get("plan", [])
                print("Plan loaded:", plan)
                if plan:
                    for p in plan:
                        regime = p.get("regimeHoraire")
                        if regime == 42:
                            self.input_heure_lundi_42.setText(str(p.get("horaireLundi", "7")))
                            self.input_lundi_42.setText(str(p.get("nbPaireLundi", "")))
                            self.input_heure_mardi_42.setText(str(p.get("horaireMardi", "7")))
                            self.input_mardi_42.setText(str(p.get("nbPaireMardi", "")))
                            self.input_heure_mercredi_42.setText(str(p.get("horaireMercredi", "7")))
                            self.input_mercredi_42.setText(str(p.get("nbPaireMercredi", "")))
                            self.input_heure_jeudi_42.setText(str(p.get("horaireJeudi", "7")))
                            self.input_jeudi_42.setText(str(p.get("nbPaireJeudi", "")))
                            self.input_heure_vendredi_42.setText(str(p.get("horaireVendredi", "7")))
                            self.input_vendredi_42.setText(str(p.get("nbPaireVendredi", "")))
                            self.input_heure_samedi_42.setText(str(p.get("horaireSamedi", "7")))
                            self.input_samedi_42.setText(str(p.get("nbPaireSamedi", "")))
                        if regime == 48:
                            self.input_heure_lundi_48.setText(str(p.get("horaireLundi", "8.5")))
                            self.input_lundi_48.setText(str(p.get("nbPaireLundi", "")))
                            self.input_heure_mardi_48.setText(str(p.get("horaireMardi", "8.5")))
                            self.input_mardi_48.setText(str(p.get("nbPaireMardi", "")))
                            self.input_heure_mercredi_48.setText(str(p.get("horaireMercredi", "8.5")))
                            self.input_mercredi_48.setText(str(p.get("nbPaireMercredi", "")))
                            self.input_heure_jeudi_48.setText(str(p.get("horaireJeudi", "8.5")))
                            self.input_jeudi_48.setText(str(p.get("nbPaireJeudi", "")))
                            self.input_heure_vendredi_48.setText(str(p.get("horaireVendredi", "8.5")))
                            self.input_vendredi_48.setText(str(p.get("nbPaireVendredi", "")))
                            self.input_heure_samedi_48.setText(str(p.get("horaireSamedi", "5.5")))
                            self.input_samedi_48.setText(str(p.get("nbPaireSamedi", "")))
                else:
                    self.reset_plan_fields()
            else:
                print(f"Error fetching plan: {response.status_code}")
                self.show_popup("Erreur", f"Erreur lors de la récupération du plan: {response.status_code}")
                self.reset_plan_fields()
        except Exception as e:
            print(f"Error in get_plan_by_modelAndChaine: {e}")
            self.show_popup("Erreur", f"Erreur lors de la récupération du plan: {str(e)}")
            self.reset_plan_fields()

    def reset_plan_fields(self):
        self.input_heure_lundi_42.setText("7")
        self.input_lundi_42.setText("")
        self.input_heure_mardi_42.setText("7")
        self.input_mardi_42.setText("")
        self.input_heure_mercredi_42.setText("7")
        self.input_mercredi_42.setText("")
        self.input_heure_jeudi_42.setText("7")
        self.input_jeudi_42.setText("")
        self.input_heure_vendredi_42.setText("7")
        self.input_vendredi_42.setText("")
        self.input_heure_samedi_42.setText("7")
        self.input_samedi_42.setText("")
        self.input_heure_lundi_48.setText("8.5")
        self.input_lundi_48.setText("")
        self.input_heure_mardi_48.setText("8.5")
        self.input_mardi_48.setText("")
        self.input_heure_mercredi_48.setText("8.5")
        self.input_mercredi_48.setText("")
        self.input_heure_jeudi_48.setText("8.5")
        self.input_jeudi_48.setText("")
        self.input_heure_vendredi_48.setText("8.5")
        self.input_vendredi_48.setText("")
        self.input_heure_samedi_48.setText("5.5")
        self.input_samedi_48.setText("")

    def on_model_select(self, text):
        try:
            chaine = self.chaine_id.currentText()
            str_roles = [str(r["id"]) for r in self.roles]
            if chaine in str_roles and text in self.modeles:
                self.get_plan_by_modelAndChaine(chaine, text)
        except Exception as e:
            print(f"Error in on_model_select: {e}")
            self.show_popup("Erreur", f"Erreur lors de la sélection du modèle: {str(e)}")

    def on_chaine_select(self, text):
        try:
            modele = self.model_id.currentText()
            str_roles = [str(r["id"]) for r in self.roles]
            if text in str_roles and modele in self.modeles:
                self.get_plan_by_modelAndChaine(text, modele)
        except Exception as e:
            print(f"Error in on_chaine_select: {e}")
            self.show_popup("Erreur", f"Erreur lors de la sélection de la chaîne: {str(e)}")

    def chercher_par_nom(self):
        try:
            search_text = self.search_input.text().strip()
            print("Searching for:", search_text)
            if search_text:
                filtered_roles = [role for role in self.roles if search_text.lower() in str(role["id"]).lower()]
                self.display_roles(filtered_roles)
            else:
                self.display_roles(self.roles)
        except Exception as e:
            print(f"Error in chercher_par_nom: {e}")
            self.show_popup("Erreur", f"Erreur lors de la recherche: {str(e)}")

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

    def root_to_addUser(self):
        self.switch_screen.emit("adduser_screen")

    def root_to_listUsers(self):
        self.switch_screen.emit("list_users_screen")

    def root_to_gestionRole(self):
        self.switch_screen.emit("gestion_role_screen")

    def logout(self):
        self.session.set_tokens(None, None)
        self.switch_screen.emit("login_screen")

