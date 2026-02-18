import sys
from PySide6.QtWidgets import QApplication
from views.login_view import LoginView
from views.main_window import MainWindow


def start_app():
    print("Login OK – abrir sistema")
    main_window = MainWindow()
    main_window.show()
    login.close()


app = QApplication(sys.argv)
with open("styles/erp.qss", "r", encoding="utf-8") as f:
    app.setStyleSheet(f.read())

login = LoginView(on_success=start_app)
login.show()

sys.exit(app.exec())
