import re
from unidecode import unidecode

def transliterate(value):
    # Транслитерация строки
    value = unidecode(value)
    # Замена пробелов и специальных символов на тире
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    value = re.sub(r'[-\s]+', '-', value)
    return value
