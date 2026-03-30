from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QScrollArea, QGridLayout, QComboBox, QMessageBox, QCalendarWidget, QDialog)
from PyQt5.QtGui import QFont, QFontDatabase, QColor
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from frontend.Client import make_request

import logging

class SelectableRowWidget(QWidget):
    def __init__(self, row_data, col_widths, on_selection_change=None):
        super().__init__()
        self.row_data = row_data
        self.col_widths = col_widths
        self.on_selection_change = on_selection_change
        self.selected = False
        self.setAttribute(Qt.WA_StyledBackground)  # Important pour le style CSS
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.setFixedHeight(40)
        self.setMinimumWidth(sum(self.col_widths))

        # Style de base
        self.setStyleSheet("""
            SelectableRowWidget {
                background-color: white;
                border-bottom: 1px solid #ddd;
            }
            SelectableRowWidget:hover {
                background-color: #f0f0f0;
            }
        """)

        for i, (val, width) in enumerate(zip(self.row_data, self.col_widths)):
            label = QLabel(str(val))
            label.setFont(QFont("Arial", 9))
            label.setFixedWidth(width)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("padding: 2px; border-right: 1px solid #ddd;")
            layout.addWidget(label)

    def mousePressEvent(self, event):
        if not self.selected:
            self.selected = True
            self.setStyleSheet("background-color: rgba(153, 204, 255, 255);")
            if self.on_selection_change:
                self.on_selection_change(self)
        event.accept()

    def is_selected(self):
        return self.selected

    def deselect(self):
        self.selected = False
        self.setStyleSheet("background-color: white;")

class CalendarDialog(QDialog):
    def __init__(self, on_date_select, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Date")
        self.setFixedSize(300, 300)
        self.on_date_select = on_date_select
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.calendar = QCalendarWidget()
        self.calendar.setFont(QFont("Arial", 10))
        self.calendar.clicked.connect(self.on_date_clicked)
        layout.addWidget(self.calendar)
        btn = QPushButton("OK")
        btn.setFont(QFont("Arial", 10))
        btn.setFixedHeight(40)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
        self.setLayout(layout)

    def on_date_clicked(self, date):
        self.selected_date = date.toString("yyyy-MM-dd")

    def accept(self):
        if hasattr(self, 'selected_date'):
            self.on_date_select(self.selected_date)
        super().accept()

class OfsEnCoursWindow(QWidget):
    switch_screen = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.show_table = True
        self.show_modification_section = False
        self.of_chaines = []
        self.df = []
        self.original_df = []
        self.selected_rows = []
        self.models = [
            "Choisir un modèle", "DCDP500 STRETCH BISQUE", "DCDP500 STRETCH NOIR",
            "DCDP900 LEATHER half-point BEI", "GAS 580Leather Slippers WHT",
            "GRPD 500F half-point BEI", "Half Point Leather Free Chrome", "MDW WITHOUT CHROME"
        ]
        self.maxnumOfs = ""
        self.search_text = ""
        self.numOFselectionne = ""
        self.filter_inputs = {}
        self.modeleforFiltered = "DCDP500 STRETCH BISQUE"
        self.rows = []
        try:
            self.init_ui()
            self.on_enter()
        except Exception as e:
            logging.error(f"Failed to initialize OfsEnCoursWindow: {str(e)}")
            self.show_popup("Erreur", f"Erreur lors de l'initialisation de l'écran: {str(e)}")

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setStyleSheet("background-color: rgba(242, 242, 242, 255);")

        font_db = QFontDatabase()
        font_id = font_db.addApplicationFont(r"D:\seguiemj.ttf")
        self.emoji_font = QFont(font_db.applicationFontFamilies(font_id)[0], 12) if font_id != -1 else QFont("Arial", 12)

        topbar = QWidget()
        topbar.setFixedHeight(50)
        topbar.setStyleSheet("background-color: rgba(51, 128, 204, 255);")
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(10, 0, 10, 0)
        topbar_label = QLabel("📊 OFs En Cours")
        topbar_label.setFont(QFont(self.emoji_font.family(), 14, QFont.Bold))
        topbar_label.setStyleSheet("color: white;")
        topbar_layout.addWidget(topbar_label)
        main_layout.addWidget(topbar)

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

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_layout.addWidget(scroll)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(15, 15, 15, 15)
        scroll_layout.setSpacing(15)
        scroll.setWidget(scroll_content)

        self.model_id = QComboBox()
        self.model_id.addItems(self.models)
        self.model_id.setCurrentText("DCDP500 STRETCH BISQUE")
        self.model_id.setFont(self.emoji_font)
        self.model_id.setFixedSize(300, 40)
        self.model_id.setStyleSheet("background-color: white; color: black; border: 1.2px solid #CCCCCC;")
        self.model_id.currentTextChanged.connect(self.spinner_selected)
        self.model_id.setVisible(self.show_table)
        scroll_layout.addWidget(self.model_id)

        reset_btn = QPushButton("🔄 Réinitialiser")
        reset_btn.setFont(self.emoji_font)
        reset_btn.setFixedSize(150, 40)
        reset_btn.setStyleSheet("background-color: rgba(204, 26, 26, 255); color: white;")
        reset_btn.clicked.connect(self.reinitialiser_formulaire)
        scroll_layout.addWidget(reset_btn)

        self.box_table_container = QWidget()
        self.box_table_container.setVisible(self.show_table)
        table_layout = QVBoxLayout(self.box_table_container)

        # Par cette version améliorée
        self.table_container = QWidget()
        table_main_layout = QVBoxLayout(self.table_container)
        table_main_layout.setContentsMargins(0, 0, 0, 0)
        table_main_layout.setSpacing(0)

        # Header
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(40)
        self.header_grid = QHBoxLayout(self.header_widget)
        self.header_grid.setContentsMargins(0, 0, 0, 0)
        self.header_grid.setSpacing(0)
        table_main_layout.addWidget(self.header_widget)

        # Table body with vertical scroll only
        self.table_body = QScrollArea()
        self.table_body.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_body.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.table_body.setWidgetResizable(True)

        self.table_content = QWidget()
        self.table_grid = QVBoxLayout(self.table_content)
        self.table_grid.setContentsMargins(0, 0, 0, 0)
        self.table_grid.setSpacing(0)
        self.table_body.setWidget(self.table_content)
        table_main_layout.addWidget(self.table_body)

        table_layout.addWidget(self.table_container)

        mod_btn = QPushButton("Modifier")
        mod_btn.setFont(QFont("Arial", 10))
        mod_btn.setFixedSize(120, 40)
        mod_btn.setStyleSheet("background-color: rgba(51, 153, 230, 255); color: white;")
        mod_btn.clicked.connect(self.afficherTextFields)
        table_layout.addWidget(mod_btn)
        scroll_layout.addWidget(self.box_table_container)

        self.edit_section = QWidget()
        self.edit_section.setFixedHeight(600)
        self.edit_section.setVisible(self.show_modification_section)
        self.edit_section.setStyleSheet("background-color: rgba(242, 242, 242, 255);")
        edit_layout = QVBoxLayout(self.edit_section)
        edit_layout.setContentsMargins(10, 10, 10, 10)
        edit_layout.setSpacing(10)

        edit_label = QLabel("✏️ Modifier les détails de l'OF sélectionné")
        edit_label.setFont(QFont(self.emoji_font.family(), 14))
        edit_label.setStyleSheet("color: rgba(26, 77, 128, 255);")
        edit_label.setFixedHeight(30)
        edit_layout.addWidget(edit_label)

        edit_grid = QGridLayout()
        edit_grid.setVerticalSpacing(8)
        edit_grid.setHorizontalSpacing(8)
        edit_grid.setColumnMinimumWidth(1, 200)

        fields = [
            ("Numéro OF :", "numOF_input", True),
            ("Inventaire :", "inventaire_input", False),
            ("Export :", "export_input", False),
            ("Magasin :", "magasin_input", False),
            ("Nbre :", "nbre_input", False),
            ("DF :", "df_input", False),
            ("Observation :", "observation_input", False)
        ]
        for row, (label_text, input_id, disabled) in enumerate(fields):
            label = QLabel(label_text)
            label.setStyleSheet("color: rgba(26, 77, 128, 255);")
            edit_grid.addWidget(label, row, 0)
            if input_id == "df_input":
                df_layout = QHBoxLayout()
                input_field = QLineEdit()
                input_field.setObjectName(input_id)
                input_field.setFixedWidth(150)
                df_layout.addWidget(input_field)
                calendar_btn = QPushButton("🗓")
                calendar_btn.setFont(self.emoji_font)
                calendar_btn.setFixedSize(40, 40)
                calendar_btn.setStyleSheet("background-color: transparent;")
                calendar_btn.clicked.connect(self.open_calendar)
                df_layout.addWidget(calendar_btn)
                edit_grid.addLayout(df_layout, row, 1)
            else:
                input_field = QLineEdit()
                input_field.setObjectName(input_id)
                input_field.setEnabled(not disabled)
                edit_grid.addWidget(input_field, row, 1)
            setattr(self, input_id, input_field)
        edit_layout.addLayout(edit_grid)

        validate_btn = QPushButton("✅ Valider les modifications")
        validate_btn.setFont(self.emoji_font)
        validate_btn.setFixedSize(200, 45)
        validate_btn.setStyleSheet("background-color: rgba(51, 153, 51, 255); color: white;")
        validate_btn.clicked.connect(self.valider_modifications)
        edit_layout.addWidget(validate_btn, alignment=Qt.AlignCenter)
        scroll_layout.addWidget(self.edit_section)
        scroll_layout.addStretch()

    def get_maximum_date_of_ofs(self):
        try:
            response = make_request("get", "/manage_ofs/get_maximum_date_of_ofs")
            if response.status_code == 200:
                self.maxnumOfs = response.json()[0].get("maxNumberOfOfs", "")
                print(f"Max number of OFs: {self.maxnumOfs}")
            else:
                print(f"Error getting max date: {response.status_code}")
                self.show_popup("Erreur", f"Erreur lors du chargement de la date maximale: {response.status_code}")
        except Exception as e:
            print(f"Error in get_maximum_date_of_ofs: {e}")
            self.show_popup("Erreur", f"Erreur lors du chargement de la date maximale: {str(e)}")

    def loadofs(self, modele):
        try:
            self.df = []
            self.original_df = []
            if modele == "Choisir un modèle":
                self.show_popup("Attention", "Veuillez sélectionner un modèle valide")
                return
            data = {"modele": modele}
            response = make_request("get", "/manage_ofs/get_all_ofs_by_modele", json=data)
            if response.status_code == 200:
                self.original_df = response.json()[0].get("ofsbyModeles", [])
                self.df = self.original_df.copy()
                print("Loaded OFs:", self.df)
                self.populate_table()
            else:
                print(f"Error loading OFs: {response.status_code}")
                self.show_popup("Erreur", f"Erreur lors du chargement des OFs: {response.status_code}")
        except Exception as e:
            print(f"Error in loadofs: {e}")
            self.show_popup("Erreur", f"Erreur lors du chargement des OFs: {str(e)}")

    def populate_table(self):
        try:
            # Clear existing widgets
            for i in reversed(range(self.header_grid.count())):
                self.header_grid.itemAt(i).widget().setParent(None)
            for i in reversed(range(self.table_grid.count())):
                self.table_grid.itemAt(i).widget().setParent(None)

            columns = ["inventaire", "atelierPiqure", "Modele", "Coloris", "DF", "numOF", "dateCreation",
                       "Quantite", "Pointure", "entre_Coupe", "sortie_Coupe", "entre_Piqure", "sortie_Piqure",
                       "entre_Montage", "sortie_Montage", "export", "magasin", "nbre", "colisNonEmb", "observation"]

            # Calculate dynamic column widths based on content
            self.col_widths = self.calculate_column_widths(columns)
            total_width = sum(self.col_widths.values())

            # Configure header
            self.header_widget.setFixedWidth(total_width)
            self.filter_inputs = {}

            for col in columns:
                col_widget = QWidget()
                col_widget.setFixedWidth(self.col_widths[col])
                col_layout = QVBoxLayout(col_widget)
                col_layout.setContentsMargins(0, 0, 0, 0)
                col_layout.setSpacing(0)

                # Header label
                header = QLabel(str(col))
                header.setFont(QFont(self.emoji_font.family(), 9, QFont.Bold))
                header.setFixedHeight(20)
                header.setAlignment(Qt.AlignCenter)
                header.setStyleSheet("color: black; border-bottom: 1px solid #ccc;")
                col_layout.addWidget(header)

                # Filter input
                filter_input = QLineEdit()
                filter_input.setPlaceholderText(f"Filtrer {col}")
                filter_input.setFont(QFont("Arial", 8))
                filter_input.setFixedHeight(20)
                filter_input.textChanged.connect(self.on_filter_change)
                col_layout.addWidget(filter_input)
                self.header_grid.addWidget(col_widget)
                self.filter_inputs[col] = filter_input
            self.update_table_rows()
        except Exception as e:
            print(f"Error in populate_table: {e}")
            self.show_popup("Erreur", f"Erreur lors du remplissage de la table: {str(e)}")

    def calculate_column_widths(self, columns):
        """Calculate appropriate column widths based on content"""
        # Largeurs spécifiques pour chaque colonne
        base_widths = {
            "inventaire": 150,
            "atelierPiqure": 150,
            "Modele": 250,
            "Coloris": 250,
            "DF": 100,
            "numOF": 100,
            "dateCreation": 100,
            "Quantite": 70,
            "Pointure": 70,
            "entre_Coupe": 120,
            "sortie_Coupe": 120,
            "entre_Piqure": 120,
            "sortie_Piqure": 120,
            "entre_Montage": 120,
            "sortie_Montage": 120,
            "export": 100,
            "magasin": 120,
            "nbre": 70,
            "colisNonEmb": 100,
            "observation": 200
        }

        # Largeur par défaut pour les colonnes non spécifiées
        default_width = 120

        # Retourne un dictionnaire avec la largeur pour chaque colonne dans la liste `columns`
        return {col: base_widths.get(col, default_width) for col in columns}

    def on_filter_change(self):
        try:
            filtered_data = self.original_df.copy()
            for col, input_widget in self.filter_inputs.items():
                filter_text = input_widget.text().lower()
                if filter_text:
                    filtered_data = [row for row in filtered_data if filter_text in str(row.get(col, "")).lower()]
            self.df = filtered_data
            self.update_table_rows()
        except Exception as e:
            print(f"Error in on_filter_change: {e}")
            self.show_popup("Erreur", f"Erreur lors du filtrage: {str(e)}")

    def update_table_rows(self):
        try:
            # Clear existing rows
            for i in reversed(range(self.table_grid.count())):
                self.table_grid.itemAt(i).widget().setParent(None)

            columns = list(self.filter_inputs.keys())
            self.rows = []

            # Configure table content size
            row_height = 40
            visible_rows = min(15, len(self.df))  # Show max 15 rows at once
            total_height = row_height * len(self.df)

            self.table_content.setFixedWidth(sum(self.col_widths.values()))
            self.table_content.setFixedHeight(total_height)

            for row_idx, row in enumerate(self.df):
                row_data = []
                for col in columns:
                    value = row.get(col, "")
                    if col == "dateCreation" and isinstance(value, str):
                        value = value.split("T")[0]
                    row_data.append(str(value))

                row_widget = SelectableRowWidget(row_data, list(self.col_widths.values()),
                                                 self.on_row_selection_changed)
                self.table_grid.addWidget(row_widget)
                self.rows.append(row_widget)

            # Adjust container height to show about 10-15 rows without scrolling
            visible_height = row_height * visible_rows
            self.table_container.setFixedHeight(40 + visible_height)  # 40 for header
        except Exception as e:
            print(f"Error in update_table_rows: {e}")
            self.show_popup("Erreur", f"Erreur lors de la mise à jour des lignes: {str(e)}")

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

    def on_enter(self):
        try:
            self.show_table = True
            self.numOFselectionne = ""
            self.show_modification_section = False
            self.numOF_input.setText("")
            self.inventaire_input.setText("")
            self.export_input.setText("")
            self.magasin_input.setText("")
            self.nbre_input.setText("")
            self.df_input.setText("")
            self.observation_input.setText("")
            self.get_maximum_date_of_ofs()
            self.loadofs(self.modeleforFiltered)
        except Exception as e:
            print(f"Error in on_enter: {e}")
            self.show_popup("Erreur", f"Erreur lors du chargement initial: {str(e)}")

    def afficherTextFields(self):
        try:
            if self.selected_rows:
                self.show_modification_section = True
                column_indices = {
                    "numOF": 5,
                    "inventaire": 0,
                    "export": 15,
                    "magasin": 16,
                    "nbre": 17,
                    "DF": 4,
                    "observation": 19
                }
                self.numOF_input.setText(self.selected_rows[column_indices["numOF"]])
                self.inventaire_input.setText(self.selected_rows[column_indices["inventaire"]])
                self.export_input.setText(self.selected_rows[column_indices["export"]])
                self.magasin_input.setText(self.selected_rows[column_indices["magasin"]])
                self.nbre_input.setText(self.selected_rows[column_indices["nbre"]])
                self.df_input.setText(self.selected_rows[column_indices["DF"]])
                self.observation_input.setText(self.selected_rows[column_indices["observation"]])
            else:
                self.show_popup("Attention", "Veuillez sélectionner une ligne")
            self.edit_section.setVisible(self.show_modification_section)
        except Exception as e:
            print(f"Error in afficherTextFields: {e}")
            self.show_popup("Erreur", f"Erreur lors de l'affichage des champs: {str(e)}")

    def open_calendar(self):
        try:
            def set_date(date_str):
                self.df_input.setText(date_str)
            dialog = CalendarDialog(set_date, self)
            dialog.exec_()
        except Exception as e:
            print(f"Error in open_calendar: {e}")
            self.show_popup("Erreur", f"Erreur lors de l'ouverture du calendrier: {str(e)}")

    def est_entier(self, valeur):
        try:
            int(valeur)
            return True
        except ValueError:
            return False

    def valider_modifications(self):
        try:
            nbre = self.nbre_input.text()
            if nbre and not self.est_entier(nbre):
                self.show_popup("Attention", "Écrire un nombre valide")
                return
            data = {
                "numof": self.numOFselectionne,
                "inventaire": self.inventaire_input.text(),
                "export": self.export_input.text(),
                "magasin": self.magasin_input.text(),
                "nbre": self.nbre_input.text(),
                "DF": self.df_input.text(),
                "observation": self.observation_input.text(),
            }
            response = make_request("put", "/manage_ofs/update_of", json=data)
            if response.status_code == 200:
                self.show_popup("Succès", "L'OF a été mise à jour")
                self.loadofs(self.modeleforFiltered)
                self.show_modification_section = False
                self.numOFselectionne = ""
                self.numOF_input.setText("")
                self.inventaire_input.setText("")
                self.export_input.setText("")
                self.magasin_input.setText("")
                self.nbre_input.setText("")
                self.df_input.setText("")
                self.observation_input.setText("")
            else:
                print(f"Error updating OF: {response.status_code}")
                self.show_popup("Attention", f"Vous n'êtes pas autorisé pour cette fonction: {response.status_code}")
        except Exception as e:
            print(f"Error in valider_modifications: {e}")
            self.show_popup("Erreur", f"Erreur lors de la validation des modifications: {str(e)}")

    def get_selected_rows(self):
        selected = []
        for i in range(self.table_grid.count()):
            widget = self.table_grid.itemAt(i).widget()
            if isinstance(widget, SelectableRowWidget) and widget.is_selected():
                selected = widget.row_data
                break
        return selected

    def on_row_selection_changed(self, selected_row):
        try:
            for row in self.rows:
                if row != selected_row:
                    row.deselect()
            self.selected_rows = self.get_selected_rows()
            print("Lignes sélectionnées:", self.selected_rows)
            if self.selected_rows:
                self.numOFselectionne = self.selected_rows[5]
                print("Selected numOF:", self.numOFselectionne)
        except Exception as e:
            print(f"Error in on_row_selection_changed: {e}")
            self.show_popup("Erreur", f"Erreur lors de la sélection de la ligne: {str(e)}")

    def spinner_selected(self, text):
        try:
            print("Model selected:", text)
            self.modeleforFiltered = text
            self.loadofs(text)
        except Exception as e:
            print(f"Error in spinner_selected: {e}")
            self.show_popup("Erreur", f"Erreur lors de la sélection du modèle: {str(e)}")

    def reinitialiser_formulaire(self):
        try:
            self.loadofs(self.modeleforFiltered or "DCDP500 STRETCH BISQUE")
            self.show_table = True
            self.numOFselectionne = ""
            self.numOF_input.setText("")
            self.show_modification_section = False
            self.inventaire_input.setText("")
            self.export_input.setText("")
            self.magasin_input.setText("")
            self.nbre_input.setText("")
            self.df_input.setText("")
            self.observation_input.setText("")
            self.edit_section.setVisible(False)
            for row in self.rows:
                row.deselect()
            self.selected_rows = []
        except Exception as e:
            print(f"Error in reinitialiser_formulaire: {e}")
            self.show_popup("Erreur", f"Erreur lors de la réinitialisation: {str(e)}")

    def root_to_lancement(self):
        self.switch_screen.emit("launch_screen")

    def root_to_update_launch(self):
        self.switch_screen.emit("update_launch_screen")

    def root_to_dashboardProduction(self):
        self.switch_screen.emit("dashboard_screen")

    def root_to_ofs_encours(self):
        self.switch_screen.emit("ofs_en_cours_screen")

    def logout(self):
        self.switch_screen.emit("login_screen")