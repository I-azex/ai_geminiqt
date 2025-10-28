import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

def generate_financial_report(data_summary: str) -> str:
    """Формирует аналитическую записку на основе данных."""
    model = genai.GenerativeModel("gemini-1.5-pro")
    prompt = f"""
    На основе данных о движении денежных средств:
    {data_summary}

    Составь краткую аналитическую записку для руководства.
    Сделай акцент на изменениях расходов, прибыли и налоговой нагрузке.
    """
    response = model.generate_content(prompt)
    return response.text
