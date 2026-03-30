import math
import traceback

import requests
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                             QLineEdit, QPushButton, QScrollArea, QGridLayout, QCheckBox, QDialog,
                             QMessageBox, QFrame, QTableWidget)
from PyQt5.QtGui import QFont, QFontDatabase, QColor, QDoubleValidator, QIntValidator
from PyQt5.QtCore import Qt, pyqtSignal
from frontend.Client import make_request


class SelectableRowWidget(QWidget):
    def __init__(self, row_data, col_widths, on_selection_change=None):
        super().__init__()
        self.row_data = row_data
        self.col_widths = col_widths
        self.on_selection_change = on_selection_change
        self.selected = False
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setFixedHeight(40)
        self.setStyleSheet("""
            background-color: white;
            border-bottom: 1px solid #ddd;
        """ if not self.selected else """
            background-color: rgba(153, 204, 255, 255);
            border-bottom: 1px solid #ddd;
        """)

        for i, val in enumerate(self.row_data):
            label = QLabel(str(val))
            label.setFont(QFont("Arial", 10))
            label.setFixedWidth(self.col_widths[i])
            label.setFixedHeight(40)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("padding: 5px; border-right: 1px solid #ddd;")
            layout.addWidget(label)

        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        self.selected = not self.selected
        self.setStyleSheet("background-color: rgba(153, 204, 255, 255);" if self.selected else "background-color: white;")
        if self.on_selection_change:
            self.on_selection_change()
        event.accept()

    def is_selected(self):
        return self.selected


class RegimeDialog(QDialog):
    def __init__(self, chaine, regime, modele, titre, plan, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Formulaire Régime Horaire")
        self.setMinimumSize(400, 300)
        self.setMaximumSize(600, 500)
        self.chaine = chaine
        self.regime = regime
        self.modele = modele
        self.titre = titre
        self.plan = plan
        self.regime_inputs = {}
        self.init_ui()

    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        self.setStyleSheet("background-color: #F5F5F5;")

        title_label = QLabel(f"<b>Régime {self.titre}</b>")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFixedHeight(30)
        main_layout.addWidget(title_label)

        # Header row
        header = QHBoxLayout()
        jour_label = QLabel("Jour")
        jour_label.setStyleSheet("color: black;")
        jour_label.setFixedWidth(120)
        header.addWidget(jour_label)

        heure_label = QLabel("Heure/jour")
        heure_label.setStyleSheet("color: black;")
        heure_label.setFixedWidth(90)
        header.addWidget(heure_label)

        paire_label = QLabel("Paires/jour")
        paire_label.setStyleSheet("color: black;")
        paire_label.setFixedWidth(90)
        header.addWidget(paire_label)
        main_layout.addLayout(header)

        # Days inputs
        jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
        for jour in jours:
            row = QHBoxLayout()
            row.setSpacing(3)
            jour_label = QLabel(f"{jour} :")
            jour_label.setStyleSheet("color: black;")
            jour_label.setFixedWidth(120)
            row.addWidget(jour_label)

            horaire_val = str(self.plan.get(f"horaire{jour}", "7"))
            nbpaire_val = str(self.plan.get(f"nbPaire{jour}", ""))

            heure_input = QLineEdit(horaire_val)
            heure_input.setFixedHeight(28)
            heure_input.setFixedWidth(90)
            heure_input.setValidator(QDoubleValidator())

            paire_input = QLineEdit(nbpaire_val)
            paire_input.setFixedHeight(28)
            paire_input.setFixedWidth(90)
            paire_input.setValidator(QIntValidator())

            self.regime_inputs[f"horaire{jour}"] = heure_input
            self.regime_inputs[f"nbPaire{jour}"] = paire_input

            row.addWidget(heure_input)
            row.addWidget(paire_input)
            main_layout.addLayout(row)

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)
        btn_layout.addStretch()

        btn_close = QPushButton("Fermer")
        btn_close.setFixedSize(120, 40)
        btn_close.setStyleSheet("background-color: rgba(255, 102, 102, 255); color: white;")
        btn_close.clicked.connect(self.reject)

        btn_save = QPushButton("Enregistrer")
        btn_save.setFixedSize(150, 40)
        btn_save.setStyleSheet("background-color: rgba(102, 179, 255, 255); color: white;")
        btn_save.clicked.connect(self.accept)

        btn_layout.addWidget(btn_close)
        btn_layout.addWidget(btn_save)
        main_layout.addLayout(btn_layout)

    def get_data(self):
        data = {
            "chaine": self.chaine,
            "regime": self.regime,
            "modele": self.modele
        }
        for key, input_field in self.regime_inputs.items():
            value = input_field.text().strip()
            if not value:
                raise ValueError(f"Champ {key} ne peut pas être vide")
            if "horaire" in key and not value.replace(".", "").isdigit():
                raise ValueError(f"Champ {key} doit être un nombre valide")
            if "nbPaire" in key and not value.isdigit():
                raise ValueError(f"Champ {key} doit être un entier")
            data[key] = value
        return data


class LaunchWindow(QWidget):

    switch_screen = pyqtSignal(str)  # Add signal for navigation

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tableau de bord")
        self.show_table = False
        self.show_checkbox = False
        self.of_chaines = []
        self.df = []
        self.selected_rows = []
        self.checks = []
        self.checksChainePicure = []
        self.planification = []
        self.qte_total = 0
        self.init_ui()
        self.on_enter()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setStyleSheet("background-color: #F5F5F5;")

        # Load emoji font with fallback
        font_db = QFontDatabase()
        font_path = "seguiemj.ttf"
        font_id = font_db.addApplicationFont(font_path)
        self.emoji_font = QFont(font_db.applicationFontFamilies(font_id)[0], 12) if font_id != -1 else QFont("Arial",
                                                                                                             12)

        # Topbar
        topbar = QWidget()
        topbar.setFixedHeight(50)
        topbar.setStyleSheet("background-color: rgba(51, 128, 204, 255);")
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(10, 0, 10, 0)
        topbar_label = QLabel("📊 Tableau de bord")
        topbar_label.setFont(QFont(self.emoji_font.family(), 14, QFont.Bold))
        topbar_label.setStyleSheet("color: white;")
        topbar_layout.addWidget(topbar_label)
        main_layout.addWidget(topbar)

        # Main content
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(content_widget)

        # Sidebar
        sidebar = QWidget()
        sidebar.setMinimumWidth(150)
        sidebar.setStyleSheet("background-color: #f0f0f0;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(5, 20, 5, 20)
        sidebar_layout.setSpacing(10)

        buttons = [
            ("Lancement", self.root_to_lancement),
            ("Modification", self.root_to_update_launch),
            ("Rapports", self.root_to_dashboardProduction),
            ("En cours", self.root_to_ofs_encours),
            ("Déconnexion", self.logout)
        ]
        for text, callback in buttons:
            btn = QPushButton(text)
            btn.setFont(QFont("Arial", 10))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #e7e7e7;
                    border: none;
                    padding: 8px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #d7d7d7;
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
        scroll_layout.setContentsMargins(15, 15, 15, 15)
        scroll_layout.setSpacing(15)
        scroll.setWidget(scroll_content)

        # Search form
        self.search_form = QWidget()  # Store as instance variable for easier debugging
        self.search_form.setFixedHeight(50)
        search_layout = QHBoxLayout(self.search_form)
        search_layout.setSpacing(10)

        self.column_spinner = QComboBox()
        self.column_spinner.addItems(
            ["Toutes les colonnes", "dateLancement", "numOF", "Modele", "Coloris", "SAIS", "Pointure"])
        self.column_spinner.setFixedWidth(150)
        self.column_spinner.setFont(self.emoji_font)
        self.column_spinner.setStyleSheet("background-color: #F5F5F5; color: black;")
        search_layout.addWidget(self.column_spinner)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Rechercher...")
        self.search_input.setFont(self.emoji_font)
        self.search_input.setFixedWidth(150)
        self.search_input.setFixedHeight(50)
        self.search_input.setStyleSheet("background-color: #F5F5F5; color: black; padding: 5px;")
        search_layout.addWidget(self.search_input)

        search_btn = QPushButton("🔎 Rechercher")
        search_btn.setFont(self.emoji_font)
        search_btn.setFixedSize(150, 50)
        search_btn.setStyleSheet("background-color: rgba(179, 217, 255, 255); color: black; border: 1px solid #808080;")
        search_btn.clicked.connect(self.search)
        search_layout.addWidget(search_btn)

        reset_btn = QPushButton("🔄 Réinitialiser")
        reset_btn.setFont(self.emoji_font)
        reset_btn.setFixedSize(150, 50)
        reset_btn.setStyleSheet("background-color: rgba(255, 179, 179, 255); color: black; border: 1px solid #808080;")
        reset_btn.clicked.connect(self.reset_filter)
        search_layout.addWidget(reset_btn)
        scroll_layout.addWidget(self.search_form)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setFont(self.emoji_font)
        self.status_label.setFixedHeight(30)
        self.status_label.setStyleSheet("color: rgba(51, 51, 51, 255);")
        scroll_layout.addWidget(self.status_label)

        # Table container
        self.box_table_container = QWidget()
        self.box_table_container.setMinimumHeight(500)
        table_layout = QVBoxLayout(self.box_table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)

        # Header
        self.header_widget = QWidget()
        self.header_grid = QGridLayout(self.header_widget)
        self.header_grid.setSpacing(0)
        self.header_grid.setContentsMargins(0, 0, 0, 0)
        table_layout.addWidget(self.header_widget)

        # Table content
        self.table_content = QWidget()
        self.table_grid = QGridLayout(self.table_content)
        self.table_grid.setSpacing(0)
        self.table_grid.setContentsMargins(0, 0, 0, 0)
        self.table_scroll = QScrollArea()
        self.table_scroll.setWidgetResizable(True)
        self.table_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_scroll.setWidget(self.table_content)
        table_layout.addWidget(self.table_scroll, 1)

        scroll_layout.addWidget(self.box_table_container)
        # Total quantity label
        self.qte_total_label = QLabel("")
        self.qte_total_label.setFont(self.emoji_font)
        self.qte_total_label.setFixedHeight(30)
        self.qte_total_label.setStyleSheet("color: rgba(51, 51, 51, 255);")
        scroll_layout.addWidget(self.qte_total_label)

        # Regime section
        self.regime_section = QWidget()
        self.regime_section.setFixedHeight(120)
        regime_layout = QVBoxLayout(self.regime_section)
        regime_layout.setContentsMargins(20, 20, 20, 20)
        regime_layout.setSpacing(15)

        regime_label = QLabel("🛠️ Sélectionner Le régime horaire")
        regime_label.setFont(QFont(self.emoji_font.family(), 18, QFont.Bold))
        regime_label.setStyleSheet("color: rgba(51, 51, 51, 255); background-color: #ECECEC;")
        regime_label.setFixedHeight(50)
        regime_layout.addWidget(regime_label)

        self.regimeHoraire_id = QComboBox()
        self.regimeHoraire_id.addItems(["Choisir le régime horaire", "42h", "48h"])
        self.regimeHoraire_id.setCurrentText("42h")
        self.regimeHoraire_id.setFont(self.emoji_font)
        self.regimeHoraire_id.setFixedSize(250, 50)
        self.regimeHoraire_id.setStyleSheet("background-color: white; color: black; border: 1.2px solid #CCCCCC;")
        regime_layout.addWidget(self.regimeHoraire_id)
        scroll_layout.addWidget(self.regime_section)

        # Chain type section
        self.my_checkbox = QWidget()
        checkbox_layout = QVBoxLayout(self.my_checkbox)
        checkbox_layout.setContentsMargins(20, 20, 20, 20)
        checkbox_layout.setSpacing(15)

        checkbox_label = QLabel("🛠️ Sélectionner type de chaîne")
        checkbox_label.setFont(QFont(self.emoji_font.family(), 18, QFont.Bold))
        checkbox_label.setStyleSheet("color: rgba(51, 51, 51, 255); background-color: #ECECEC;")
        checkbox_label.setFixedHeight(50)
        checkbox_layout.addWidget(checkbox_label)

        self.type_chaine = QGridLayout()
        self.type_chaine.setHorizontalSpacing(30)
        self.type_chaine.setVerticalSpacing(30)
        self.type_chaine.setContentsMargins(30, 30, 30, 30)
        type_chaine_widget = QWidget()
        type_chaine_widget.setStyleSheet("background-color: #FAFAFA; border: 1px solid #999999;")
        type_chaine_widget.setLayout(self.type_chaine)
        checkbox_layout.addWidget(type_chaine_widget)
        scroll_layout.addWidget(self.my_checkbox)

        # Save button
        save_btn = QPushButton("Enregistrer")
        save_btn.setFont(self.emoji_font)
        save_btn.setFixedHeight(50)
        save_btn.setStyleSheet("background-color: rgba(255, 217, 102, 255); color: black; border: 1px solid #B3B3B3;")
        save_btn.clicked.connect(self.save_ofs_typechaine)
        scroll_layout.addWidget(save_btn)
        scroll_layout.addStretch()


    def root_to_lancement(self):
        self.switch_screen.emit("launch_screen")

    def root_to_update_launch(self):
        self.switch_screen.emit("update_launch_screen")

    def root_to_dashboardProduction(self):
        self.switch_screen.emit("dashboard_screen")

    def root_to_ofs_encours(self):
        self.switch_screen.emit("ofs_encours_screen")

    def logout(self):
        self.switch_screen.emit("login_screen")

    def calcul_qte_total(self, data):
        try:
            self.qte_total = sum(item["Quantite"] for item in data)
            self.qte_total_label.setText(f"{self.qte_total} paires au total")
        except Exception as e:
            print(f"Error in calcul_qte_total: {e}")
            self.show_popup("Erreur", "Erreur lors du calcul de la quantité totale")

    def loadofs(self):
        try:
            response = make_request("get", "/manage_ofs/getAllLatestOfs")
            print("loadofs response:", response.json())

            if response.status_code in (200, 201):
                data = response.json()

                # Vérifier si data est vide ou non
                if not data or not isinstance(data, list):
                    print("Aucune donnée d'OF disponible")
                    self.status_label.setText("Aucun ordre de fabrication n’a encore été créé")
                    self.show_table = False
                    self.show_checkbox = False
                    self.df = []
                else:
                    # Récupérer la liste d'OF en toute sécurité
                    self.df = data[0].get("ofs", []) if len(data) > 0 and isinstance(data[0], dict) else []

                    if not self.df:
                        print("Aucun ordre de fabrication trouvé")
                        self.status_label.setText("Aucun ordre de fabrication disponible")
                        self.show_table = False
                        self.show_checkbox = False
                    else:
                        self.calcul_qte_total(self.df)
                        self.status_label.setText("")
                        self.show_table = True
                        self.show_checkbox = True

                # Mettre à jour la table et l'interface
                self.populate_table()
                self.box_table_container.setVisible(self.show_table)
                self.regime_section.setVisible(self.show_table)
                self.my_checkbox.setVisible(self.show_checkbox)

            else:
                print("Error loading OFs:", response.status_code)
                self.show_popup("Erreur", "Impossible de charger les ordres de fabrication")
                self.status_label.setText("Erreur de chargement des données")
                self.show_table = False
                self.show_checkbox = False

        except Exception as e:
            print(f"Error in loadofs: {e}")
            self.show_popup("Erreur", f"Erreur lors du chargement des OFs: {str(e)}")
            self.status_label.setText("Erreur de connexion au serveur")
            self.show_table = False
            self.show_checkbox = False
            self.df = []

    def populate_table(self):
        try:
            # Clear existing widgets
            for i in reversed(range(self.header_grid.count())):
                self.header_grid.itemAt(i).widget().setParent(None)
            for i in reversed(range(self.table_grid.count())):
                self.table_grid.itemAt(i).widget().setParent(None)

            # Define columns and their widths
            columns = ['numOF', 'Pointure', 'Quantite', 'Coloris', 'Modele', 'SAIS', 'dateLancement', 'dateCreation',
                       'etat']
            col_widths = [150, 100, 100, 120, 150, 100, 120, 120, 100]  # Adjusted widths for better visibility
            total_width = sum(col_widths)

            # Headers
            for i, col in enumerate(columns):
                header = QLabel(str(col))
                header.setFont(QFont(self.emoji_font.family(), 10, QFont.Bold))
                header.setFixedWidth(col_widths[i])
                header.setFixedHeight(40)
                header.setAlignment(Qt.AlignCenter)
                header.setStyleSheet("color: black; padding: 5px; border: 1px solid #ddd; background-color: #ECECEC;")
                self.header_grid.addWidget(header, 0, i)

            # Table rows
            row_height = 40
            for row_idx, row in enumerate(self.df):
                row_data = []
                for col in columns:
                    value = row.get(col, "")
                    if col == "dateLancement" and isinstance(value, str):
                        value = value.split("T")[0]
                    row_data.append(str(value))

                row_widget = SelectableRowWidget(row_data, col_widths, self.on_row_selection_changed)
                self.table_grid.addWidget(row_widget, row_idx, 0, 1, len(columns))

            # Adjust content size
            content_height = len(self.df) * row_height
            self.table_content.setFixedHeight(content_height)
            self.table_content.setFixedWidth(total_width)  # Set width to fit all columns
            self.header_widget.setFixedWidth(total_width)  # Match header width to content

            # Adjust container height dynamically
            visible_height = min(800, content_height + 40)  # 40 for header
            self.box_table_container.setMinimumHeight(visible_height)
            self.table_scroll.setMinimumHeight(min(500, content_height + 40))

        except Exception as e:
            print(f"Error in populate_table: {e}")
            self.show_popup("Erreur", f"Erreur lors du remplissage de la table: {str(e)}")

    def reset_filter(self):
        try:
            self.loadofs()
            if not self.df:
                self.status_label.setText("Vous n'avez aucun ordre de fabrication à lancer pour l'instant")
                self.show_table = False
                self.show_checkbox = False
            else:
                self.status_label.setText("")
                self.show_table = True
                self.show_checkbox = True
                self.populate_table()
                self.display_roles()
            self.search_input.clear()
            self.box_table_container.setVisible(self.show_table)
            self.regime_section.setVisible(self.show_table)
            self.my_checkbox.setVisible(self.show_checkbox)
        except Exception as e:
            print(f"Error in reset_filter: {e}")
            self.show_popup("Erreur", f"Erreur lors de la réinitialisation: {str(e)}")

    def show_popup(self, title, message):
        popup = QMessageBox()
        popup.setWindowTitle(title)
        popup.setText(message)
        popup.setFont(self.emoji_font)
        popup.setStyleSheet("""
            QMessageBox { background-color: #F5F5F5; }
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

    def get_global_plan(self, chaine, regime, modele):
        print("get plan")
        try:
            data = {"modele": modele, "chaine": chaine, "regime": regime}
            response = make_request("get", "/manage_chaine_roles/getPlanBymodelChaineAndRegime", json=data)
            if response.status_code == 200:
                print(response.json())
                return response.json()[0].get("plan", {})
            return {}
        except Exception as e:
            print(f"Error in get_global_plan: {e}")
            self.show_popup("Erreur", f"Erreur lors du chargement du plan: {str(e)}")
            return {}

    def show_popup_formulaire_regimes(self, chaine, regime, modele, titre):
        try:
            listplan = [item for item in self.checks if item["chaine"] == chaine]
            plan = listplan[0] if listplan else self.get_global_plan(chaine, regime, modele)
            dialog = RegimeDialog(chaine, regime, modele, titre, plan, self)
            if dialog.exec_():
                data = dialog.get_data()
                for item in self.checks[:]:
                    if item["chaine"] == chaine:
                        self.checks.remove(item)
                self.checks.append(data)
                print(self.checks)
        except Exception as e:
            print(f"Error in show_popup_formulaire_regimes: {e}")
            self.show_popup("Erreur", f"Erreur lors de l'affichage du formulaire: {str(e)}")

    def on_enter(self):
        try:
            self.search_input.clear()
            self.regimeHoraire_id.setCurrentText("42h")
            self.loadofs()
            if not self.df:
                self.status_label.setText("Vous n'avez aucun ordre de fabrication à lancer pour l'instant")
                self.show_table = False
                self.show_checkbox = False
            else:
                self.status_label.setText("")
                self.show_table = True
                self.show_checkbox = True
                self.populate_table()
                self.display_roles()
            self.box_table_container.setVisible(self.show_table)
            self.regime_section.setVisible(self.show_table)
            self.my_checkbox.setVisible(self.show_checkbox)
        except Exception as e:
            print(f"Error in on_enter: {e}")
            self.show_popup("Erreur", f"Erreur lors du chargement: {str(e)}")

    def display_roles(self):
        try:
            for i in reversed(range(self.type_chaine.count())):
                self.type_chaine.itemAt(i).widget().setParent(None)
            roles = self.loadType_chaine()
            for row_idx, role in enumerate(roles):
                widget = self.build_role_widget(role)
                self.type_chaine.addWidget(widget, row_idx // 2, row_idx % 2)
        except Exception as e:
            print(f"Error in display_roles: {e}")
            self.show_popup("Erreur", f"Erreur lors de l'affichage des rôles: {str(e)}")

    def build_role_widget(self, role):
        try:
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setSpacing(5)
            container.setFixedHeight(140)

            top_row = QHBoxLayout()
            top_row.setSpacing(10)
            label = QLabel(role)
            label.setFont(QFont(self.emoji_font.family(), 12))
            label.setStyleSheet("color: rgba(26, 26, 26, 255);")
            label.setFixedWidth(84)
            top_row.addWidget(label)

            checkbox_row = QHBoxLayout()
            checkbox_row.setSpacing(2)
            checkbox = QCheckBox()
            checkbox.setFixedWidth(30)
            checkbox.stateChanged.connect(lambda state: self.checkbox_typeChaine(checkbox, state, role))
            eye_button = QPushButton("👁")
            eye_button.setFont(QFont(self.emoji_font.family(), 12))
            eye_button.setFixedSize(20, 20)
            eye_button.setStyleSheet("background-color: transparent; color: black;")
            eye_button.clicked.connect(lambda: self.on_eye_click(role))
            checkbox_row.addWidget(checkbox)
            checkbox_row.addWidget(eye_button)
            top_row.addLayout(checkbox_row)

            container_layout.addLayout(top_row)
            return container
        except Exception as e:
            print(f"Error in build_role_widget: {e}")
            self.show_popup("Erreur", f"Erreur lors de la création du widget de rôle: {str(e)}")
            return QWidget()

    def on_eye_click(self, role):
        try:
            regime = self.regimeHoraire_id.currentText()
            if regime == "42h":
                self.show_popup_formulaire_regimes(role, regime, self.df[0]["Modele"] if self.df else "", "42h")
            else:
                self.show_popup_formulaire_regimes(role, regime, self.df[0]["Modele"] if self.df else "", "48h")
        except Exception as e:
            print(f"Error in on_eye_click: {e}")
            self.show_popup("Erreur", f"Erreur lors du clic sur l'œil: {str(e)}")

    def loadType_chaine(self):
        try:
            response = make_request("get", "/manage_chaine_roles/getAllRoles")
            if response.status_code == 200:
                data = response.json()[0].get("roles", [])
                values = [role["id"] for role in data]
                print("Loaded roles:", values)
                return values
            else:
                print("Error loading roles:", response.status_code)
                self.show_popup("Erreur", "Impossible de charger les rôles")
                return []
        except Exception as e:
            print(f"Error in loadType_chaine: {e}")
            self.show_popup("Erreur", f"Erreur lors du chargement des rôles: {str(e)}")
            return []

    def checkbox_typeChaine(self, checkbox, state, chaine):
        try:
            if state == Qt.Checked:
                regime = self.regimeHoraire_id.currentText()
                if regime in ["42h", "48h"] and self.df:
                    self.show_popup_formulaire_regimes(chaine, regime, self.df[0]["Modele"], regime)
                else:
                    checkbox.setChecked(False)
                    self.show_popup("Attention", "Veuillez sélectionner un régime horaire valide et avoir des données OF")
            else:
                for item in self.checks[:]:
                    if item["chaine"] == chaine:
                        self.checks.remove(item)
            print(f"Chaînes sélectionnées: {self.checks}")
        except Exception as e:
            print(f"Error in checkbox_typeChaine: {e}")
            self.show_popup("Erreur", f"Erreur lors de la sélection de la chaîne: {str(e)}")

    def get_selected_rows(self):
        try:
            selected = []
            for i in range(self.table_grid.count()):
                widget = self.table_grid.itemAt(i).widget()
                if isinstance(widget, SelectableRowWidget) and widget.is_selected():
                    selected.append(widget.row_data)
            return selected
        except Exception as e:
            print(f"Error in get_selected_rows: {e}")
            self.show_popup("Erreur", f"Erreur lors de la récupération des lignes sélectionnées: {str(e)}")
            return []

    def on_row_selection_changed(self):
        try:
            self.selected_rows = self.get_selected_rows()
            print("Lignes sélectionnées:", self.selected_rows)
        except Exception as e:
            print(f"Error in on_row_selection_changed: {e}")
            self.show_popup("Erreur", f"Erreur lors de la mise à jour des lignes sélectionnées: {str(e)}")

    def getPlanBymodelChaineAndRegime(self, model, chaine, regimehoraire):
        try:
            data = {"modele": model, "chaine": chaine, "regime": regimehoraire}
            response = make_request("get", "/manage_chaine_roles/getPlanBymodelChaineAndRegime", json=data)
            print("getPlanBymodelChaineAndRegime response:", response.json())
            if response.status_code == 404:
                return None
            elif response.status_code == 200:
                return response.json()[0]
            return None
        except Exception as e:
            print(f"Error in getPlanBymodelChaineAndRegime: {e}")
            self.show_popup("Erreur", f"Erreur lors de la récupération du plan: {str(e)}")
            return None

    def closeEvent(self, event):
        # Nettoyage des ressources
        if hasattr(self, 'session'):
            self.session.close()
        event.accept()

    def save_ofs_typechaine(self):
        """Enregistrer uniquement les OF sélectionnés avec leurs chaînes assignées."""
        # Vérifier les conditions de base
        if not self.validate_save_conditions():
            return

        # Récupérer uniquement les OF sélectionnés
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            self.show_popup("Attention", "Veuillez sélectionner au moins un OF avant de lancer.")
            return

        self.of_chaines.clear()
        regime_horaire_str = self.regimeHoraire_id.currentText()

        # CORRECTION : Convertir "42h"/"48h" en integer 42/48
        try:
            regime_horaire_int = int(regime_horaire_str.replace("h", ""))
        except ValueError:
            self.show_popup("Erreur", f"Format de régime horaire invalide: {regime_horaire_str}")
            return

        try:
            # Traiter chaque configuration de chaîne
            for item in self.checks:
                self.process_chain_config_selected(item, regime_horaire_int, selected_rows)

            # Sauvegarder toutes les associations OF-chaîne
            response = make_request("post", "/manage_ofs/addOfs_chaines", json=self.of_chaines)

            self.handle_save_response(response)

        except Exception as e:
            self.show_popup("Erreur", f"Échec de l'enregistrement: {str(e)}")
            print(f"Save error: {traceback.format_exc()}")

    def process_chain_config_selected(self, item, regime_horaire_int, selected_rows):
        """Traite une seule configuration de chaîne pour les OF sélectionnés."""

        # CORRECTION : Ajouter le régime horaire au plan
        item["regimeHoraire"] = regime_horaire_int

        response = make_request("post", "/manage_planification_chaine_modele/addOrUpdatePlanification", json=item)

        if response.json()[1] != 201:
            raise ValueError(f"Échec de l'enregistrement du plan pour la chaîne {item['chaine']}")

        plan_id = response.json()[0]["id"]

        # Associer uniquement les OF sélectionnés
        for row in selected_rows:
            self.of_chaines.append({
                "regimeHoraire": regime_horaire_int,  # CORRECTION : utiliser integer
                "modele": row[4],  # Colonne 'Modele'
                "idchaine": item["chaine"],
                "numCommandeOF": row[0],  # Colonne 'numOF'
                "idPlanification": plan_id
            })
    def validate_save_conditions(self):
        """Check if we have everything needed to save."""
        if not self.checks:
            self.show_popup("Attention", "Veuillez sélectionner au moins une chaîne")
            return False
        if not self.df:
            self.show_popup("Attention", "Aucun ordre de fabrication à enregistrer")
            return False
        return True

    def process_chain_config(self, item, regime_horaire_str):
        """Process a single chain configuration."""

        # CORRECTION : Convertir en integer
        try:
            regime_horaire_int = int(regime_horaire_str.replace("h", ""))
        except ValueError:
            raise ValueError(f"Format de régime horaire invalide: {regime_horaire_str}")

        # CORRECTION : Ajouter le régime horaire au plan
        item["regimeHoraire"] = regime_horaire_int

        response = make_request("post", "/manage_planification_chaine_modele/addOrUpdatePlanification", json=item)

        if response.json()[1] != 201:
            raise ValueError(f"Échec de l'enregistrement du plan pour la chaîne {item['chaine']}")

        plan_id = response.json()[0]["id"]
        self.create_of_chaines_associations(plan_id, item["chaine"], regime_horaire_int)  # CORRECTION : passer integer

    def create_of_chaines_associations(self, plan_id, chaine, regime_horaire_int):
        """Create OF-chain associations for all current OFs."""
        for of in self.df:
            self.of_chaines.append({
                "regimeHoraire": regime_horaire_int,  # CORRECTION : integer
                "modele": of.get("Modele"),
                "idchaine": chaine,
                "numCommandeOF": of.get("numOF"),
                "idPlanification": plan_id
            })

    def handle_save_response(self, response):
        """Handle the response from the save operation."""
        if response.status_code == 200:
            self.show_success()
        elif response.status_code == 409:
            self.show_popup("Attention", "L'affectation des chaînes pour ces OFs a déjà été faite")
        else:
            self.show_popup("Erreur", "Vous n'êtes pas autorisé à effectuer cette opération")

    def show_success(self):
        """Update UI after successful save."""
        self.display_roles()
        self.show_popup("Succès", "OFs enregistrés avec succès")
        self.loadofs()
        self.checks = []

        if not self.df:
            self.status_label.setText("Vous n'avez aucun ordre de fabrication à lancer pour l'instant")
            self.show_table = False
        else:
            self.status_label.setText("")
            self.show_table = True
            self.search_input.clear()

    def search(self):
        try:
            # Debug logs
            print("Début de la recherche...")

            search_text = self.search_input.text().strip().lower()
            selected_column = self.column_spinner.currentText()

            print(f"Recherche: '{search_text}' dans colonne: '{selected_column}'")

            if not search_text:
                self.show_popup("Attention", "Veuillez entrer un terme de recherche.")
                return

            columns = ['numOF', 'Pointure', 'Quantite', 'Coloris', 'Modele',
                       'SAIS', 'dateLancement', 'dateCreation', 'etat']

            # Sauvegarde des données originales pour reset
            if not hasattr(self, 'original_df'):
                self.original_df = self.df.copy()

            # Filtrage
            if selected_column == "Toutes les colonnes":
                filtered_df = [
                    item for item in self.original_df
                    if any(search_text in str(item.get(col, "")).lower()
                           for col in columns)
                ]
            else:
                if selected_column not in columns:
                    self.show_popup("Erreur", "Colonne invalide sélectionnée")
                    return

                filtered_df = [
                    item for item in self.original_df
                    if search_text in str(item.get(selected_column, "")).lower()
                ]

            print(f"{len(filtered_df)} résultats trouvés")

            self.df = filtered_df
            self.calcul_qte_total(self.df)
            self.populate_table()

            # Feedback visuel
            self.status_label.setText(
                f"{len(self.df)} résultat(s) trouvé(s) "
                f"(sur {len(self.original_df)})"
            )
            self.status_label.setStyleSheet("color: green;")

        except Exception as e:
            print(f"Erreur recherche: {str(e)}")
            self.show_popup("Erreur", f"Échec de la recherche: {str(e)}")
            self.df = self.original_df
            self.populate_table()