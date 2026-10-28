import pytest
from app.utils.validators import validate_full_name

# --- ТЕСТ 1. Проверка правильного ФИО ---
def test_valid_full_name():
    # Вызываем функцию с правильными данными
    is_valid, error_msg = validate_full_name("Дюжев Фёдор Андреевич", gender="male")
    
    # Проверяем (assert), что функция вернула True и нет текста ошибки
    assert is_valid is True
    assert error_msg == ""

# --- ТЕСТ 2. Проверка неправильного пола (женское отчество у мужчины) ---
def test_invalid_gender_patronymic():
    is_valid, error_msg = validate_full_name("Дюжев Фёдор Андреевна", gender="male")
    
    # Проверяем, что функция вернула False и есть текст ошибки про отчество
    assert is_valid is False
    assert "отчество мужчины" in error_msg.lower()

# --- ТЕСТ 3. Проверка, что имя написано с маленькой буквы ---
def test_lowercase_name():
    is_valid, error_msg = validate_full_name("дюжев фёдор андреевич", gender="male")
    
    assert is_valid is False
    assert "с большой буквы" in error_msg.lower()

# --- ТЕСТ 4. Проверка, что ввели только 2 слова (нет отчества) ---
def test_short_name():
    is_valid, error_msg = validate_full_name("Дюжев Фёдор", gender="male")
    
    assert is_valid is False
    assert "ровно 3 слова" in error_msg