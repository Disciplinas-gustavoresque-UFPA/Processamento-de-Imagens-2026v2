import os

# Deve ser definido antes de qualquer import de PySide6.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Fornece uma única ``QApplication`` para toda a sessão de testes."""
    app = QApplication.instance() or QApplication([])
    yield app
