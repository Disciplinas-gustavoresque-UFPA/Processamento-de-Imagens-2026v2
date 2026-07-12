from pathlib import Path
from PySide6.QtCore import QSettings, QStandardPaths


class Config:
    def __init__(self):
        # Salva em config.ini
        self.settings = QSettings(
            "config.ini",
            QSettings.IniFormat
        )

    def get_last_image_path(self):
        path = self.settings.value("paths/last_image_path", "")

        if path and Path(path).exists():
            return path

        # Se nunca abriu nada, retorna a pasta Imagens do usuário
        return QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.PicturesLocation
        )

    def set_last_image_path(self, path):
        self.settings.setValue("paths/last_image_path", path)
