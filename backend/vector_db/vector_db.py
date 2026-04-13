"""
Модуль для работы с векторной базой данных
Использует ChromaDB для хранения и поиска векторных представлений постов
"""

import os
import chromadb
from pathlib import Path
from sentence_transformers import SentenceTransformer


class VectorDB:
    """Класс для работы с векторной базой данных постов"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            # Инициализация модели для создания эмбеддингов
            # Используем легкую модель для русского и английского языков
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            
            # Путь к базе данных
            project_root = Path(__file__).resolve().parent.parent.parent
            db_path = project_root / 'data' / 'vector_db'
            db_path.mkdir(parents=True, exist_ok=True)
            
            # Инициализация ChromaDB
            self.client = chromadb.PersistentClient(path=str(db_path))
            
            # Получаем или создаем коллекцию для постов
            self.posts_collection = self.client.get_or_create_collection(
                name="posts",
                metadata={"hnsw:space": "cosine"}  # Косинусное расстояние для похожести
            )
            
            self._initialized = True
    
    def add_post(self, post_id: int, title: str, content: str, author: str):
        """Добавляет пост в векторную базу"""
        # Создаем текстовое представление для векторизации
        text = f"{title} {content}"
        
        # Генерируем эмбеддинг
        embedding = self.model.encode(text).tolist()
        
        # Добавляем в коллекцию
        self.posts_collection.upsert(
            ids=[str(post_id)],
            embeddings=[embedding],
            metadatas=[{
                "title": title,
                "author": author,
                "content_preview": content[:200]  # Первые 200 символов
            }]
        )
    
    def update_post(self, post_id: int, title: str, content: str, author: str):
        """Обновляет пост в векторной базе"""
        # Удаляем старую запись
        self.posts_collection.delete(ids=[str(post_id)])
        # Добавляем обновленную
        self.add_post(post_id, title, content, author)
    
    def delete_post(self, post_id: int):
        """Удаляет пост из векторной базы"""
        self.posts_collection.delete(ids=[str(post_id)])
    
    def search_posts(self, query: str, n_results: int = 10):
        """Ищет похожие посты по запросу"""
        # Генерируем эмбеддинг для запроса
        query_embedding = self.model.encode(query).tolist()
        
        # Ищем в коллекции
        results = self.posts_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["metadatas", "distances"]
        )
        
        # Форматируем результаты
        posts = []
        if results['ids'] and results['ids'][0]:
            for i, post_id in enumerate(results['ids'][0]):
                posts.append({
                    'id': int(post_id),
                    'title': results['metadatas'][0][i]['title'],
                    'author': results['metadatas'][0][i]['author'],
                    'content_preview': results['metadatas'][0][i]['content_preview'],
                    'distance': results['distances'][0][i]
                })
        
        return posts
    
    def get_all_post_ids(self):
        """Возвращает все ID постов в базе"""
        return self.posts_collection.get()['ids']
    
    def sync_post(self, post_id: int, title: str, content: str, author: str):
        """Синхронизирует пост: добавляет если нет, обновляет если есть"""
        existing_ids = self.get_all_post_ids()
        if str(post_id) in existing_ids:
            self.update_post(post_id, title, content, author)
        else:
            self.add_post(post_id, title, content, author)


# Глобальный экземпляр
vector_db = VectorDB()
