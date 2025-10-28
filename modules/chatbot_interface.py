from flask import Flask, request, render_template_string
from werkzeug.utils import secure_filename
import google.generativeai as genai
from config import GEMINI_API_KEY, UPLOAD_DIR
from pathlib import Path
import os
from modules.document_parser import extract_invoice_data
from modules.accounting_logic import classify_transaction
from modules.database import save_file_and_transactions, get_all_files, get_file_with_transactions
import json

app = Flask(__name__)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

os.makedirs(UPLOAD_DIR, exist_ok=True)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ИИ-бухгалтер</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h2 {
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        .section {
            margin: 20px 0;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
            background-color: #fafafa;
        }
        input[type="text"], input[type="file"] {
            width: 100%;
            padding: 10px;
            margin: 5px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        input[type="submit"], .btn {
            background-color: #4CAF50;
            color: white;
            padding: 12px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 10px;
            text-decoration: none;
            display: inline-block;
        }
        input[type="submit"]:hover, .btn:hover {
            background-color: #45a049;
        }
        input[type="submit"]:disabled {
            background-color: #ccc;
            cursor: not-allowed;
        }
        a {
            color: #4CAF50;
            text-decoration: none;
            font-weight: bold;
        }
        a:hover {
            text-decoration: underline;
        }
        .loading-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            z-index: 9999;
            justify-content: center;
            align-items: center;
        }
        .loading-overlay.show {
            display: flex;
        }
        .loading-content {
            background: white;
            padding: 40px;
            border-radius: 10px;
            text-align: center;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #4CAF50;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .loading-text {
            color: #333;
            font-size: 18px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-content">
            <div class="spinner"></div>
            <div class="loading-text">Обработка документа...</div>
            <p style="color: #666; margin-top: 10px;">Пожалуйста, подождите</p>
        </div>
    </div>

    <div class="container">
        <h2>🤖 ИИ-бухгалтер</h2>
        
        <div style="text-align: center; margin-bottom: 20px;">
            <a href="/history" class="btn">📋 История обработанных файлов</a>
        </div>
        
        <div class="section">
            <h3>📄 Загрузить PDF/изображение счёта</h3>
            <form method="post" action="/upload" enctype="multipart/form-data" id="uploadForm">
                <label>Выберите файл (PDF, JPG, PNG):</label><br>
                <input type="file" name="file" accept=".pdf,.jpg,.jpeg,.png" required>
                <input type="submit" value="Обработать документ" id="uploadSubmit">
            </form>
        </div>
        
        <div class="section">
            <h3>💬 Задать вопрос бухгалтеру</h3>
            <form method="post" action="/chat" id="chatForm">
                <label>Введите запрос:</label><br>
                <input type="text" name="message" placeholder="Например: Как учитывать НДС?" required>
                <input type="submit" value="Отправить" id="chatSubmit">
            </form>
        </div>
    </div>

    <script>
        function showLoading(text) {
            const overlay = document.getElementById('loadingOverlay');
            const loadingText = overlay.querySelector('.loading-text');
            loadingText.textContent = text;
            overlay.classList.add('show');
        }

        document.getElementById('uploadForm').addEventListener('submit', function(e) {
            const submitBtn = document.getElementById('uploadSubmit');
            submitBtn.disabled = true;
            showLoading('Обработка документа...');
        });

        document.getElementById('chatForm').addEventListener('submit', function(e) {
            const submitBtn = document.getElementById('chatSubmit');
            submitBtn.disabled = true;
            showLoading('Получение ответа от ИИ...');
        });
    </script>
</body>
</html>
"""

HISTORY_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>История файлов</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1000px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h2 {
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #4CAF50;
            color: white;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        a {
            color: #4CAF50;
            text-decoration: none;
            font-weight: bold;
        }
        a:hover {
            text-decoration: underline;
        }
        .btn {
            display: inline-block;
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border-radius: 4px;
            text-decoration: none;
            margin-bottom: 20px;
        }
        .btn:hover {
            background-color: #45a049;
        }
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>📋 История обработанных файлов</h2>
        <a href="/" class="btn">← Назад</a>
        
        {% if files %}
        <table>
            <tr>
                <th>Имя файла</th>
                <th>Дата загрузки</th>
                <th>Количество транзакций</th>
                <th>Действие</th>
            </tr>
            {% for file in files %}
            <tr>
                <td>{{ file.filename }}</td>
                <td>{{ file.upload_date }}</td>
                <td>{{ file.transaction_count }}</td>
                <td><a href="/file/{{ file.id }}">Просмотреть →</a></td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <div class="empty-state">
            <p>📭 История пуста</p>
            <p>Загрузите первый документ на главной странице</p>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

FILE_DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ file.filename }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1000px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h2 {
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        .transaction {
            background: #fafafa;
            border-left: 4px solid #4CAF50;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }
        .transaction h3 {
            margin-top: 0;
            color: #4CAF50;
        }
        .data-row {
            display: flex;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        .data-label {
            font-weight: bold;
            min-width: 200px;
            color: #555;
        }
        .data-value {
            color: #333;
        }
        a {
            color: #4CAF50;
            text-decoration: none;
            font-weight: bold;
        }
        a:hover {
            text-decoration: underline;
        }
        .btn {
            display: inline-block;
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border-radius: 4px;
            text-decoration: none;
            margin-bottom: 20px;
        }
        .btn:hover {
            background-color: #45a049;
        }
        .meta-info {
            background: #e8f5e9;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>📄 {{ file.filename }}</h2>
        <a href="/history" class="btn">← К истории</a>
        <a href="/" class="btn">🏠 На главную</a>
        
        <div class="meta-info">
            <div class="data-row">
                <div class="data-label">Дата загрузки:</div>
                <div class="data-value">{{ file.upload_date }}</div>
            </div>
            <div class="data-row">
                <div class="data-label">Всего транзакций:</div>
                <div class="data-value">{{ file.transactions|length }}</div>
            </div>
        </div>
        
        <h3>Транзакции:</h3>
        {% for transaction in file.transactions %}
        <div class="transaction">
            <h3>Транзакция №{{ loop.index }}</h3>
            <div class="data-row">
                <div class="data-label">ИНН поставщика:</div>
                <div class="data-value">{{ transaction.inn or 'Не указан' }}</div>
            </div>
            <div class="data-row">
                <div class="data-label">Название контрагента:</div>
                <div class="data-value">{{ transaction.counterparty or 'Не указано' }}</div>
            </div>
            <div class="data-row">
                <div class="data-label">Сумма:</div>
                <div class="data-value">{{ transaction.amount or 'Не указана' }}</div>
            </div>
            <div class="data-row">
                <div class="data-label">Дата:</div>
                <div class="data-value">{{ transaction.date or 'Не указана' }}</div>
            </div>
            <div class="data-row">
                <div class="data-label">Назначение платежа:</div>
                <div class="data-value">{{ transaction.purpose or 'Не указано' }}</div>
            </div>
            <div class="data-row">
                <div class="data-label">Бухгалтерский счет:</div>
                <div class="data-value">{{ transaction.account or 'Не определен' }}</div>
            </div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

RESULT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Результат обработки</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1000px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h2 {
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        .result {
            background-color: #e8f5e9;
            padding: 15px;
            border-radius: 5px;
            margin-top: 20px;
        }
        .error {
            background-color: #ffebee;
            color: #c62828;
            padding: 15px;
            border-radius: 5px;
            margin-top: 20px;
        }
        .transaction {
            background: white;
            border-left: 4px solid #4CAF50;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }
        .transaction h3 {
            margin-top: 0;
            color: #4CAF50;
        }
        .data-item {
            margin: 10px 0;
            padding: 10px;
            background: #fafafa;
            border-left: 3px solid #4CAF50;
        }
        pre {
            background-color: #263238;
            color: #aed581;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            white-space: pre-wrap;
        }
        a {
            color: #4CAF50;
            text-decoration: none;
            font-weight: bold;
            display: inline-block;
            margin-top: 20px;
            margin-right: 10px;
        }
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>{{ title }}</h2>
        <div class="{{ result_class }}">
            {{ content | safe }}
        </div>
        <a href='/'>← На главную</a>
        <a href='/history'>📋 История</a>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/history")
def history():
    files = get_all_files()
    return render_template_string(HISTORY_TEMPLATE, files=files)

@app.route("/file/<int:file_id>")
def file_detail(file_id):
    file_data = get_file_with_transactions(file_id)
    if not file_data:
        content = "<p>Файл не найден</p>"
        return render_template_string(RESULT_TEMPLATE, title="Ошибка", content=content, result_class="error")
    return render_template_string(FILE_DETAIL_TEMPLATE, file=file_data)

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.form.get("message", "")
    try:
        response = model.generate_content(f"Ты опытный бухгалтер. Ответь на запрос: {user_input}")
        content = f"<p><b>Ответ:</b> {response.text}</p>"
        return render_template_string(RESULT_TEMPLATE, title="💬 Ответ ИИ-бухгалтера", content=content, result_class="result")
    except Exception as e:
        content = f"<p>Ошибка при обработке запроса: {str(e)}</p>"
        return render_template_string(RESULT_TEMPLATE, title="Ошибка", content=content, result_class="error")

@app.route("/upload", methods=["POST"])
def upload():
    if 'file' not in request.files:
        content = "<p>Файл не выбран</p>"
        return render_template_string(RESULT_TEMPLATE, title="Ошибка", content=content, result_class="error")
    
    file = request.files['file']
    if file.filename == '':
        content = "<p>Файл не выбран</p>"
        return render_template_string(RESULT_TEMPLATE, title="Ошибка", content=content, result_class="error")
    
    try:
        safe_filename = secure_filename(file.filename)
        if not safe_filename:
            content = "<p>Недопустимое имя файла</p>"
            return render_template_string(RESULT_TEMPLATE, title="Ошибка", content=content, result_class="error")
        
        file_path = Path(UPLOAD_DIR) / safe_filename
        file.save(str(file_path))
        
        transactions = extract_invoice_data(file_path)
        
        if not isinstance(transactions, list):
            transactions = [transactions]
        
        successful_transactions = []
        for transaction in transactions:
            if isinstance(transaction, dict) and "error" not in transaction:
                transaction["Счет"] = classify_transaction(transaction.get("Назначение платежа", ""))
                successful_transactions.append(transaction)
        
        file_ext = Path(safe_filename).suffix.lower()
        file_id = save_file_and_transactions(safe_filename, file_ext, transactions)
        
        html_content = f"<h3>✅ Документ успешно обработан!</h3>"
        html_content += f"<p><b>Найдено транзакций:</b> {len(transactions)}</p>"
        
        if len(successful_transactions) == 0:
            html_content += "<p style='color: orange;'><b>⚠️ Внимание:</b> Ни одна транзакция не была успешно обработана. Проверьте формат документа.</p>"
        
        has_errors = False
        for i, transaction in enumerate(transactions, 1):
            if isinstance(transaction, dict) and "error" in transaction:
                has_errors = True
                html_content += f"<div class='transaction'><h3>Ошибка обработки</h3>"
                html_content += f"<p><b>Ошибка:</b> {transaction['error']}</p>"
                if 'raw_output' in transaction:
                    html_content += f"<p><b>Ответ API:</b></p><pre>{transaction['raw_output']}</pre>"
                html_content += "</div>"
            else:
                html_content += f"<div class='transaction'><h3>Транзакция №{i}</h3>"
                for key, value in transaction.items():
                    html_content += f"<div class='data-item'><b>{key}:</b> {value if value else 'Не указано'}</div>"
                html_content += "</div>"
        
        if len(successful_transactions) > 0:
            html_content += f"<p style='margin-top: 20px;'>✅ {len(successful_transactions)} транзакци(й/я) сохранено в <a href='/history'>историю</a></p>"
        
        return render_template_string(RESULT_TEMPLATE, title="📄 Результат обработки документа", content=html_content, result_class="result")
    
    except Exception as e:
        content = f"<p>Ошибка при обработке файла: {str(e)}</p>"
        import traceback
        content += f"<pre>{traceback.format_exc()}</pre>"
        return render_template_string(RESULT_TEMPLATE, title="Ошибка", content=content, result_class="error")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
