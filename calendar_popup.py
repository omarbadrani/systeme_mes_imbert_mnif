# widgets/calendar.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QCalendarWidget, QPushButton
from PyQt5.QtCore import QDate


class CalendarPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sélectionner une date")
        self.setModal(True)

        layout = QVBoxLayout()

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        layout.addWidget(self.calendar)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        layout.addWidget(self.ok_button)

        self.setLayout(layout)

    def selected_date(self):
        return self.calendar.selectedDate().toString("yyyy-MM-dd")