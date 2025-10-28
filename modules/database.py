import sqlite3
from datetime import datetime
from pathlib import Path
import json
from config import DB_PATH

def init_database():
    """Инициализация базы данных и создание таблиц."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploaded_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_type TEXT,
            status TEXT DEFAULT 'success',
            user_question TEXT,
            ai_answer TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            inn TEXT,
            counterparty TEXT,
            amount TEXT,
            date TEXT,
            purpose TEXT,
            account TEXT,
            is_anomaly INTEGER DEFAULT 0,
            anomaly_reasons TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES uploaded_files (id)
        )
    ''')
    
    try:
        cursor.execute('ALTER TABLE uploaded_files ADD COLUMN user_question TEXT')
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute('ALTER TABLE uploaded_files ADD COLUMN ai_answer TEXT')
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute('ALTER TABLE transactions ADD COLUMN is_anomaly INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute('ALTER TABLE transactions ADD COLUMN anomaly_reasons TEXT')
    except sqlite3.OperationalError:
        pass
    
    conn.commit()
    conn.close()

def save_file_and_transactions(filename, file_type, transactions_data, user_question=None, ai_answer=None):
    """Сохраняет файл и все его транзакции в базу данных."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT INTO uploaded_files (filename, file_type, user_question, ai_answer) VALUES (?, ?, ?, ?)',
        (filename, file_type, user_question, ai_answer)
    )
    file_id = cursor.lastrowid
    
    if isinstance(transactions_data, dict):
        transactions_data = [transactions_data]
    
    for transaction in transactions_data:
        if isinstance(transaction, dict) and "error" not in transaction:
            is_anomaly = 1 if transaction.get("is_anomaly", False) else 0
            anomaly_reasons = json.dumps(transaction.get("anomaly_reasons", []), ensure_ascii=False)
            
            cursor.execute('''
                INSERT INTO transactions 
                (file_id, inn, counterparty, amount, date, purpose, account, is_anomaly, anomaly_reasons)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                file_id,
                transaction.get("ИНН поставщика"),
                transaction.get("Название контрагента"),
                transaction.get("Сумма"),
                transaction.get("Дата"),
                transaction.get("Назначение платежа"),
                transaction.get("Счет"),
                is_anomaly,
                anomaly_reasons
            ))
    
    conn.commit()
    conn.close()
    
    return file_id

def get_all_files():
    """Получает список всех загруженных файлов."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT f.*, COUNT(t.id) as transaction_count
        FROM uploaded_files f
        LEFT JOIN transactions t ON f.id = t.file_id
        GROUP BY f.id
        ORDER BY f.upload_date DESC
    ''')
    
    files = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return files

def get_file_transactions(file_id):
    """Получает все транзакции для конкретного файла."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM transactions
        WHERE file_id = ?
        ORDER BY id
    ''', (file_id,))
    
    transactions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return transactions

def get_file_with_transactions(file_id):
    """Получает файл вместе со всеми его транзакциями."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM uploaded_files WHERE id = ?', (file_id,))
    file_data = cursor.fetchone()
    
    if not file_data:
        conn.close()
        return None
    
    file_dict = dict(file_data)
    
    cursor.execute('''
        SELECT * FROM transactions
        WHERE file_id = ?
        ORDER BY id
    ''', (file_id,))
    
    transactions = []
    for row in cursor.fetchall():
        t = dict(row)
        if t.get('anomaly_reasons'):
            try:
                t['anomaly_reasons'] = json.loads(t['anomaly_reasons'])
            except (json.JSONDecodeError, TypeError):
                t['anomaly_reasons'] = []
        else:
            t['anomaly_reasons'] = []
        transactions.append(t)
    
    conn.close()
    
    file_dict['transactions'] = transactions
    
    return file_dict

init_database()
