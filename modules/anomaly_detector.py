import pandas as pd
from sklearn.ensemble import IsolationForest
import re
from typing import List, Dict, Any

def parse_amount(amount_str: str) -> float:
    """Извлекает числовое значение из строки суммы."""
    if not amount_str or amount_str == "Не указана":
        return 0.0
    
    cleaned = re.sub(r'[^\d,.-]', '', str(amount_str))
    cleaned = cleaned.replace(',', '.')
    
    try:
        return float(cleaned)
    except (ValueError, AttributeError):
        return 0.0

def detect_anomalies_in_transactions(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Находит аномалии в списке транзакций.
    
    Анализирует:
    - Необычные суммы (выбросы)
    - Отсутствующие обязательные поля
    - Подозрительные паттерны
    
    Returns:
        List с добавленными полями 'is_anomaly' и 'anomaly_reasons'
    """
    if not transactions or len(transactions) < 3:
        for t in transactions:
            t['is_anomaly'] = False
            t['anomaly_reasons'] = []
        return transactions
    
    df = pd.DataFrame(transactions)
    
    amounts = []
    for t in transactions:
        amount = parse_amount(t.get('Сумма', ''))
        amounts.append(amount)
    
    df['amount_numeric'] = amounts
    
    valid_amounts = [a for a in amounts if a > 0]
    
    if len(valid_amounts) >= 3:
        model = IsolationForest(contamination=0.15, random_state=42)
        amount_array = [[a] for a in amounts]
        predictions = model.fit_predict(amount_array)
    else:
        predictions = [1] * len(amounts)
    
    for i, transaction in enumerate(transactions):
        anomaly_reasons = []
        
        if predictions[i] == -1 and amounts[i] > 0:
            anomaly_reasons.append("Необычная сумма")
        
        if not transaction.get('ИНН поставщика') or transaction.get('ИНН поставщика') == 'Не указан':
            anomaly_reasons.append("Отсутствует ИНН")
        
        if not transaction.get('Название контрагента') or transaction.get('Название контрагента') == 'Не указано':
            anomaly_reasons.append("Отсутствует контрагент")
        
        if amounts[i] == 0:
            anomaly_reasons.append("Нулевая или отсутствующая сумма")
        
        transaction['is_anomaly'] = len(anomaly_reasons) > 0
        transaction['anomaly_reasons'] = anomaly_reasons
    
    return transactions
