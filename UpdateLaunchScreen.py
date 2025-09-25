import traceback
from datetime import datetime
from typing import List, Dict, Any, Optional

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QScrollArea, QGridLayout, QComboBox,
                             QMessageBox, QCheckBox, QDialog, QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtGui import QFont, QDoubleValidator, QIntValidator
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from frontend.Client import make_request


class UpdateLaunchWindow(QWidget):
    """Fenêtre principale pour la modification des lancements."""
    switch_screen = pyqtSignal(str)

    # Configuration des colonnes
    COLUMNS = ['selection', 'numOF', 'Pointure', 'Quantite', 'Coloris',
               'Modele', 'SAIS', 'dateCreation', 'regimeHoraire', 'parcours']
    COL_WIDTHS = [80, 100, 100, 100, 180, 180, 180, 180, 180, 180]
    ROW_HEIGHT = 80

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modification du Lancement")
        self.setMinimumSize(1000, 700)
        self.init_data()
        self.init_ui()
        self.load_initial_data()

    def init_data(self):
        """Initialise les variables de données."""
        self.show_checkboxes = False
        self.of_chaines = []
        self.df = []
        self.selected_rows = []
        self.checks = []
        self.modeles = []
        self.selected_rows_indices = []
        self.is_selecting_all = False
        self.search_text = ""
        self.row_widgets = []
        self.old_chaines = []

    def init_ui(self):
        """Initialise l'interface utilisateur."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Barre supérieure
        self.create_top_bar(main_layout)

        # Contenu principal
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(content)

        # Barre latérale
        self.create_sidebar(content_layout)

        # Zone de défilement principale
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_layout.addWidget(scroll)

        scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setContentsMargins(15, 15, 15, 15)
        self.scroll_layout.setSpacing(15)
        scroll.setWidget(scroll_content)

        # Formulaire de recherche
        self.create_search_form()

        # Tableau des OF
        self.create_of_table()

        # Sélection des chaînes (masqué par défaut)
        self.create_chain_selection()

        # Bouton Refresh (doit être visible)
        self.refresh_btn = QPushButton("Actualiser")
        self.refresh_btn.setFixedSize(200, 40)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.refresh_btn.clicked.connect(self.refresh_data_after_save)  # ⚠️ Pas de parenthèses !
        self.refresh_btn.setVisible(True)  # S'assurer qu'il est visible

        # Bouton Enregistrer
        self.save_btn = QPushButton("Enregistrer les modifications")
        self.save_btn.setFixedSize(200, 40)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.save_btn.clicked.connect(self.save_ofs_typechaine)
        self.save_btn.setVisible(False)

        # Ajout des boutons au layout
        self.scroll_layout.addWidget(self.refresh_btn, alignment=Qt.AlignCenter)
        self.scroll_layout.addWidget(self.save_btn, alignment=Qt.AlignCenter)

        # Espace en bas
        self.scroll_layout.addStretch()

    def create_top_bar(self, layout):
        """Crée la barre supérieure."""
        topbar = QWidget()
        topbar.setFixedHeight(50)
        topbar.setStyleSheet("background-color: #2196F3;")

        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel("Modification du Lancement")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: white;")
        topbar_layout.addWidget(title)

        layout.addWidget(topbar)

    def create_sidebar(self, layout):
        """Crée la barre latérale de navigation."""
        sidebar = QWidget()
        sidebar.setFixedWidth(150)
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
        layout.addWidget(sidebar)

    def create_search_form(self):
        """Crée le formulaire de recherche."""
        form = QWidget()
        form.setFixedHeight(120)

        form_layout = QHBoxLayout(form)
        form_layout.setSpacing(20)

        # Année
        self.year_combo = QComboBox()
        self.year_combo.setFixedWidth(150)
        form_layout.addWidget(QLabel("Année:"))
        form_layout.addWidget(self.year_combo)

        # Semaine
        self.week_combo = QComboBox()
        self.week_combo.setFixedWidth(120)
        form_layout.addWidget(QLabel("Semaine:"))
        form_layout.addWidget(self.week_combo)

        # Modèle
        self.model_combo = QComboBox()
        self.model_combo.setFixedWidth(200)
        form_layout.addWidget(QLabel("Modèle:"))
        form_layout.addWidget(self.model_combo)
        form.setStyleSheet("""
            QLabel { font-size: 18px; }
            QComboBox { font-size: 18px; }
            QPushButton { font-size: 18px; }
        """)

        # Boutons
        search_btn = QPushButton("Rechercher")
        search_btn.setFixedWidth(150)
        search_btn.setStyleSheet("background-color: #2196F3; color: white;")
        search_btn.clicked.connect(self.search)
        form_layout.addWidget(search_btn)

        reset_btn = QPushButton("Réinitialiser")
        reset_btn.setFixedWidth(150)
        reset_btn.setStyleSheet("background-color: #f44336; color: white;")
        reset_btn.clicked.connect(self.reset_filter)
        form_layout.addWidget(reset_btn)

        self.scroll_layout.addWidget(form)

    def create_of_table(self):
        """Crée un tableau dynamique des OF avec colonnes redimensionnables et triables."""
        container = QWidget()
        container.setStyleSheet("background-color: white; border: 1px solid #ddd; border-radius: 5px;")

        table_layout = QVBoxLayout(container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)

        # Création du tableau
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setStyleSheet("""
            QTableWidget {
                border: none;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 5px;
                color: #333;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
            }
        """)

        # Configuration des en-têtes
        header = self.table.horizontalHeader()
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #f5f5f5;
                color: #333;
                padding: 8px;
                border: 1px solid #ddd;
                font: bold 10pt Arial;
            }
        """)
        for i, width in enumerate(self.COL_WIDTHS):
            self.table.setColumnWidth(i, width)
        header.setSectionsMovable(False)
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        header.sectionClicked.connect(self.sort_table)

        # Configuration des lignes
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)

        # Sélection multiple
        select_layout = QHBoxLayout()
        select_layout.setContentsMargins(10, 10, 10, 10)

        self.select_all_cb = QCheckBox("Tout sélectionner")
        self.select_all_cb.stateChanged.connect(self.select_all_rows)
        select_layout.addWidget(self.select_all_cb)

        validate_btn = QPushButton("Valider la sélection")
        validate_btn.setStyleSheet("background-color: #2196F3; color: white; border-radius: 3px; padding: 5px;")
        validate_btn.clicked.connect(self.valider_selection)
        select_layout.addWidget(validate_btn)

        table_layout.addWidget(self.table)
        table_layout.addLayout(select_layout)
        self.scroll_layout.addWidget(container)

    def populate_table(self):
        """Remplit le tableau avec les données."""
        self.table.setRowCount(0)
        self.row_widgets = []
        self.selected_rows_indices = []

        self.table.setRowCount(len(self.df))
        for row_idx, row_data in enumerate(self.df):
            # Checkbox pour la sélection
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(lambda state, idx=row_idx: self.on_checkbox_active(idx, state == Qt.Checked))
            checkbox_layout.addWidget(checkbox)
            self.table.setCellWidget(row_idx, 0, checkbox_widget)

            # Données de la ligne
            for col_idx, col in enumerate(self.COLUMNS[1:], 1):
                value = str(row_data.get(col, ""))
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                item.setFont(QFont("Arial", 10))
                self.table.setItem(row_idx, col_idx, item)

            # Hauteur de ligne
            self.table.setRowHeight(row_idx, 50)

            # Ajout à row_widgets pour compatibilité avec le reste du code
            self.row_widgets.append(checkbox)

        # Ajuster automatiquement la hauteur des lignes
        self.table.resizeRowsToContents()

    def on_checkbox_active(self, row_index, is_checked):
        """Gère la sélection/désélection d'une ligne."""
        if self.is_selecting_all:
            return

        if is_checked and row_index not in self.selected_rows_indices:
            self.selected_rows_indices.append(row_index)
        elif not is_checked and row_index in self.selected_rows_indices:
            self.selected_rows_indices.remove(row_index)

        self.selected_rows = self.get_selected_rows()

    def sort_table(self, column):
        """Trie le tableau par la colonne cliquée."""
        if column == 0:  # Ignorer la colonne de sélection
            return
        order = Qt.AscendingOrder if self.table.isSortingEnabled() else Qt.DescendingOrder
        self.table.sortItems(column, order)
        self.table.setSortingEnabled(True)

        # Reconnect checkbox signals with new row positions
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.layout().itemAt(0).widget()
                try:
                    checkbox.stateChanged.disconnect()
                except TypeError:
                    pass
                checkbox.stateChanged.connect(lambda state, r=row: self.on_checkbox_active(r, state == Qt.Checked))

        # Update selected indices based on current checked states
        sorted_indices = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0).layout().itemAt(0).widget()
            if checkbox.isChecked():
                sorted_indices.append(row)
        self.selected_rows_indices = sorted_indices
        self.selected_rows = self.get_selected_rows()

    def get_selected_rows(self):
        selected = []
        for idx in self.selected_rows_indices:
            row_data = {}
            for col_idx, col in enumerate(self.COLUMNS[1:], 1):
                item = self.table.item(idx, col_idx)
                if item:
                    row_data[col] = item.text()
            selected.append(row_data)
        return selected

    def create_chain_selection(self):
        """Crée la section de sélection des chaînes."""
        self.chain_widget = QWidget()
        self.chain_widget.setVisible(False)

        chain_layout = QVBoxLayout(self.chain_widget)
        chain_layout.setContentsMargins(20, 20, 20, 20)
        chain_layout.setSpacing(15)

        title = QLabel("Sélection des chaînes de production")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        chain_layout.addWidget(title)

        self.chain_grid = QGridLayout()
        self.chain_grid.setSpacing(15)
        self.chain_grid.setContentsMargins(20, 20, 20, 20)

        chain_container = QWidget()
        chain_container.setStyleSheet("background-color: white; border: 1px solid #ddd;")
        chain_container.setLayout(self.chain_grid)
        chain_layout.addWidget(chain_container)

        self.scroll_layout.addWidget(self.chain_widget)

    def load_initial_data(self):
        """Charge les données initiales."""
        current_year = datetime.now().year
        current_week = datetime.today().isocalendar().week

        # Remplir les combobox
        self.year_combo.addItems([str(y) for y in range(current_year - 1, current_year + 2)])
        self.week_combo.addItems([f"{w:02d}" for w in range(1, 53)])

        self.year_combo.setCurrentText(str(current_year))
        self.week_combo.setCurrentText(f"{current_week:02d}")

        # Charger les modèles
        self.load_models()

    def load_models(self):
        """Charge la liste des modèles disponibles."""
        try:
            response = make_request("GET", "/manage_chaine_roles/get_all_models")
            if response.status_code == 200:
                self.modeles = [m["nom_modele"] for m in response.json()[0].get("modeles", [])]
                self.model_combo.clear()
                self.model_combo.addItems(self.modeles)
            else:
                self.show_error("Erreur", f"Erreur serveur: {response.status_code}")
        except Exception as e:
            self.show_error("Erreur", f"Impossible de charger les modèles: {str(e)}")

    def search(self):
        """Lance une recherche avec les critères sélectionnés."""
        try:
            self.show_checkboxes = False
            self.checks = []
            self.select_all_cb.setChecked(False)

            year = self.year_combo.currentText()
            week = self.week_combo.currentText()
            modele = self.model_combo.currentText()

            if not year or not week or not modele:
                self.show_error("Attention", "Veuillez sélectionner une année, une semaine et un modèle")
                return

            last_digit_year = year[-1]
            self.search_text = int(f"{last_digit_year}{week}")

            data = {
                "numof": self.search_text,
                "annee": year,
                "modele": modele,
            }

            self.load_ofs(data)

        except Exception as e:
            self.show_error("Erreur", f"Erreur lors de la recherche: {str(e)}")

    def load_ofs(self, data):
        """Charge les OF depuis l'API et met à jour le tableau."""
        try:
            response = make_request("GET", "/manage_ofs/getofsChaines", json=data)
            if response.status_code == 200:
                self.df = response.json()[0].get("ofs", [])

                # Sauvegarder l'état de tri actuel
                sort_column = self.table.horizontalHeader().sortIndicatorSection()
                sort_order = self.table.horizontalHeader().sortIndicatorOrder()

                self.populate_table()

                # Restaurer le tri
                if sort_column >= 0:
                    self.table.sortItems(sort_column, sort_order)

            else:
                self.show_error("Erreur", f"Erreur serveur: {response.status_code}")
        except Exception as e:
            self.show_error("Erreur", f"Erreur lors du chargement: {str(e)}")

    def select_all_rows(self, state):
        """Sélectionne ou désélectionne toutes les lignes."""
        self.is_selecting_all = True
        self.selected_rows_indices.clear()

        for idx in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(idx, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.layout().itemAt(0).widget()
                checkbox.setChecked(state == Qt.Checked)
            if state == Qt.Checked:
                self.selected_rows_indices.append(idx)

        self.selected_rows = self.get_selected_rows()
        self.is_selecting_all = False

    def valider_selection(self):
        """Valide la sélection des OF pour modification."""
        self.selected_rows = self.get_selected_rows()
        if not self.selected_rows:
            self.show_error("Attention", "Veuillez sélectionner au moins un OF")
            return

        try:
            numcmd = self.selected_rows[0]["numOF"]
            data = {"numcmd": numcmd}

            response = make_request("GET", "/manage_planification_chaine_modele/get_planifications_par_numcmd",
                                    json=data)
            if response.status_code == 200:
                self.show_checkboxes = True
                self.checks = response.json()[0].get("plan", [])
                self.chain_widget.setVisible(True)
                self.save_btn.setVisible(True)
                self.display_chain_selection()
            else:
                self.show_error("Erreur", f"Erreur lors du chargement des planifications: {response.status_code}")

        except Exception as e:
            self.show_error("Erreur", f"Erreur lors de la validation: {str(e)}")

    def display_chain_selection(self):
        """Affiche les options de sélection des chaînes."""
        # Nettoyer la grille existante
        for i in reversed(range(self.chain_grid.count())):
            widget = self.chain_grid.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Charger les rôles disponibles
        roles = self.load_chain_roles()

        # Ajouter les options
        for row, role in enumerate(roles):
            container = QWidget()
            layout = QHBoxLayout(container)

            # Checkbox
            cb = QCheckBox(role)
            cb.setFont(QFont("Arial", 10))

            # Vérifier si cette chaîne est déjà sélectionnée
            for item in self.checks:
                if item["chaine"] == role:
                    cb.setChecked(True)
                    break

            cb.stateChanged.connect(lambda state, r=role: self.on_chain_check(state, r))
            layout.addWidget(cb)

            # Bouton "œil" pour voir les détails
            eye_btn = QPushButton("👁")
            eye_btn.setFont(QFont("Arial", 10))
            eye_btn.setFixedSize(25, 25)
            eye_btn.setStyleSheet("background-color: transparent; border: none;")
            eye_btn.clicked.connect(lambda _, r=role: self.show_chain_details(r))
            layout.addWidget(eye_btn)

            self.chain_grid.addWidget(container, row // 2, row % 2)

    def load_chain_roles(self):
        """Charge les rôles de chaîne disponibles."""
        try:
            response = make_request("GET", "/manage_chaine_roles/getAllRoles")
            if response.status_code == 200:
                return [role["id"] for role in response.json()[0].get("roles", [])]
            else:
                self.show_error("Erreur", f"Erreur serveur: {response.status_code}")
                return []
        except Exception as e:
            self.show_error("Erreur", f"Erreur lors du chargement des rôles: {str(e)}")
            return []

    def on_chain_check(self, state, chaine):
        """Gère la sélection d'une chaîne."""
        if state == Qt.Checked:
            # Vérifier si cette chaîne est déjà dans les checks
            for item in self.checks:
                if item["chaine"] == chaine:
                    return

            # Si ce n'est pas le cas, ouvrir le dialogue de configuration
            if self.selected_rows:
                first_row = self.selected_rows[0]
                self.show_chain_config(
                    chaine,
                    first_row["regimeHoraire"],
                    first_row["Modele"]
                )
        else:
            # Retirer de la liste des checks
            self.checks = [item for item in self.checks if item["chaine"] != chaine]

    def show_chain_details(self, chaine):
        """Affiche les détails de configuration d'une chaîne."""
        for item in self.checks:
            if item["chaine"] == chaine:
                first_row = self.selected_rows[0] if self.selected_rows else {}
                regime = item.get("regimeHoraire", first_row.get("regimeHoraire", ""))
                modele = item.get("Modele", first_row.get("Modele", ""))
                self.show_chain_config(
                    chaine,
                    regime,
                    modele,
                    item
                )
                return

        if self.selected_rows:
            first_row = self.selected_rows[0]
            self.show_chain_config(
                chaine,
                first_row["regimeHoraire"],
                first_row["Modele"]
            )

    def show_chain_config(self, chaine, regime, modele, plan=None):
        """Affiche le dialogue de configuration de chaîne."""
        if plan is None:
            plan = self.get_global_plan(chaine, regime, modele)

        dialog = RegimeDialog(
            chaine,
            f"Configuration {chaine}",
            regime,
            modele,
            plan,
            self.save_chain_config
        )
        dialog.exec_()

    def get_global_plan(self, chaine, regime, modele):
        """Récupère le plan global pour une chaîne."""
        try:
            data = {
                "modele": modele,
                "chaine": chaine,
                "regime": regime
            }
            response = make_request("GET", "/manage_chaine_roles/getPlanBymodelChaineAndRegime", json=data)
            if response.status_code == 200:
                return response.json()[0].get("plan", {})
            else:
                self.show_error("Erreur", f"Erreur serveur: {response.status_code}")
                return {}
        except Exception as e:
            self.show_error("Erreur", f"Erreur lors du chargement du plan: {str(e)}")
            return {}

    def save_chain_config(self, data):
        """Enregistre la configuration d'une chaîne."""
        # Mettre à jour ou ajouter la configuration
        data["chaine"] = data.get("chaine", "")  # Ajout de la chaîne si absente
        self.checks = [item for item in self.checks if item["chaine"] != data["chaine"]]
        self.checks.append(data)

        # Rafraîchir l'affichage
        self.display_chain_selection()

    def save_ofs_typechaine(self):
        try:
            # Vérifications initiales
            if (not self.selected_rows or len(self.selected_rows) == 0) and (not hasattr(self, 'df') or not self.df):
                self.show_error("Attention", "Aucun OF sélectionné")
                return

            if not self.checks or len(self.checks) == 0:
                self.show_error("Attention", "Veuillez sélectionner au moins une chaîne")
                return

            # Détermination des OF à mettre à jour
            ofs_to_update = self.selected_rows if self.selected_rows else self.df

            # Extraction des chaînes existantes
            first_row = ofs_to_update[0]
            old_chaines = list(set(first_row.get("parcours", "").split(","))) if first_row.get("parcours") else []

            of_chaines_data = []
            plan_ids = []

            # Création ou mise à jour des planifications
            for item in self.checks:
                response = make_request(
                    "POST",
                    "/manage_planification_chaine_modele/addOrUpdatePlanification",
                    json=item,
                    timeout=10
                )

                if response is None:
                    self.show_error("Erreur", "La requête a échoué (aucune réponse du serveur)")
                    return

                if response.status_code not in (200, 201):
                    self.show_error("Erreur", f"Échec de la création du plan: {response.status_code}")
                    return

                try:
                    response_data = response.json()
                    if not response_data or not isinstance(response_data, list) or not response_data[0].get("id"):
                        self.show_error("Erreur", "Format de réponse invalide")
                        return
                except ValueError as e:
                    self.show_error("Erreur", f"Erreur de parsing JSON: {str(e)}")
                    return

                plan_data = response_data[0]
                plan_id = plan_data["id"]
                regime = plan_data.get("regimeHoraire", item.get("regimeHoraire", ""))
                plan_ids.append(plan_id)

                for of in ofs_to_update:
                    of_chaines_data.append({
                        "idchaine": item["chaine"],
                        "numCommandeOF": of["numOF"],
                        "idPlanification": plan_id,
                        "regimeHoraire": regime,
                    })

            # Mise à jour des OF avec les chaînes
            update_data = {
                "chaines": old_chaines,
                "ofs_chaines": of_chaines_data
            }

            response = make_request(
                "PUT",
                "/manage_ofs/update_of_chaine",
                json=update_data,
                timeout=15
            )

            if response is None:
                self.show_error("Erreur", "La requête de mise à jour a échoué (aucune réponse du serveur)")
                return

            if response.status_code == 500:
                # Try to get the error message from the response body
                error_msg = "Erreur interne du serveur"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", error_msg)
                except:
                    # If we can't parse JSON, try to get raw text
                    try:
                        error_msg = response.text[:200]  # Limit to first 200 chars
                    except:
                        pass
                self.show_error("Erreur serveur", f"Code: 500 - {error_msg}")
                return

            if response.status_code in (200, 201):
                QMessageBox.information(None, "Succès", "Modification effectuée avec succès")
                self.reset_after_save()
            else:
                self.show_error("Erreur", f"Échec de la mise à jour des OF: {response.status_code}")

        except Exception as e:
            self.show_error("Erreur", f"Erreur critique: {str(e)}")
            traceback.print_exc()

    def refresh_data_after_save(self):
        """Recharge toutes les données pour mettre à jour le tableau."""
        try:
            if hasattr(self, 'search_text') and self.search_text:
                data = {
                    "numof": self.search_text,
                    "annee": self.year_combo.currentText(),
                    "modele": self.model_combo.currentText(),
                }
                self.load_ofs(data)
            else:
                print("Aucun critère de recherche défini pour recharger les données.")
        except Exception as e:
            print(f"Erreur lors du rechargement des données: {str(e)}")
            self.show_error("Erreur", "Impossible de recharger les données")


    def prepare_of_chaines_data(self, ofs_to_update):
        """Prépare les données des OF à mettre à jour."""
        of_chaines = []

        for item in self.checks:
            # Enregistrer la planification
            response = make_request("POST", "/manage_planification_chaine_modele/addOrUpdatePlanification", json=item)

            if response.status_code == 201:
                plan_id = response.json()[0]["id"]
                regime = response.json()[0]["regimeHoraire"]

                # Ajouter chaque OF à cette chaîne
                for of in ofs_to_update:
                    of_chaines.append({
                        "idchaine": item["chaine"],
                        "numCommandeOF": of["numOF"],
                        "idPlanification": plan_id,
                        "regimeHoraire": regime,
                    })

        return of_chaines

    def reset_after_save(self):
        """Réinitialise l'interface après enregistrement."""
        self.show_checkboxes = False
        self.checks = []
        self.chain_widget.setVisible(False)
        self.save_btn.setVisible(False)
        self.select_all_cb.setChecked(False)

        # Recharger les données
        if hasattr(self, 'search_text') and self.search_text:
            data = {
                "numof": self.search_text,
                "annee": self.year_combo.currentText(),
                "modele": self.model_combo.currentText(),
            }
            self.load_ofs(data)

    def reset_filter(self):
        """Réinitialise les filtres de recherche."""
        self.year_combo.setCurrentIndex(0)
        self.week_combo.setCurrentIndex(0)
        self.model_combo.setCurrentIndex(0)
        self.search_text = ""
        self.df = []
        self.populate_table()

    def show_error(self, title, message):
        """Affiche une boîte de dialogue d'erreur."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information if title == "Succès" else QMessageBox.Critical)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec_()

    # Méthodes de navigation
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


class RegimeDialog(QDialog):
    """Dialogue pour la configuration du régime horaire."""

    def __init__(self, chaine: str, titre: str, regime: str, modele: str,
                 plan: Dict[str, str], on_save: callable, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Régime Horaire - {chaine}")
        self.setFixedSize(700, 700)
        self.on_save = on_save
        self.chaine = chaine  # Ajout pour garantir la disponibilité de la chaîne
        self.regime = regime
        self.modele = modele
        self.plan = plan if plan else {}
        self.init_ui(chaine, regime, modele, self.plan)

    def init_ui(self, chaine: str, regime: str, modele: str, plan: Dict[str, str]):
        layout = QVBoxLayout(self)
        layout.setSpacing(30)
        layout.setContentsMargins(40, 40, 40, 40)

        # Titre
        title = QLabel(f"Configuration pour {chaine} - {modele}")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # En-tête
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.addWidget(QLabel("Jour"), 1, Qt.AlignCenter)
        header_layout.addWidget(QLabel("Heures/jour"), 1, Qt.AlignCenter)
        header_layout.addWidget(QLabel("Paires/jour"), 1, Qt.AlignCenter)
        layout.addWidget(header)

        # Configuration des jours
        self.inputs = {}
        jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]

        float_validator = QDoubleValidator(0, 24, 1)
        int_validator = QIntValidator(0, 1000)

        for jour in jours:
            row = QWidget()
            row_layout = QHBoxLayout(row)

            # Label du jour
            day_label = QLabel(jour)
            day_label.setFixedWidth(100)
            row_layout.addWidget(day_label)

            # Champ heures
            heures = QLineEdit(str(plan.get(f"horaire{jour}", "7" if regime == "42h" else "8.5")))
            heures.setValidator(float_validator)
            heures.setFixedWidth(100)
            row_layout.addWidget(heures)

            # Champ paires
            paires = QLineEdit(str(plan.get(f"nbPaire{jour}", "")))
            paires.setValidator(int_validator)
            paires.setFixedWidth(100)
            row_layout.addWidget(paires)

            self.inputs[f"horaire{jour}"] = heures
            self.inputs[f"nbPaire{jour}"] = paires
            layout.addWidget(row)

        # Boutons
        buttons = QWidget()
        buttons_layout = QHBoxLayout(buttons)
        buttons_layout.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setFixedSize(100, 30)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Enregistrer")
        save_btn.setFixedSize(100, 30)
        save_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        save_btn.clicked.connect(self.on_save_clicked)
        buttons_layout.addWidget(save_btn)

        layout.addWidget(buttons)
        layout.addStretch()

    def on_save_clicked(self):
        """Collecte les données et les envoie au callback."""
        data = self.plan.copy()
        data["chaine"] = self.chaine
        for key, field in self.inputs.items():
            data[key] = field.text()
        if "modele" not in data:
            data["modele"] = self.modele
        if "regimeHoraire" not in data:
            data["regimeHoraire"] = self.regime
        self.on_save(data)
        self.accept()


class RowWidget(QWidget):
    """Widget personnalisé pour afficher une ligne de données."""

    def __init__(self, row_data: List[str], col_widths: List[int], row_index: int,
                 on_checkbox_changed: callable):
        super().__init__()
        self.row_data = row_data
        self.col_widths = col_widths
        self.row_index = row_index
        self.on_checkbox_changed = on_checkbox_changed
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(5)
        self.setFixedHeight(60)

        # Checkbox de sélection
        self.checkbox = QCheckBox()
        self.checkbox.setFixedWidth(self.col_widths[0])
        self.checkbox.stateChanged.connect(self.on_checkbox_state_changed)
        layout.addWidget(self.checkbox)

        # Données de la ligne
        for i, val in enumerate(self.row_data):
            label = QLabel(str(val))
            label.setFont(QFont("Arial", 10))
            label.setFixedWidth(self.col_widths[i])
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("""
                padding: 5px;
                border: 1px solid #ddd;
                background-color: white;
                border-radius: 3px;
            """)
            layout.addWidget(label)

        layout.addStretch()

    def on_checkbox_state_changed(self, state):
        self.on_checkbox_changed(self.row_index, state == Qt.Checked)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    window = UpdateLaunchWindow()
    window.show()
    sys.exit(app.exec_())