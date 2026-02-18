from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
)
from services.auth import login


class LoginView(QWidget):
    def __init__(self, on_success):
        super().__init__()
        self.on_success = on_success
        self.setWindowTitle("Login - PDV")

        layout = QVBoxLayout()

        layout.addWidget(QLabel("Email"))
        self.email_input = QLineEdit()
        layout.addWidget(self.email_input)

        layout.addWidget(QLabel("Senha"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password) # type: ignore
        layout.addWidget(self.password_input)

        self.login_button = QPushButton("Entrar")
        self.login_button.clicked.connect(self.handle_login)
        layout.addWidget(self.login_button)

        self.setLayout(layout)
        self.resize(420, 300)

    def handle_login(self):
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()

        success, error = login(email, password)

        if success:
            self.on_success()
        else:
            QMessageBox.critical(self, "Erro", error) # type: ignore
 