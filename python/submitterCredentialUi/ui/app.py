import sys
import signal
import os
from PySide6 import __version__ as PySideVersion
from PySide6 import QtCore
from PySide6.QtCore import QObject, QUrl, QJsonValue, qInstallMessageHandler, QtMsgType, QSettings, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

signal.signal(signal.SIGINT, signal.SIG_DFL)


class CredentialsBackend(QObject):
    """Backend to handle credentials between QML and Python."""
    
    def __init__(self):
        super().__init__()
        self._username = ""
        self._password = ""
        self._accepted = False
    
    @Slot(str, str)
    def setCredentials(self, username, password):
        """Called from QML when user accepts the dialog."""
        self._username = username
        self._password = password
        self._accepted = True
    
    def getCredentials(self):
        """Get the credentials after dialog closes."""
        if self._accepted:
            return {
                'username': self._username,
                'password': self._password
            }
        return None


class DialogApp(QApplication):
    """Password Dialog Application."""
    
    def __init__(self):
        super().__init__(sys.argv)
        
        font = self.font()
        font.setPointSize(9)
        self.setFont(font)
        
        # Use Fusion style by default
        QQuickStyle.setStyle("Fusion")
        
        pwd = os.path.dirname(__file__)
        
        # Create backend
        self.backend = CredentialsBackend()
        
        # QML engine setup
        qmlDir = os.path.join(pwd, "qml")
        url = os.path.join(qmlDir, "main.qml")
        self.engine = QQmlApplicationEngine()
        self.engine.addImportPath(qmlDir)
        
        # Expose backend to QML
        self.engine.rootContext().setContextProperty("backend", self.backend)
        
        # Load QML
        self.engine.load(os.path.normpath(url))
        
        if not self.engine.rootObjects():
            sys.exit(-1)
    
    def terminateManual(self):
        self.engine.clearComponentCache()
        self.engine.collectGarbage()
        self.engine.deleteLater()



def getCredentials():
    """ Show password dialog and return credentials.
    
    Example:
        credentials = getCredentials()
        if credentials:
            print(f"Username: {credentials['username']}")
            print(f"Password: {'*' * len(credentials['password'])}")
        else:
            print("Dialog cancelled")
    
    Returns:
        dict: {'username': str, 'password': str} if accepted, None if cancelled
    """
    app = DialogApp()
    app.aboutToQuit.connect(app.terminateManual)
    app.exec()
    
    # Get credentials from backend
    return app.backend.getCredentials()
