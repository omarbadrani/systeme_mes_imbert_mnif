import requests
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, pyqtSignal
from frontend.SessionManager import SessionManager

class LoginWindow(QWidget):
    switch_screen = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.session = SessionManager.get_instance()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Login")
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignCenter)
        main_widget.setStyleSheet("background-color: rgba(242, 242, 242, 255);")
        self.setLayout(main_layout)

        # Welcome label
        welcome_label = QLabel("Bienvenue!")
        welcome_label.setFont(QFont("Arial", 24, QFont.Bold))
        welcome_label.setStyleSheet("color: rgba(51, 51, 51, 255);")
        welcome_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(welcome_label)
        main_layout.addSpacing(20)

        # Login form container
        form_container = QWidget()
        form_container.setFixedSize(360, 450)
        form_container.setStyleSheet("""
            background-color: white;
            border-radius: 20px;
        """)
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(30, 30, 30, 30)
        form_layout.setSpacing(20)
        main_layout.addWidget(form_container)

        # Login title
        login_label = QLabel("Login")
        login_label.setFont(QFont("Arial", 20))
        login_label.setStyleSheet("color: rgba(77, 77, 77, 255);")
        login_label.setFixedHeight(40)
        login_label.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(login_label)

        # Username field
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Enter your username")
        self.login_input.setFont(QFont("Arial", 14))
        self.login_input.setFixedHeight(40)
        self.login_input.setStyleSheet("""
            background-color: rgba(242, 242, 242, 255);
            color: black;
            padding: 10px;
            border: none;
        """)
        form_layout.addWidget(self.login_input)

        # Username error label
        self.login_error = QLabel("")
        self.login_error.setFont(QFont("Arial", 12))
        self.login_error.setStyleSheet("color: red;")
        self.login_error.setFixedHeight(20)
        form_layout.addWidget(self.login_error)

        # Password label
        password_label = QLabel("Password")
        password_label.setFont(QFont("Arial", 20))
        password_label.setStyleSheet("color: rgba(77, 77, 77, 255);")
        password_label.setFixedHeight(40)
        form_layout.addWidget(password_label)

        # Password field
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setFont(QFont("Arial", 14))
        self.password_input.setFixedHeight(40)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("""
            background-color: rgba(242, 242, 242, 255);
            color: black;
            padding: 10px;
            border: none;
        """)
        self.password_input.returnPressed.connect(self.on_login)
        form_layout.addWidget(self.password_input)

        # Password error label
        self.password_error = QLabel("")
        self.password_error.setFont(QFont("Arial", 12))
        self.password_error.setStyleSheet("color: red;")
        self.password_error.setFixedHeight(20)
        form_layout.addWidget(self.password_error)

        # Login button
        login_button = QPushButton("Login")
        login_button.setFont(QFont("Arial", 12))
        login_button.setFixedHeight(45)
        login_button.setStyleSheet("""
            background-color: rgba(51, 153, 219, 255);
            color: white;
            border: none;
        """)
        login_button.clicked.connect(self.on_login)
        form_layout.addWidget(login_button)
        main_layout.addStretch()

    def on_login(self):
        login_value = self.login_input.text()
        password_value = self.password_input.text()

        self.login_error.setText("Veuillez entrer un nom d'utilisateur" if not login_value else "")
        self.password_error.setText("Veuillez entrer votre mot de passe" if not password_value else "")

        if login_value and password_value:
            url = "http://192.168.1.210:5001/auth/login"
            data = {"username": login_value, "password": password_value}
            try:
                response = requests.post(url, json=data)
                print("Response:", response.json())
                if response.status_code == 200:
                    data = response.json()[0]  # Adjust for [data, status] response
                    self.session.set_tokens(data.get("access_token"), data.get("refresh_token"))
                    role = data.get("role")
                    if role == "production":
                        self.switch_screen.emit("launch_screen")
                    elif role == "userManager":
                        self.switch_screen.emit("list_users_screen")
                    elif role == "Technicien picure2 🛠":
                        self.switch_screen.emit("adduser_screen")
                    else:
                        self.show_popup("Erreur", "Rôle non reconnu")
                elif response.status_code == 401:
                    self.show_popup("Erreur de connexion", response.json().get("message", "Login ou mot de passe incorrect"))
                else:
                    self.show_popup("Erreur de connexion", "Une erreur est survenue")
            except requests.exceptions.RequestException as e:
                self.show_popup("Erreur de connexion", "Impossible de se connecter au serveur")
                print("Erreur de connexion au serveur:", e)
        else:
            self.show_popup("Erreur", "Veuillez remplir tous les champs")

    def show_popup(self, title, message):
        popup = QMessageBox()
        popup.setWindowTitle(title)
        popup.setText(message)
        popup.setFont(QFont("Arial", 10))
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

    def logout(self):
        self.session.set_tokens(None, None)
        self.switch_screen.emit("login_screen")