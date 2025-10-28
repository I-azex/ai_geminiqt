from modules.document_parser import extract_invoice_data
from modules.accounting_logic import classify_transaction
from pathlib import Path
import json
from config import OUTPUT_DIR

def main():
    file_path = Path("data/uploads/test.pdf")  # Пример файла
    result = extract_invoice_data(file_path)

    if "error" not in result:
        result["Счет"] = classify_transaction(result.get("Назначение", ""))
    output_path = Path(OUTPUT_DIR) / "invoice_data.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("✅ Обработка завершена. Результат сохранён в:", output_path)

if __name__ == "__main__":
    main()
