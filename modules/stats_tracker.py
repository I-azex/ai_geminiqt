"""
Модуль для отслеживания статистики в реальном времени:
- Активные пользователи онлайн
- Файлы в процессе обработки
"""
import time
from threading import Lock
from collections import defaultdict

class StatsTracker:
    def __init__(self):
        self.lock = Lock()
        # Храним время последней активности для каждого пользователя (по session ID)
        self.active_users = {}
        # Храним файлы в обработке
        self.processing_files = set()
        # Время бездействия после которого пользователь считается offline (в секундах)
        self.user_timeout = 60
    
    def update_user_activity(self, session_id):
        """Обновить активность пользователя"""
        with self.lock:
            self.active_users[session_id] = time.time()
            self._cleanup_inactive_users()
    
    def _cleanup_inactive_users(self):
        """Удалить неактивных пользователей"""
        current_time = time.time()
        inactive = [
            sid for sid, last_active in self.active_users.items()
            if current_time - last_active > self.user_timeout
        ]
        for sid in inactive:
            del self.active_users[sid]
    
    def get_online_users_count(self):
        """Получить количество активных пользователей"""
        with self.lock:
            self._cleanup_inactive_users()
            return len(self.active_users)
    
    def start_processing(self, filename):
        """Начать обработку файла"""
        with self.lock:
            self.processing_files.add(filename)
    
    def finish_processing(self, filename):
        """Завершить обработку файла"""
        with self.lock:
            self.processing_files.discard(filename)
    
    def get_processing_files_count(self):
        """Получить количество файлов в обработке"""
        with self.lock:
            return len(self.processing_files)
    
    def get_stats(self):
        """Получить полную статистику"""
        return {
            'online_users': self.get_online_users_count(),
            'processing_files': self.get_processing_files_count()
        }

# Глобальный экземпляр трекера
stats_tracker = StatsTracker()
