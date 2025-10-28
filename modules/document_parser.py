import base64
import json
import re
from pathlib import Path
import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

def clean_json_response(text):
    """Очищает ответ от markdown форматирования и извлекает JSON."""
    text = text.strip()
    
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if json_match:
        return json_match.group(1).strip()
    
    return text

def extract_invoice_data(file_path):
    """Извлекает реквизиты из PDF или изображения счёта через Gemini API.
    Может извлекать как одну, так и несколько транзакций."""
    file = Path(file_path)
    
    file_ext = file.suffix.lower() if file.suffix else ""
    
    if file_ext == ".pdf":
        mime_type = "application/pdf"
    elif file_ext in ['.jpg', '.jpeg']:
        mime_type = "image/jpeg"
    elif file_ext == '.png':
        mime_type = "image/png"
    else:
        mime_type = "application/pdf"

    with open(file, "rb") as f:
        data = f.read()
    base64_data = base64.b64encode(data).decode("utf-8")

    prompt = """
    Ты бухгалтерский ИИ. Проанализируй этот документ и найди ВСЕ транзакции/операции в нем.
    
    Верни JSON массив, где каждый элемент содержит данные одной транзакции:
    - ИНН поставщика
    - Название контрагента
    - Сумма
    - Дата
    - Назначение платежа
    
    ВАЖНО:
    1. Если в документе НЕСКОЛЬКО транзакций/строк таблицы - верни массив со всеми транзакциями
    2. Если в документе ОДНА транзакция - всё равно верни массив с одним элементом
    3. Верни ТОЛЬКО JSON массив, без markdown форматирования и без дополнительного текста
    4. Если какого-то поля нет - укажи null
    
    Пример формата ответа:
    [
        {
            "ИНН поставщика": "1234567890",
            "Название контрагента": "ООО Компания",
            "Сумма": "10000",
            "Дата": "01.01.2024",
            "Назначение платежа": "Оплата за товар"
        }
    ]
    """

    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content([
        {"mime_type": mime_type, "data": base64_data},
        {"text": prompt}
    ])

    try:
        cleaned_text = clean_json_response(response.text)
        result = json.loads(cleaned_text)
        
        if not isinstance(result, list):
            result = [result]
        
        return result
        
    except json.JSONDecodeError as e:
        return [{
            "error": f"Не удалось распарсить JSON: {str(e)}", 
            "raw_output": response.text,
            "cleaned_output": clean_json_response(response.text)
        }]
