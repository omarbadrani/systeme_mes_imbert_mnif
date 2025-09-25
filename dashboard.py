import sys
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QPushButton, QScrollArea, QGridLayout,
                             QMessageBox, QFrame)
from PyQt5.QtGui import QFont, QFontDatabase, QColor
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView
from frontend.Client import make_request
from requests.exceptions import RequestException
from PyQt5.QtWebEngineWidgets import QWebEngineView

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
        self.setFixedWidth(sum(self.col_widths))
        self.update_style()

        for i, val in enumerate(self.row_data):
            label = QLabel(str(val))
            label.setFont(QFont("Arial", 10))
            label.setFixedWidth(self.col_widths[i])
            label.setFixedHeight(40)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("padding: 5px;")
            layout.addWidget(label)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        self.selected = not self.selected
        self.update_style()
        if self.on_selection_change:
            self.on_selection_change()
        event.accept()

    def update_style(self):
        self.setStyleSheet("background-color: rgba(153, 204, 255, 255);" if self.selected else "background-color: white;")

    def is_selected(self):
        return self.selected

class DashboardWindow(QWidget):
    switch_screen = pyqtSignal(str)  # Add signal for navigation

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tableau de bord")
        self.show_table = False
        self.show_statistics = False
        self.of_chaines = []
        self.df = []
        self.selected_rows = []
        self.models = []
        self.statistics = []
        self.ofsPerChaine = []
        self.search_text = ""
        self.maxnumOfs = None
        self.current_page = 1
        self.rows_per_page = 10
        self.table_columns = [
            {"key": "Modele", "label": "Modèle", "width": 300},
            {"key": "total_quantite", "label": "Quantité Totale", "width": 250},
            {"key": "Coloris", "label": "Coloris", "width": 250},
            {"key": "SAIS", "label": "SAIS", "width": 250},
            {"key": "dateCreation", "label": "Date Création", "width": 280, "format": lambda x: x.split("T")[0] if isinstance(x, str) and "T" in x else str(x)},
            {"key": "total_ofs", "label": "Total OFs", "width": 280}
        ]
        self.init_ui()
        self.on_enter()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setStyleSheet("background-color: #F5F5F5;")

        # Load emoji font with fallback
        font_db = QFontDatabase()
        font_id = font_db.addApplicationFont("seguiemj.ttf")  # Assume relative path or bundled resource
        self.emoji_font = QFont(font_db.applicationFontFamilies(font_id)[0], 12) if font_id != -1 else QFont("Arial", 12)

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
        search_form = QWidget()
        search_form.setFixedHeight(50)
        search_layout = QHBoxLayout(search_form)
        search_layout.setSpacing(10)

        self.year_id = QComboBox()
        self.year_id.setFixedHeight(40)
        self.year_id.setFixedWidth(150)
        self.year_id.addItem("Choisir l'année")
        self.year_id.setFont(self.emoji_font)
        self.year_id.setStyleSheet("background-color: white; border: 1.2px solid #CCCCCC; color: black;")
        self.year_id.currentTextChanged.connect(self.spinner_selected)
        search_layout.addWidget(self.year_id)

        self.week_id = QComboBox()
        self.week_id.setFixedHeight(40)
        self.week_id.setFixedWidth(150)
        self.week_id.addItem("Choisir le num de semaine")
        self.week_id.setFont(self.emoji_font)
        self.week_id.setStyleSheet("background-color: white; border: 1.2px solid #CCCCCC; color: black;")
        self.week_id.currentTextChanged.connect(self.spinner_selected)
        search_layout.addWidget(self.week_id)

        search_btn = QPushButton("🔎 Rechercher")
        search_btn.setFont(self.emoji_font)
        search_btn.setFixedSize(160, 40)
        search_btn.clicked.connect(self.search)
        search_layout.addWidget(search_btn)
        scroll_layout.addWidget(search_form)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setFont(self.emoji_font)
        self.status_label.setFixedHeight(30)
        scroll_layout.addWidget(self.status_label)

        # Pie chart container
        self.pie_chart_container = QWidget()
        self.pie_chart_container.setMinimumHeight(250)
        self.pie_chart_layout = QHBoxLayout(self.pie_chart_container)
        self.pie_chart_layout.setContentsMargins(10, 10, 10, 10)
        self.pie_chart_layout.setSpacing(20)
        self.pie_chart_container.setVisible(self.show_table)
        scroll_layout.addWidget(self.pie_chart_container)

        # Table container
        self.box_table_container = QWidget()
        self.box_table_container.setVisible(self.show_table)
        table_layout = QVBoxLayout(self.box_table_container)

        self.header_scroll = QScrollArea()
        self.header_scroll.setFixedHeight(40)
        self.header_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.header_grid = QGridLayout()
        header_widget = QWidget()
        header_widget.setLayout(self.header_grid)
        self.header_scroll.setWidget(header_widget)
        self.header_scroll.setWidgetResizable(True)
        table_layout.addWidget(self.header_scroll)

        self.table_scroll = QScrollArea()
        self.table_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.table_grid = QGridLayout()
        table_widget = QWidget()
        table_widget.setLayout(self.table_grid)
        self.table_scroll.setWidget(table_widget)
        self.table_scroll.setWidgetResizable(True)
        table_layout.addWidget(self.table_scroll)

        # Pagination
        self.pagination_widget = QWidget()
        pagination_layout = QHBoxLayout(self.pagination_widget)
        self.prev_button = QPushButton("◄ Précédent")
        self.prev_button.setFont(self.emoji_font)
        self.prev_button.clicked.connect(self.prev_page)
        pagination_layout.addWidget(self.prev_button)
        self.page_label = QLabel("Page 1")
        self.page_label.setFont(self.emoji_font)
        pagination_layout.addWidget(self.page_label)
        self.next_button = QPushButton("Suivant ►")
        self.next_button.setFont(self.emoji_font)
        self.next_button.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.next_button)
        table_layout.addWidget(self.pagination_widget)
        scroll_layout.addWidget(self.box_table_container)

        # Model spinner
        self.model_id = QComboBox()
        self.model_id.addItem("Choisir un modele")
        self.model_id.setFixedHeight(40)
        self.model_id.setFixedWidth(150)
        self.model_id.setFont(self.emoji_font)
        self.model_id.setStyleSheet("background-color: white; border: 1.2px solid #CCCCCC; color: black;")
        self.model_id.currentTextChanged.connect(self.spinner_selected)
        self.model_id.setVisible(self.show_table)
        scroll_layout.addWidget(self.model_id)

        # Bar chart container
        self.bar_chart_container = QWidget()
        self.bar_chart_layout = QVBoxLayout(self.bar_chart_container)
        self.bar_chart_layout.setContentsMargins(40, 40, 40, 40)
        self.bar_chart_container.setVisible(self.show_statistics)
        scroll_layout.addWidget(self.bar_chart_container)

        # Per-chain table and chart container
        self.tableau_graphique_container = QWidget()
        self.tableau_graphique_layout = QVBoxLayout(self.tableau_graphique_container)
        self.tableau_graphique_layout.setSpacing(20)
        self.tableau_graphique_container.setVisible(self.show_statistics)
        scroll_layout.addWidget(self.tableau_graphique_container)
        scroll_layout.addStretch()

    def get_maximum_num_of_ofs(self):
        try:
            response = make_request("get", "/manage_ofs/get_maximum_date_of_ofs")
            if response.status_code in (200, 201):
                self.maxnumOfs = response.json()[0].get("maxNumberOfOfs")
                print(f"Max number of OFs: {self.maxnumOfs}")
            else:
                print(f"HTTP Error: {response.status_code}")
                self.show_popup("Erreur", f"Erreur serveur: Code {response.status_code}")
        except RequestException as e:
            print(f"Network Error: {e}")
            self.show_popup("Erreur", "Problème de connexion au serveur. Vérifiez votre réseau.")
        except KeyError as e:
            print(f"Data Error: {e}")
            self.show_popup("Erreur", "Données inattendues reçues du serveur.")
        except Exception as e:
            print(f"Unexpected Error in get_maximum_num_of_ofs: {e}")
            self.show_popup("Erreur", f"Erreur inattendue: {str(e)}")

    def loadofs(self):
        try:
            data = {"numof": int(self.search_text)}
            response = make_request("get", "/manage_ofs/getofs_byModele", json=data)
            if response.status_code in (200, 201):
                response_data = response.json()
                if not isinstance(response_data, list) or not response_data:
                    self.show_popup("Info", "Aucune donnée reçue pour cette recherche")
                    self.df = []
                    return
                self.df = response_data[0].get("ofs", [])
                if not self.df:
                    self.show_popup("Info", "Aucun ordre de fabrication trouvé")
                else:
                    print("Loaded OFs:", self.df)
                    self.populate_table()
            else:
                print(f"HTTP Error: {response.status_code}")
                self.show_popup("Erreur", f"Erreur serveur: Code {response.status_code}")
        except RequestException as e:
            print(f"Network Error: {e}")
            self.show_popup("Erreur", "Problème de connexion au serveur. Vérifiez votre réseau.")
        except ValueError as e:
            print(f"JSON Error: {e}")
            self.show_popup("Erreur", "Erreur dans les données reçues du serveur.")
        except Exception as e:
            print(f"Unexpected Error in loadofs: {e}")
            self.show_popup("Erreur", f"Erreur inattendue: {str(e)}")

    def populate_table(self):
        try:
            if not self.df:
                self.show_popup("Info", "Aucune donnée à afficher")
                return
            required_keys = {col["key"] for col in self.table_columns}
            for row in self.df:
                if not all(key in row for key in required_keys):
                    print(f"Missing keys in row: {row}")
                    self.show_popup("Erreur", f"Données incomplètes pour le modèle {row.get('Modele', 'inconnu')}")
                    return

            for i in reversed(range(self.header_grid.count())):
                self.header_grid.itemAt(i).widget().setParent(None)
            for i in reversed(range(self.table_grid.count())):
                self.table_grid.itemAt(i).widget().setParent(None)

            col_widths = [col["width"] for col in self.table_columns]
            total_width = sum(col_widths)

            # Headers
            for i, col in enumerate(self.table_columns):
                header = QLabel(col["label"])
                header.setFont(QFont(self.emoji_font.family(), 10, QFont.Bold))
                header.setFixedWidth(col_widths[i])
                header.setFixedHeight(40)
                header.setAlignment(Qt.AlignCenter)
                header.setStyleSheet("color: black; padding: 5px;")
                self.header_grid.addWidget(header, 0, i)

            # Table rows with pagination
            start_idx = (self.current_page - 1) * self.rows_per_page
            end_idx = start_idx + self.rows_per_page
            visible_rows = self.df[start_idx:end_idx]
            row_height = 40
            content_height = row_height * len(visible_rows)
            self.box_table_container.setMinimumHeight(40 + content_height)
            self.table_grid.setHorizontalSpacing(0)
            self.table_grid.setVerticalSpacing(0)
            for row_idx, row in enumerate(visible_rows):
                row_data = []
                for col in self.table_columns:
                    value = row.get(col["key"], "")
                    if "format" in col and callable(col["format"]):
                        value = col["format"](value)
                    row_data.append(str(value))
                row_widget = SelectableRowWidget(row_data, col_widths, self.on_row_selection_changed)
                self.table_grid.addWidget(row_widget, row_idx, 0, 1, len(self.table_columns))

            table_widget = self.table_scroll.widget()
            table_widget.setFixedWidth(total_width)
            table_widget.setFixedHeight(content_height)
            self.page_label.setText(f"Page {self.current_page}")
            self.prev_button.setEnabled(self.current_page > 1)
            self.next_button.setEnabled(end_idx < len(self.df))
        except Exception as e:
            print(f"Error in populate_table: {e}")
            self.show_popup("Erreur", f"Erreur lors du remplissage de la table: {str(e)}")

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.populate_table()

    def next_page(self):
        if self.current_page * self.rows_per_page < len(self.df):
            self.current_page += 1
            self.populate_table()

    def search(self):
        try:
            self.status_label.setText("🔄 Recherche en cours...")
            QApplication.processEvents()
            self.show_statistics = False
            self.models = []
            self.statistics = []
            self.ofsPerChaine = []
            self.model_id.setCurrentText("Choisir un modele")
            year = self.year_id.currentText()
            week = self.week_id.currentText()
            if year == "Choisir l'année" or week == "Choisir le num de semaine":
                self.status_label.setText("")
                self.show_popup("Attention", "Veuillez choisir une année et un numéro de semaine valides")
                return
            last_digit_year = year[-1]
            self.search_text = f"{last_digit_year}{week}"
            print(f"Search text: {self.search_text}")
            if len(self.search_text) == 3:
                data = {"numof": int(self.search_text)}
                response = make_request("get", "/manage_ofs/getofs_byModele", json=data)
                if response.status_code in (200, 201):
                    self.show_table = True
                    self.df = response.json()[0].get("ofs", [])
                    if self.df:
                        self.models = list(set(model["Modele"] for model in self.df))
                        self.model_id.clear()
                        self.model_id.addItem("Choisir un modele")
                        self.model_id.addItems(self.models)
                        print("Loaded models:", self.models)
                        self.loadStatistics()
                        self.current_page = 1
                        self.populate_table()
                        self.status_label.setText("✅ Recherche terminée")
                    else:
                        self.status_label.setText("")
                        self.show_popup("Erreur", "Aucun modèle lancé à cette date")
                        self.show_table = False
                else:
                    self.status_label.setText("")
                    self.show_popup("Erreur", f"Erreur lors de la recherche: {response.status_code}")
                    self.show_table = False
            else:
                self.status_label.setText("")
                self.show_popup("Attention", "Veuillez choisir un numéro valide")
                self.show_table = False
            self.pie_chart_container.setVisible(self.show_table)
            self.box_table_container.setVisible(self.show_table)
            self.model_id.setVisible(self.show_table)
        except RequestException as e:
            self.status_label.setText("❌ Erreur lors de la recherche")
            print(f"Network Error in search: {e}")
            self.show_popup("Erreur", "Problème de connexion au serveur. Vérifiez votre réseau.")
        except ValueError as e:
            self.status_label.setText("❌ Erreur lors de la recherche")
            print(f"JSON Error in search: {e}")
            self.show_popup("Erreur", "Erreur dans les données reçues du serveur.")
        except Exception as e:
            self.status_label.setText("❌ Erreur lors de la recherche")
            print(f"Unexpected Error in search: {e}")
            self.show_popup("Erreur", f"Erreur inattendue: {str(e)}")

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

    def on_enter(self):
        try:
            annee_actuelle = datetime.now().year
            self.show_table = False
            self.show_statistics = False
            self.year_id.addItems([str(i) for i in range(2025, annee_actuelle + 11)])
            self.week_id.addItems([f"{i:02}" for i in range(1, 53)])
            self.get_maximum_num_of_ofs()
            if self.maxnumOfs is not None:
                str_num = f"{self.maxnumOfs:03d}"
                num_week = str_num[1:3]
                anne_extract = str(annee_actuelle)[:3]
                self.year_id.setCurrentText(f"{anne_extract}{str_num[0]}")
                self.week_id.setCurrentText(num_week)
                self.search()
        except Exception as e:
            print(f"Error in on_enter: {e}")
            self.show_popup("Erreur", f"Erreur lors du chargement initial: {str(e)}")

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

    def loadStatistics(self):
        try:
            self.statistics = []
            data = {"numof": int(self.search_text), "models": self.models}
            response = make_request("get", "/manage_ofs/getStaticticPerModele", json=data)
            if response.status_code in (200, 201):
                self.statistics = response.json()[0].get("statistics", [])
                print("Loaded statistics:", self.statistics)
                self.afficher_pie_chart(self.statistics)
            else:
                print(f"HTTP Error: {response.status_code}")
                self.show_popup("Erreur", f"Erreur serveur: Code {response.status_code}")
        except RequestException as e:
            print(f"Network Error: {e}")
            self.show_popup("Erreur", "Problème de connexion au serveur. Vérifiez votre réseau.")
        except ValueError as e:
            print(f"JSON Error: {e}")
            self.show_popup("Erreur", "Erreur dans les données reçues du serveur.")
        except Exception as e:
            print(f"Unexpected Error in loadStatistics: {e}")
            self.show_popup("Erreur", f"Erreur inattendue: {str(e)}")

    def afficher_pie_chart(self, data):
        try:
            for i in reversed(range(self.pie_chart_layout.count())):
                self.pie_chart_layout.itemAt(i).widget().setParent(None)
            for item in data:
                modele = item["modele"]
                values = [item["nb_done"], item["nb_inProgress"], item["nb_waiting"]]
                labels = ["Terminés", "En cours", "En attente"]
                colors = ["#2ecc71", "#f1c40f", "#e74c3c"]
                web_view = QWebEngineView()
                web_view.setFixedWidth(450)
                web_view.setFixedHeight(250)
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                </head>
                <body>
                    <canvas id="pieChart" style="max-height: 250px;"></canvas>
                    <script>
                        var ctx = document.getElementById('pieChart').getContext('2d');
                        new Chart(ctx, {{
                            type: 'pie',
                            data: {{
                                labels: {labels},
                                datasets: [{{
                                    data: {values},
                                    backgroundColor: {colors},
                                    borderWidth: 1
                                }}]
                            }},
                            options: {{
                                plugins: {{
                                    title: {{
                                        display: true,
                                        text: '{modele}',
                                        font: {{size: 20}},
                                        color: '#34495e'
                                    }},
                                    legend: {{
                                        labels: {{font: {{size: 14}}}}
                                    }},
                                    tooltip: {{
                                        callbacks: {{
                                            label: function(context) {{
                                                let value = context.parsed;
                                                let sum = context.dataset.data.reduce((a, b) => a + b, 0);
                                                let percentage = (value * 100 / sum).toFixed(1) + '%';
                                                return context.label + ': ' + value + ' (' + percentage + ')';
                                            }}
                                        }}
                                    }}
                                }},
                                responsive: true,
                                maintainAspectRatio: false
                            }}
                        }});
                    </script>
                </body>
                </html>
                """
                web_view.setHtml(html_content)
                self.pie_chart_layout.addWidget(web_view)
        except Exception as e:
            print(f"Error in afficher_pie_chart: {e}")
            self.show_popup("Erreur", f"Erreur lors de l'affichage du graphique circulaire: {str(e)}")

    def bar_chart(self, values):
        try:
            for i in reversed(range(self.bar_chart_layout.count())):
                self.bar_chart_layout.itemAt(i).widget().setParent(None)
            categories = ['En attente', 'En cours', 'Terminé']
            colors = ["#e9c46a", "#2a9d8f", "#264653"]
            web_view = QWebEngineView()
            web_view.setFixedHeight(350)
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
            </head>
            <body>
                <canvas id="barChart" style="max-height: 350px;"></canvas>
                <script>
                    Chart.register(ChartDataLabels);
                    var ctx = document.getElementById('barChart').getContext('2d');
                    new Chart(ctx, {{
                        type: 'bar',
                        data: {{
                            labels: {categories},
                            datasets: [{{
                                data: {values},
                                backgroundColor: {colors},
                                borderWidth: 1
                            }}]
                        }},
                        options: {{
                            indexAxis: 'y',
                            plugins: {{
                                title: {{
                                    display: true,
                                    text: 'Statistiques des OFs',
                                    font: {{size: 24}},
                                    color: '#34495e'
                                }},
                                legend: {{
                                    display: false
                                }},
                                datalabels: {{
                                    anchor: 'end',
                                    align: 'left',
                                    font: {{size: 18}},
                                    color: 'black',
                                    formatter: function(value) {{
                                        return Math.round(value);
                                    }}
                                }}
                            }},
                            scales: {{
                                x: {{
                                    display: false
                                }},
                                y: {{
                                    ticks: {{
                                        font: {{size: 18}}
                                    }}
                                }}
                            }},
                            responsive: true,
                            maintainAspectRatio: false
                        }}
                    }});
                </script>
            </body>
            </html>
            """
            web_view.setHtml(html_content)
            self.bar_chart_layout.addWidget(web_view)
        except Exception as e:
            print(f"Error in bar_chart: {e}")
            self.show_popup("Erreur", f"Erreur lors de l'affichage du graphique à barres: {str(e)}")

    def spinner_selected(self, text):
        try:
            print(f"Spinner selected: {text}")
            for stat in self.statistics:
                if stat["modele"] == text:
                    self.show_statistics = True
                    self.bar_chart([stat["nb_waiting"], stat["nb_inProgress"], stat["nb_done"]])
                    self.loadofsPerModeleAndPerChaine(text)
                    break
            self.bar_chart_container.setVisible(self.show_statistics)
            self.tableau_graphique_container.setVisible(self.show_statistics)
        except Exception as e:
            print(f"Error in spinner_selected: {e}")
            self.show_popup("Erreur", f"Erreur lors de la sélection du modèle: {str(e)}")

    def loadofsPerModeleAndPerChaine(self, modele):
        try:
            self.ofsPerChaine = []
            data = {"numof": int(self.search_text), "modele": modele}
            response = make_request("get", "/manage_ofs/getAllofsGroupbyChainewithStatistic", json=data)
            if response.status_code in (200, 201):
                self.ofsPerChaine = response.json()[0].get("statistics", [])
                print("Loaded OFs per chaine:", self.ofsPerChaine)
                self.populate_table_ofs_and_chart(self.ofsPerChaine)
            else:
                print(f"HTTP Error: {response.status_code}")
                self.show_popup("Erreur", f"Erreur serveur: Code {response.status_code}")
        except RequestException as e:
            print(f"Network Error: {e}")
            self.show_popup("Erreur", "Problème de connexion au serveur. Vérifiez votre réseau.")
        except ValueError as e:
            print(f"JSON Error: {e}")
            self.show_popup("Erreur", "Erreur dans les données reçues du serveur.")
        except Exception as e:
            print(f"Unexpected Error in loadofsPerModeleAndPerChaine: {e}")
            self.show_popup("Erreur", f"Erreur inattendue: {str(e)}")









    def debug_data_structure(self):
        """Affiche la structure des données pour le débogage"""
        try:
            print("=== DEBUG: Structure des données ===")
            for i, chaine in enumerate(self.ofsPerChaine):
                print(f"Chaîne {i}: ID={chaine.get('idChaine', 'N/A')}")
                print(f"  Nombre d'OFs: {len(chaine.get('ofs', []))}")

                for j, of in enumerate(chaine.get('ofs', [])):
                    print(f"    OF {j}:")
                    for key, value in of.items():
                        print(f"      {key}: {value}")
                    print()
        except Exception as e:
            print(f"Erreur lors du débogage de la structure: {e}")

    def on_spinner_select(self, spinner, selected_value):
        try:
            chaine_id = getattr(spinner, 'chaine_id', None)
            if not chaine_id:
                print(f"Error: No chaine_id found for spinner with value {selected_value}")
                self.show_popup("Erreur", "Aucune chaîne associée au filtre sélectionné")
                return
            print(f"Spinner selected: {selected_value} for chain {chaine_id}")

            # Debug: Log all widgets in tableau_graphique_layout
            print("Widgets in tableau_graphique_layout:")
            for i in range(self.tableau_graphique_layout.count()):
                widget = self.tableau_graphique_layout.itemAt(i).widget()
                widget_type = type(widget).__name__ if widget else "None"
                widget_chaine_id = getattr(widget, 'chaine_id', 'None') if widget else "None"
                has_tableau = hasattr(widget, 'tableau') if widget else False
                print(f"Index {i}: type={widget_type}, chaine_id={widget_chaine_id}, has_tableau={has_tableau}")

            # Find the row widget with matching chaine_id and tableau attribute
            for i in range(self.tableau_graphique_layout.count()):
                child = self.tableau_graphique_layout.itemAt(i).widget()
                if not child or not hasattr(child, 'chaine_id') or not hasattr(child, 'tableau'):
                    print(
                        f"Skipping widget at index {i}: Not a row widget (type={type(child).__name__ if child else 'None'}, chaine_id={getattr(child, 'chaine_id', 'None') if child else 'None'}, has_tableau={hasattr(child, 'tableau') if child else False})")
                    continue
                if child.chaine_id == chaine_id:
                    table_layout = child.tableau
                    print(f"Found table layout for chain {chaine_id} at index {i}")
                    self.filtrer_tableau(table_layout, chaine_id, selected_value)
                    return
            print(f"Error: No row widget with table layout found for chain {chaine_id}")
            self.show_popup("Erreur", f"Aucune table trouvée pour la chaîne {chaine_id}")
        except Exception as e:
            print(f"Error in on_spinner_select: {e}")
            self.show_popup("Erreur", f"Erreur lors de la sélection du filtre: {str(e)}")

    def populate_table_ofs_and_chart(self, data):
        try:
            for i in reversed(range(self.tableau_graphique_layout.count())):
                widget = self.tableau_graphique_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()

            for item in data:
                ofs_list = item['ofs']
                # Title
                title = QLabel(f"<b>Chaîne : {item['idChaine']}</b>")
                title.setFont(QFont(self.emoji_font.family(), 12, QFont.Bold))
                title.setStyleSheet("color: rgba(26, 77, 128, 255);")
                title.setFixedHeight(20)
                self.tableau_graphique_layout.addWidget(title)
                print(f"Added title for chain {item['idChaine']}")

                # Filter spinner
                spinner = QComboBox()
                spinner.addItems(["Filtrer les OFs", "Tous", "En attente", "En cours", "Terminés"])
                spinner.setFont(self.emoji_font)
                spinner.setFixedSize(200, 35)
                spinner.setStyleSheet("background-color: white; border: 1.2px solid #CCCCCC; color: black;")
                spinner.chaine_id = item["idChaine"]
                spinner.currentTextChanged.connect(lambda text, s=spinner: print(
                    f"Spinner triggered for chain {s.chaine_id} with value {text}") or self.on_spinner_select(s, text))
                self.tableau_graphique_layout.addWidget(spinner)
                print(f"Added spinner for chain {item['idChaine']}")

                # Row with table and chart
                row = QWidget()
                row_layout = QHBoxLayout(row)
                row_layout.setSpacing(10)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row.setFixedHeight(400)  # Increased from 300 to 350
                row.chaine_id = item['idChaine']

                # Table
                table_scroll = QScrollArea()
                table_scroll.setFixedWidth(600)  # Increased from 420 to 500
                table_widget = QWidget()
                table_layout = QGridLayout(table_widget)
                table_layout.setHorizontalSpacing(5)
                table_layout.setVerticalSpacing(0)
                table_scroll.setWidget(table_widget)
                table_scroll.setWidgetResizable(True)
                row.tableau = table_layout  # Store table_layout on row widget
                columns = ["numOF", "Pointure", "Quantité", "État", "Date lancement", "Date fin", "Ouvriers"]
                for col_idx, col in enumerate(columns):
                    header = QLabel(f"<b>{col}</b>")
                    header.setFont(QFont(self.emoji_font.family(), 10, QFont.Bold))
                    header.setStyleSheet("color: rgba(51, 51, 51, 255);")
                    header.setFixedHeight(50)  # Increased from 30 to 40
                    table_layout.addWidget(header, 0, col_idx)
                for idx, of in enumerate(ofs_list):
                    bg_color = "white" if idx % 2 == 0 else "#F5F5F5"
                    fields_map = {
                        "numOF": of.get("numCommandeOF") or of.get("numOF") or "-",
                        "Pointure": of.get("Pointure", "-"),
                        "Quantité": of.get("Quantite", "-"),
                        "État": of.get("etat", "-"),
                        "Date lancement": of.get("dateLancement_of_chaine", "-"),
                        "Date fin": of.get("dateFin", "-"),
                        "Ouvriers": of.get("ouvriers", "-"),
                    }
                    for col_idx, key in enumerate(columns):
                        label = QLabel(str(fields_map[key]))
                        label.setFont(QFont(self.emoji_font.family(), 10))
                        label.setStyleSheet(f"color: rgba(26, 77, 128, 255); background-color: {bg_color};")
                        label.setFixedHeight(50)  # Increased from 30 to 40
                        table_layout.addWidget(label, idx + 1, col_idx)
                table_widget.setFixedHeight(50 * (len(ofs_list) + 1))  # Updated to use 40
                row_layout.addWidget(table_scroll)

                # Pie chart with Chart.js
                values = [item["nb_en_attente"], item["nb_en_cours"], item["nb_termine"]]
                labels = ["En attente", "En cours", "Terminés"]
                colors = ["#e9c46a", "#2a9d8f", "#264653"]
                web_view = QWebEngineView()
                web_view.setFixedWidth(450)
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                </head>
                <body>
                    <canvas id="pieChart" style="max-height: 250px;"></canvas>
                    <script>
                        var ctx = document.getElementById('pieChart').getContext('2d');
                        new Chart(ctx, {{
                            type: 'pie',
                            data: {{
                                labels: {labels},
                                datasets: [{{
                                    data: {values},
                                    backgroundColor: {colors},
                                    borderWidth: 1
                                }}]
                            }},
                            options: {{
                                plugins: {{
                                    legend: {{
                                        labels: {{font: {{size: 14}}}}
                                    }},
                                    tooltip: {{
                                        callbacks: {{
                                            label: function(context) {{
                                                let value = context.parsed;
                                                let sum = context.dataset.data.reduce((a, b) => a + b, 0);
                                                let percentage = (value * 100 / sum).toFixed(1) + '%';
                                                return context.label + ': ' + value + ' (' + percentage + ')';
                                            }}
                                        }}
                                    }}
                                }},
                                responsive: true,
                                maintainAspectRatio: false
                            }}
                        }});
                    </script>
                </body>
                </html>
                """
                web_view.setHtml(html_content)
                row_layout.addWidget(web_view)

                self.tableau_graphique_layout.addWidget(row)
                print(
                    f"Added row for chain {item['idChaine']} with table layout, chaine_id={row.chaine_id}, has_tableau={hasattr(row, 'tableau')}")
                spacer = QWidget()
                spacer.setFixedHeight(20)
                self.tableau_graphique_layout.addWidget(spacer)
                print(f"Added spacer for chain {item['idChaine']}")
        except Exception as e:
            print(f"Error in populate_table_ofs_and_chart: {e}")
            self.show_popup("Erreur", f"Erreur lors du remplissage de la table et du graphique: {str(e)}")

    def filtrer_tableau(self, table_layout, chaine_id, filtre):
        try:
            # Find the relevant chain data
            ofs_for_filter = []
            for chaine in self.ofsPerChaine:
                if chaine["idChaine"] == chaine_id:
                    ofs_for_filter = chaine["ofs"]
                    break

            if not ofs_for_filter:
                print(f"No OFs found for chain {chaine_id}")
                self.show_popup("Info", f"Aucun ordre de fabrication trouvé pour la chaîne {chaine_id}")
                return

            # Log all unique etat values for debugging
            etat_values = sorted(set(of.get('etat', '-') for of in ofs_for_filter))
            print(f"Available 'etat' values for chain {chaine_id}: {etat_values}")

            # Apply filtering based on the selected value
            if filtre == "Tous":
                filtrés = ofs_for_filter
            elif filtre == "En cours":
                filtrés = [of for of in ofs_for_filter if of.get('etat', '-') == 'enCours']
            elif filtre == "Terminés":
                filtrés = [of for of in ofs_for_filter if of.get('etat', '-') == 'termine']
            elif filtre == "En attente":
                filtrés = [of for of in ofs_for_filter if of.get('etat', '-') == 'enAttente']
            else:
                filtrés = ofs_for_filter
                print(f"Unknown filter value: {filtre}, defaulting to all OFs")

            # Log the filtered results
            print(f"Filtered OFs for chain {chaine_id}, filter '{filtre}': {len(filtrés)} items")
            if filtrés:
                print(f"Filtered OFs etat values: {[of.get('etat', '-') for of in filtrés]}")

            # Clear existing table content
            for i in reversed(range(table_layout.count())):
                widget = table_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()

            # Define table columns
            columns = ["numOF", "Pointure", "Quantité", "État", "Date lancement", "Date fin", "Ouvriers"]

            # Add headers
            for col_idx, col in enumerate(columns):
                header = QLabel(f"<b>{col}</b>")
                header.setFont(QFont(self.emoji_font.family(), 10, QFont.Bold))
                header.setStyleSheet("color: rgba(51, 51, 51, 255);")
                header.setFixedHeight(30)
                table_layout.addWidget(header, 0, col_idx)

            # Populate filtered data
            for idx, of in enumerate(filtrés):
                bg_color = "white" if idx % 2 == 0 else "#F5F5F5"
                fields_map = {
                    "numOF": of.get("numCommandeOF") or of.get("numOF") or "-",
                    "Pointure": of.get("Pointure", "-"),
                    "Quantité": of.get("Quantite", "-"),
                    "État": of.get("etat", "-"),
                    "Date lancement": of.get("dateLancement_of_chaine", "-"),
                    "Date fin": of.get("dateFin", "-"),
                    "Ouvriers": of.get("ouvriers", "-"),
                }
                for col_idx, key in enumerate(columns):
                    label = QLabel(str(fields_map[key]))
                    label.setFont(QFont(self.emoji_font.family(), 10))
                    label.setStyleSheet(f"color: rgba(26, 77, 128, 255); background-color: {bg_color};")
                    label.setFixedHeight(30)
                    table_layout.addWidget(label, idx + 1, col_idx)

            # Update table widget height
            table_widget = table_layout.parentWidget()
            table_widget.setFixedHeight(30 * (len(filtrés) + 1))

            # Show message if no results
            if not filtrés:
                self.show_popup("Info",
                                f"Aucun ordre de fabrication trouvé pour le filtre '{filtre}' dans la chaîne {chaine_id}")

            # Force layout update
            table_widget.update()
            table_widget.parentWidget().update()
        except Exception as e:
            print(f"Error in filtrer_tableau: {e}")
            self.show_popup("Erreur", f"Erreur lors du filtrage de la table: {str(e)}")



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