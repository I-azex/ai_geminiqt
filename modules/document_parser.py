import base64
import json
from pathlib import Path
import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

def extract_invoice_data(file_path):
    """Извлекает реквизиты из PDF или изображения счёта через Gemini API."""
    file = Path(file_path)
    mime_type = "application/pdf" if file.suffix.lower() == ".pdf" else "image/jpeg"

    with open(file, "rb") as f:
        data = f.read()
    base64_data = base64.b64encode(data).decode("utf-8")

    prompt = """
    Ты бухгалтерский ИИ. Проанализируй этот документ и верни JSON со следующими ключами:
    - ИНН поставщика
    - Название контрагента
    - Сумма
    - Дата
    - Назначение платежа
    Если чего-то нет, укажи null.
    """

    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content([
        {"mime_type": mime_type, "data": base64_data},
        {"text": prompt}
    ])

    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        return {"error": "Не удалось распарсить JSON", "raw_output": response.text}
