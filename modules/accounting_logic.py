def classify_transaction(description: str) -> str:
    """Простейшая логика сопоставления операции и бухгалтерского счёта."""
    if not description:
        return "91.02"
    
    text = description.lower()
    if "счет-фактура" in text:
        return "60.01"
    elif "акт" in text:
        return "20"
    elif "зарплата" in text:
        return "70"
    elif "налог" in text:
        return "68"
    else:
        return "91.02"
