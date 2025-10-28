from flask import Flask, request, render_template_string, session, jsonify
from werkzeug.utils import secure_filename
import google.generativeai as genai
from config import GEMINI_API_KEY, UPLOAD_DIR
from pathlib import Path
import os
from modules.document_parser import extract_invoice_data
from modules.accounting_logic import classify_transaction
from modules.database import save_file_and_transactions, get_all_files, get_file_with_transactions
from modules.anomaly_detector import detect_anomalies_in_transactions
from modules.stats_tracker import stats_tracker
import base64
import json
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.before_request
def track_user_activity():
    """Отслеживание активности пользователей"""
    if 'session_id' not in session:
        session['session_id'] = secrets.token_hex(16)
    stats_tracker.update_user_activity(session['session_id'])

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ИИ-бухгалтер</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .stats-bar {
            background: rgba(255, 255, 255, 0.95);
            padding: 15px 30px;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 40px;
            backdrop-filter: blur(10px);
        }
        .stat-item {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 16px;
            color: #333;
        }
        .stat-icon {
            font-size: 24px;
        }
        .stat-value {
            font-weight: bold;
            color: #7c3aed;
            font-size: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.98);
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        h2 {
            color: #5b21b6;
            font-size: 36px;
            margin-bottom: 30px;
            text-align: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .btn-primary {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 14px 30px;
            border-radius: 10px;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            border: none;
            cursor: pointer;
            font-size: 16px;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }
        .section {
            margin: 25px 0;
            padding: 25px;
            border-radius: 15px;
            background: linear-gradient(135deg, #f5f7fa 0%, #f3e7ff 100%);
            border: 2px solid rgba(124, 58, 237, 0.1);
        }
        .section h3 {
            color: #5b21b6;
            margin-bottom: 15px;
            font-size: 20px;
        }
        input[type="text"], input[type="file"] {
            width: 100%;
            padding: 12px 15px;
            margin: 8px 0;
            border: 2px solid #e0d4f7;
            border-radius: 10px;
            font-size: 15px;
            transition: all 0.3s ease;
            background: white;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #7c3aed;
            box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
        }
        input[type="submit"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 14px 30px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            margin-top: 10px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        input[type="submit"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }
        input[type="submit"]:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        label {
            display: block;
            color: #5b21b6;
            font-weight: 600;
            margin-bottom: 5px;
        }
        .loading-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(91, 33, 182, 0.7);
            backdrop-filter: blur(5px);
            z-index: 9999;
            justify-content: center;
            align-items: center;
        }
        .loading-overlay.show {
            display: flex;
        }
        .loading-content {
            background: white;
            padding: 50px;
            border-radius: 20px;
            text-align: center;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        .spinner {
            border: 5px solid #f3f3f3;
            border-top: 5px solid #7c3aed;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .loading-text {
            color: #5b21b6;
            font-size: 20px;
            font-weight: bold;
        }
        .btn-container {
            text-align: center;
            margin-bottom: 30px;
        }
    </style>
</head>
<body>
    <div class="stats-bar" id="statsBar">
        <div class="stat-item">
            <span class="stat-icon">👥</span>
            <span>Онлайн: <span class="stat-value" id="onlineUsers">0</span></span>
        </div>
        <div class="stat-item">
            <span class="stat-icon">📂</span>
            <span>В обработке: <span class="stat-value" id="processingFiles">0</span></span>
        </div>
    </div>

    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-content">
            <div class="spinner"></div>
            <div class="loading-text">Обработка документа...</div>
            <p style="color: #666; margin-top: 15px; font-size: 14px;">Пожалуйста, подождите</p>
        </div>
    </div>

    <div class="container">
        <h2>🤖 ИИ-бухгалтер</h2>
        
        <div class="btn-container">
            <a href="/history" class="btn-primary">📋 История обработанных файлов</a>
        </div>
        
        <div class="section">
            <h3>📄 Загрузить PDF/изображение счёта</h3>
            <form method="post" action="/upload" enctype="multipart/form-data" id="uploadForm">
                <label>Выберите файл (PDF, JPG, PNG):</label>
                <input type="file" name="file" accept=".pdf,.jpg,.jpeg,.png" required>
                <label>Вопрос по документу (опционально):</label>
                <input type="text" name="question" placeholder="Например: Какая общая сумма по всем позициям?">
                <input type="submit" value="Обработать документ" id="uploadSubmit">
            </form>
        </div>
        
        <div class="section">
            <h3>💬 Задать вопрос бухгалтеру</h3>
            <form method="post" action="/chat" id="chatForm">
                <label>Введите запрос:</label>
                <input type="text" name="message" placeholder="Например: Как учитывать НДС?" required>
                <input type="submit" value="Отправить" id="chatSubmit">
            </form>
        </div>
    </div>

    <script>
        function updateStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('onlineUsers').textContent = data.online_users;
                    document.getElementById('processingFiles').textContent = data.processing_files;
                })
                .catch(error => console.error('Ошибка загрузки статистики:', error));
        }

        updateStats();
        setInterval(updateStats, 5000);

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
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1100px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.98);
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        h2 {
            color: #5b21b6;
            font-size: 32px;
            margin-bottom: 25px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 25px;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        th, td {
            padding: 15px;
            text-align: left;
        }
        th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: 600;
        }
        tr {
            border-bottom: 1px solid #e0d4f7;
            transition: all 0.2s ease;
        }
        tr:hover {
            background: linear-gradient(135deg, #faf5ff 0%, #f5f3ff 100%);
        }
        td a {
            color: #7c3aed;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.2s ease;
        }
        td a:hover {
            color: #5b21b6;
        }
        .btn {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 25px;
            border-radius: 10px;
            text-decoration: none;
            margin-bottom: 25px;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }
        .empty-state {
            text-align: center;
            padding: 60px 40px;
            background: linear-gradient(135deg, #f5f7fa 0%, #f3e7ff 100%);
            border-radius: 15px;
            color: #5b21b6;
            margin-top: 20px;
        }
        .empty-state p:first-child {
            font-size: 48px;
            margin-bottom: 15px;
        }
        .empty-state p:last-child {
            font-size: 18px;
            color: #7c3aed;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>📋 История обработанных файлов</h2>
        <a href="/" class="btn">← Назад на главную</a>
        
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
            <p>📭</p>
            <p>История пуста. Загрузите первый документ на главной странице</p>
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
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1100px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.98);
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        h2 {
            color: #5b21b6;
            font-size: 32px;
            margin-bottom: 25px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .transaction {
            background: white;
            border-left: 5px solid #7c3aed;
            padding: 20px;
            margin: 15px 0;
            border-radius: 15px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            transition: all 0.2s ease;
        }
        .transaction:hover {
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        .transaction.anomaly {
            border-left: 5px solid #ff9800;
            background: linear-gradient(135deg, #fff8e1 0%, #ffe0b2 10%, white 50%);
        }
        .transaction h3 {
            margin-top: 0;
            color: #5b21b6;
            font-size: 20px;
        }
        .transaction.anomaly h3 {
            color: #ff9800;
        }
        .anomaly-badge {
            background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
            color: white;
            padding: 5px 12px;
            border-radius: 8px;
            font-size: 12px;
            margin-left: 10px;
            box-shadow: 0 2px 4px rgba(255, 152, 0, 0.3);
        }
        .anomaly-reasons {
            background: #fff3e0;
            border-left: 4px solid #ff9800;
            padding: 15px;
            margin: 15px 0;
            border-radius: 10px;
        }
        .anomaly-reasons ul {
            margin: 5px 0;
            padding-left: 20px;
        }
        .data-row {
            display: flex;
            padding: 12px 0;
            border-bottom: 1px solid #e0d4f7;
        }
        .data-row:last-child {
            border-bottom: none;
        }
        .data-label {
            font-weight: 600;
            min-width: 220px;
            color: #5b21b6;
        }
        .data-value {
            color: #333;
            flex: 1;
        }
        .btn {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 25px;
            border-radius: 10px;
            text-decoration: none;
            margin-bottom: 25px;
            margin-right: 10px;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }
        .meta-info {
            background: linear-gradient(135deg, #f0fdf4 0%, #f3e7ff 100%);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 25px;
            border: 2px solid rgba(124, 58, 237, 0.2);
        }
        .qa-section {
            background: linear-gradient(135deg, #e0f2fe 0%, #f3e7ff 100%);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 25px;
            border-left: 5px solid #7c3aed;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        .qa-section h3 {
            margin-top: 0;
            color: #5b21b6;
        }
        .qa-section p {
            margin: 12px 0;
            line-height: 1.6;
        }
        h3 {
            color: #5b21b6;
            margin-top: 30px;
            margin-bottom: 15px;
            font-size: 24px;
        }
        #ai-answer {
            line-height: 1.8;
            color: #333;
        }
        #ai-answer code {
            background: #f3e7ff;
            padding: 2px 6px;
            border-radius: 4px;
            color: #7c3aed;
            font-family: 'Courier New', monospace;
        }
        #ai-answer pre {
            background: #1f2937;
            color: #a78bfa;
            padding: 15px;
            border-radius: 10px;
            overflow-x: auto;
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
            {% set anomaly_count = file.transactions|selectattr('is_anomaly', 'equalto', 1)|list|length %}
            {% if anomaly_count > 0 %}
            <div class="data-row">
                <div class="data-label">Обнаружено аномалий:</div>
                <div class="data-value" style="color: #ff9800; font-weight: bold;">⚠️ {{ anomaly_count }}</div>
            </div>
            {% endif %}
        </div>
        
        {% if file.user_question and file.ai_answer %}
        <div class="qa-section">
            <h3 style="margin-top: 0;">💬 Вопрос и ответ по документу</h3>
            <p><b>❓ Вопрос:</b> {{ file.user_question }}</p>
            <p><b>💡 Ответ:</b></p>
            <div id="ai-answer"></div>
            <script>
                const aiAnswer = {{ file.ai_answer|tojson }};
                document.getElementById('ai-answer').innerHTML = marked.parse(aiAnswer);
            </script>
        </div>
        {% endif %}
        
        <h3>Транзакции:</h3>
        {% for transaction in file.transactions %}
        <div class="transaction{% if transaction.is_anomaly == 1 %} anomaly{% endif %}">
            <h3>
                Транзакция №{{ loop.index }}
                {% if transaction.is_anomaly == 1 %}
                <span class="anomaly-badge">⚠️ Аномалия</span>
                {% endif %}
            </h3>
            
            {% if transaction.is_anomaly == 1 and transaction.anomaly_reasons %}
            <div class="anomaly-reasons">
                <b>Обнаруженные проблемы:</b>
                <ul style="margin: 5px 0; padding-left: 20px;">
                {% for reason in transaction.anomaly_reasons %}
                    <li>{{ reason }}</li>
                {% endfor %}
                </ul>
            </div>
            {% endif %}
            
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
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.98);
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        h2 {
            color: #5b21b6;
            font-size: 32px;
            margin-bottom: 25px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .result {
            background: linear-gradient(135deg, #f0fdf4 0%, #f3e7ff 100%);
            padding: 20px;
            border-radius: 15px;
            margin-top: 20px;
            border: 2px solid rgba(124, 58, 237, 0.2);
        }
        .error {
            background: linear-gradient(135deg, #fee2e2 0%, #fce7f3 100%);
            color: #991b1b;
            padding: 20px;
            border-radius: 15px;
            margin-top: 20px;
            border: 2px solid rgba(220, 38, 38, 0.3);
        }
        .transaction {
            background: white;
            border-left: 5px solid #7c3aed;
            padding: 20px;
            margin: 15px 0;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        .transaction h3 {
            margin-top: 0;
            color: #5b21b6;
        }
        .data-item {
            margin: 10px 0;
            padding: 12px;
            background: linear-gradient(135deg, #faf5ff 0%, #f5f3ff 100%);
            border-left: 3px solid #a78bfa;
            border-radius: 5px;
        }
        pre {
            background: #1f2937;
            color: #a78bfa;
            padding: 15px;
            border-radius: 10px;
            overflow-x: auto;
            white-space: pre-wrap;
        }
        a {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 25px;
            border-radius: 10px;
            text-decoration: none;
            font-weight: 600;
            margin-top: 20px;
            margin-right: 10px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        a:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }
        #ai-response {
            line-height: 1.8;
        }
        #ai-response h1, #ai-response h2, #ai-response h3 {
            color: #5b21b6;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        #ai-response code {
            background: #f3e7ff;
            padding: 2px 6px;
            border-radius: 4px;
            color: #7c3aed;
            font-family: 'Courier New', monospace;
        }
        #ai-response pre {
            background: #1f2937;
            color: #a78bfa;
            padding: 15px;
            border-radius: 10px;
            overflow-x: auto;
        }
        #ai-response ul, #ai-response ol {
            margin-left: 20px;
            line-height: 1.8;
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

@app.route("/api/stats")
def get_stats():
    """API endpoint для получения статистики"""
    return jsonify(stats_tracker.get_stats())

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
        escaped_text = json.dumps(response.text)
        content = f"<div id='ai-response'></div><script>const aiText = {escaped_text}; document.getElementById('ai-response').innerHTML = marked.parse(aiText);</script>"
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
        
        stats_tracker.start_processing(safe_filename)
        
        file_path = Path(UPLOAD_DIR) / safe_filename
        file.save(str(file_path))
        
        user_question = request.form.get("question", "").strip()
        ai_answer = None
        
        if user_question:
            try:
                with open(file_path, "rb") as f:
                    file_data = f.read()
                file_base64 = base64.b64encode(file_data).decode("utf-8")
                
                file_ext = Path(safe_filename).suffix.lower()
                if file_ext == ".pdf":
                    mime_type = "application/pdf"
                elif file_ext in ['.jpg', '.jpeg']:
                    mime_type = "image/jpeg"
                elif file_ext == '.png':
                    mime_type = "image/png"
                else:
                    mime_type = "application/pdf"
                
                response = model.generate_content([
                    {"mime_type": mime_type, "data": file_base64},
                    {"text": f"Ответь на вопрос по этому документу: {user_question}"}
                ])
                ai_answer = response.text
            except Exception as e:
                ai_answer = f"Ошибка при обработке вопроса: {str(e)}"
        
        transactions = extract_invoice_data(file_path)
        
        if not isinstance(transactions, list):
            transactions = [transactions]
        
        successful_transactions = []
        for transaction in transactions:
            if isinstance(transaction, dict) and "error" not in transaction:
                transaction["Счет"] = classify_transaction(transaction.get("Назначение платежа", ""))
                successful_transactions.append(transaction)
        
        if successful_transactions:
            successful_transactions = detect_anomalies_in_transactions(successful_transactions)
        
        all_transactions_with_anomalies = []
        for transaction in transactions:
            if isinstance(transaction, dict) and "error" not in transaction:
                all_transactions_with_anomalies.append(transaction)
        
        file_ext = Path(safe_filename).suffix.lower()
        file_id = save_file_and_transactions(safe_filename, file_ext, all_transactions_with_anomalies, user_question, ai_answer)
        
        html_content = f"<h3>✅ Документ успешно обработан!</h3>"
        html_content += f"<p><b>Найдено транзакций:</b> {len(transactions)}</p>"
        
        if user_question and ai_answer:
            html_content += f"<div style='background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 15px 0;'>"
            html_content += f"<p><b>❓ Ваш вопрос:</b> {user_question}</p>"
            html_content += f"<p><b>💡 Ответ:</b> {ai_answer}</p>"
            html_content += "</div>"
        
        anomaly_count = sum(1 for t in successful_transactions if t.get('is_anomaly', False))
        if anomaly_count > 0:
            html_content += f"<p style='color: orange;'><b>⚠️ Обнаружено аномалий:</b> {anomaly_count}</p>"
        
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
                is_anomaly = transaction.get('is_anomaly', False)
                anomaly_class = ' style="border-left: 4px solid #ff9800;"' if is_anomaly else ''
                html_content += f"<div class='transaction'{anomaly_class}>"
                if is_anomaly:
                    html_content += f"<h3>⚠️ Транзакция №{i} (Аномалия)</h3>"
                    reasons = transaction.get('anomaly_reasons', [])
                    if reasons:
                        html_content += f"<div style='background: #fff3e0; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>"
                        html_content += f"<b>Причины:</b> {', '.join(reasons)}"
                        html_content += "</div>"
                else:
                    html_content += f"<h3>Транзакция №{i}</h3>"
                
                for key, value in transaction.items():
                    if key not in ['is_anomaly', 'anomaly_reasons']:
                        html_content += f"<div class='data-item'><b>{key}:</b> {value if value else 'Не указано'}</div>"
                html_content += "</div>"
        
        if len(successful_transactions) > 0:
            html_content += f"<p style='margin-top: 20px;'>✅ {len(successful_transactions)} транзакци(й/я) сохранено в <a href='/history'>историю</a></p>"
            html_content += f"<p><a href='/file/{file_id}'>Просмотреть детали →</a></p>"
        
        stats_tracker.finish_processing(safe_filename)
        return render_template_string(RESULT_TEMPLATE, title="📄 Результат обработки документа", content=html_content, result_class="result")
    
    except Exception as e:
        if 'safe_filename' in locals():
            stats_tracker.finish_processing(safe_filename)
        content = f"<p>Ошибка при обработке файла: {str(e)}</p>"
        import traceback
        content += f"<pre>{traceback.format_exc()}</pre>"
        return render_template_string(RESULT_TEMPLATE, title="Ошибка", content=content, result_class="error")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
