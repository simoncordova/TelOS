# Vacío a propósito: su sola presencia en la raíz del repo hace que
# pytest inserte la raíz en sys.path antes de recolectar tests, igual
# que scripts/chat_terminal.py hace a mano con sys.path.insert -- así
# `from api import main` (sin api/__init__.py, paquete de namespace
# implícito, mismo patrón que agents/ y tools/) funciona sin importar
# desde qué directorio se invoque pytest.
