"""Базовая проверка структуры проекта."""


def test_import_app():
    """Проверяет, что пакет app импортируется без ошибок."""
    import app

    assert app is not None
