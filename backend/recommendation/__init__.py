"""
Модуль рекомендаций для бесконечной ленты (Infinite Scroll).

Алгоритм по спецификации из task.txt:
1. Загрузка и валидация конфигурации из config.json
2. Сбор взаимодействий в два независимых FIFO-буфера (Alpha / Beta)
3. Расчёт векторов профиля через взвешенное усреднение
4. Вероятностный выбор целевого вектора (Alpha / Beta / Random)
5. Фильтрация кандидатов: cosine_distance(post_vector, target) < TBM
6. Выбор поста с вероятностью, пропорциональной sqrt(likes_count)
"""

import json
import math
import random
from pathlib import Path
from typing import Optional

import numpy as np

from backend.database import db_session
from backend.database.models.posts_model import PostModel
from backend.vector_db.vector_db import VectorDB


# ============================================================
# 1. КОНФИГУРАЦИЯ
# ============================================================

class RecommendationConfig:
    """Загружает и валидирует параметры из config.json."""

    REQUIRED_INT_FIELDS = ('DR', 'DL', 'DS', 'alpha_N', 'beta_N')
    REQUIRED_FLOAT_FIELDS = ('alphaPerc', 'betaPerc', 'randPerc', 'TBM')

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).resolve().parent / 'config.json'

        with open(config_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)

        self._validate(raw)

        self.DR = int(raw['DR'])
        self.DL = int(raw['DL'])
        self.DS = int(raw['DS'])
        self.alpha_N = int(raw['alpha_N'])
        self.beta_N = int(raw['beta_N'])
        self.alphaPerc = float(raw['alphaPerc'])
        self.betaPerc = float(raw['betaPerc'])
        self.randPerc = float(raw['randPerc'])
        self.TBM = float(raw['TBM'])

    @classmethod
    def _validate(cls, raw: dict):
        """Валидирует наличие, типы и ограничения всех полей."""
        # Проверка наличия
        all_required = list(cls.REQUIRED_INT_FIELDS) + list(cls.REQUIRED_FLOAT_FIELDS)
        missing = [k for k in all_required if k not in raw]
        if missing:
            raise ValueError(
                f"Config is missing required fields: {missing}"
            )

        # Проверка целочисленных полей
        for key in cls.REQUIRED_INT_FIELDS:
            val = raw[key]
            if not isinstance(val, int):
                raise TypeError(
                    f"Config field '{key}' must be int, got {type(val).__name__} (value={val})"
                )

        # Проверка вещественных полей и их диапазона [0.0, 1.0]
        for key in cls.REQUIRED_FLOAT_FIELDS:
            val = raw[key]
            if not isinstance(val, (int, float)):
                raise TypeError(
                    f"Config field '{key}' must be float, got {type(val).__name__} (value={val})"
                )
            if not (0.0 <= val <= 1.0):
                raise ValueError(
                    f"Config field '{key}' must be in [0.0, 1.0], got {val}"
                )

        # Строгая проверка суммы вероятностей
        total = raw['alphaPerc'] + raw['betaPerc'] + raw['randPerc']
        if not math.isclose(total, 1.0, rel_tol=1e-9):
            raise ValueError(
                f"alphaPerc + betaPerc + randPerc must equal 1.0 exactly, "
                f"got {raw['alphaPerc']} + {raw['betaPerc']} + {raw['randPerc']} = {total}"
            )


# ============================================================
# 2. БУФЕР ВЗАИМОДЕЙСТВИЙ (FIFO / sliding window)
# ============================================================

class InteractionBuffer:
    """
    Буфер фиксированного размера для хранения пар:
        (семантический_вектор_поста, очки_взаимодействия)

    Поведение: FIFO (sliding window). При добавлении в полный буфер
    самый старый элемент удаляется.
    """

    def __init__(self, max_size: int):
        if max_size < 0:
            raise ValueError(f"Buffer size must be >= 0, got {max_size}")
        self.max_size = max_size
        self._vectors: list = []   # numpy-векторы
        self._scores: list = []    # очки взаимодействия (int)

    def add(self, vector: np.ndarray, score: int):
        """Добавляет пару (вектор, очки). При переполнении удаляет старейший элемент."""
        if self.max_size <= 0:
            return
        if len(self._vectors) >= self.max_size:
            self._vectors.pop(0)
            self._scores.pop(0)
        self._vectors.append(np.array(vector, dtype=np.float64))
        self._scores.append(int(score))

    @property
    def is_empty(self) -> bool:
        return len(self._vectors) == 0

    @property
    def size(self) -> int:
        return len(self._vectors)

    def compute_profile_vector(self) -> np.ndarray:
        """
        Вычисляет вектор профиля строго по алгоритму из ТЗ:

        1. Расширенный массив: каждый вектор повторяется ровно score раз.
        2. Поэлементное арифметическое усреднение.

        Используется математически эквивалентная оптимизация:
            Σ(vector_i * score_i) / Σ(score_i)

        Это даёт полностью идентичный результат без создания гигантских массивов.
        Если буфер пуст — возвращает нулевой вектор.
        """
        if self.is_empty:
            return np.array([])

        weighted_sum = np.zeros_like(self._vectors[0], dtype=np.float64)
        total_score = 0

        for vec, score in zip(self._vectors, self._scores):
            weighted_sum += vec * score
            total_score += score

        if total_score == 0:
            return np.zeros_like(self._vectors[0], dtype=np.float64)

        return (weighted_sum / total_score).astype(np.float64)


# ============================================================
# 3. ДВИЖОК РЕКОМЕНДАЦИЙ
# ============================================================

class RecommendationEngine:
    """
    Основной движок системы рекомендаций.

    Хранит буферы Alpha и Beta для каждого пользователя в оперативной памяти.
    Для продакшена потребуется персистентное хранилище (Redis / БД).
    """

    def __init__(self, config: Optional[RecommendationConfig] = None):
        self.config = config or RecommendationConfig()
        self.vector_db = VectorDB()

        # Состояние буферов: { user_id: {'alpha': InteractionBuffer, 'beta': InteractionBuffer} }
        self._user_buffers: dict = {}

    # ─── Управление буферами ──────────────────────────

    def _ensure_buffers(self, user_id: int):
        """Создаёт буферы для пользователя, если их ещё нет."""
        if user_id not in self._user_buffers:
            self._user_buffers[user_id] = {
                'alpha': InteractionBuffer(self.config.alpha_N),
                'beta': InteractionBuffer(self.config.beta_N),
            }

    def record_interaction(self, user_id: int, post_id: int, action: str):
        """
        Записывает взаимодействие в оба буфера (Alpha и Beta).

        action: 'read', 'like', 'favorite'
        """
        score_map = {
            'read': self.config.DR,
            'like': self.config.DL,
            'favorite': self.config.DS,
        }
        score = score_map.get(action)
        if score is None:
            return

        vector = self._get_post_vector(post_id)
        if vector is None or vector.size == 0:
            return

        self._ensure_buffers(user_id)
        self._user_buffers[user_id]['alpha'].add(vector, score)
        self._user_buffers[user_id]['beta'].add(vector, score)

    def _get_post_vector(self, post_id: int) -> Optional[np.ndarray]:
        """Извлекает вектор поста из ChromaDB."""
        try:
            result = self.vector_db.posts_collection.get(
                ids=[str(post_id)],
                include=['embeddings']
            )
            if result['ids'] and result['embeddings']:
                return np.array(result['embeddings'][0], dtype=np.float64)
        except Exception:
            pass
        return None

    # ─── Векторы профиля ─────────────────────────────

    def compute_profile_vectors(self, user_id: int) -> tuple:
        """
        Возвращает (vector_alpha, vector_beta).
        Пустой буфер → нулевой вектор соответствующей размерности.
        """
        self._ensure_buffers(user_id)
        buffers = self._user_buffers[user_id]
        return (
            buffers['alpha'].compute_profile_vector(),
            buffers['beta'].compute_profile_vector(),
        )

    # ─── Выбор целевого вектора ──────────────────────

    def _choose_target_vector(
        self,
        vector_alpha: np.ndarray,
        vector_beta: np.ndarray,
    ) -> np.ndarray:
        """
        Вероятностный выбор целевого вектора:
        - alphaPerc → vector_alpha
        - betaPerc  → vector_beta
        - randPerc  → вектор случайного поста с весом sqrt(likes_count)
        """
        r = random.random()

        if r < self.config.alphaPerc:
            return vector_alpha
        elif r < self.config.alphaPerc + self.config.betaPerc:
            return vector_beta
        else:
            return self._get_random_weighted_vector()

    def _get_random_weighted_vector(self) -> np.ndarray:
        """
        Выбирает случайный пост из всей базы.
        Вероятность выбора ∝ sqrt(likes_count + 1).  (+1 — защита от нуля)
        """
        db_sess = db_session.create_session()
        try:
            posts = db_sess.query(PostModel).all()
            if not posts:
                return np.array([])

            weights = [math.sqrt(max(0, p.likes_count or 0) + 1) for p in posts]
            total = sum(weights)
            if total == 0:
                return np.array([])

            probs = [w / total for w in weights]
            chosen = random.choices(posts, weights=probs, k=1)[0]

            vector = self._get_post_vector(chosen.id)
            return vector if (vector is not None and vector.size > 0) else np.array([])
        finally:
            db_sess.close()

    # ─── Косинусное расстояние ──────────────────────

    @staticmethod
    def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
        """
        Косинусное расстояние: 1 − cos(a,b).
        Для пустых/нулевых векторов возвращает 1.0 (максимальное расстояние).
        """
        if a.size == 0 or b.size == 0:
            return 1.0
        norm_a = float(np.linalg.norm(a))
        norm_b = float(np.linalg.norm(b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 1.0
        return 1.0 - float(np.dot(a, b) / (norm_a * norm_b))

    # ─── Основной метод: получить один пост ──────────

    def get_feed_post(self, user_id: int, exclude_ids: set) -> Optional[dict]:
        """
        Выполняет один цикл рекомендации (шаги 3–5 из ТЗ):

        1. Вычисляет vector_alpha, vector_beta.
        2. Выбирает целевой вектор (Alpha / Beta / Random).
        3. Фильтрует: cosine_distance < TBM.
        4. Выбирает один пост с вероятностью ∝ sqrt(likes_count).
        5. Fallback при отсутствии кандидатов — случайный пост.

        exclude_ids — ID уже показанных постов в текущем батче.
        """
        vector_alpha, vector_beta = self.compute_profile_vectors(user_id)
        target = self._choose_target_vector(vector_alpha, vector_beta)

        if target.size == 0:
            return self._fallback_random_post(exclude_ids)

        return self._select_candidate(target, exclude_ids)

    def _select_candidate(
        self, target: np.ndarray, exclude_ids: set
    ) -> Optional[dict]:
        """
        Отбирает посты с cosine_distance(vector, target) < TBM
        и выбирает один случайно с весом sqrt(likes_count).
        """
        db_sess = db_session.create_session()
        try:
            all_posts = db_sess.query(PostModel).all()
            candidates = []
            weights = []

            for post in all_posts:
                if post.id in exclude_ids:
                    continue
                vector = self._get_post_vector(post.id)
                if vector is None or vector.size == 0:
                    continue
                if self.cosine_distance(vector, target) < self.config.TBM:
                    candidates.append(post)
                    weights.append(math.sqrt(max(0, post.likes_count or 0) + 1))

            if not candidates:
                return self._fallback_random_post(exclude_ids, db_sess)

            total = sum(weights)
            if total == 0:
                chosen = random.choice(candidates)
            else:
                probs = [w / total for w in weights]
                chosen = random.choices(candidates, weights=probs, k=1)[0]

            return self._post_to_dict(chosen)
        finally:
            db_sess.close()

    def _fallback_random_post(
        self, exclude_ids: set, db_sess=None
    ) -> Optional[dict]:
        """Fallback: случайный пост с весом sqrt(likes_count) из всей базы."""
        close_sess = False
        if db_sess is None:
            db_sess = db_session.create_session()
            close_sess = True
        try:
            posts = [p for p in db_sess.query(PostModel).all()
                     if p.id not in exclude_ids]
            if not posts:
                return None

            weights = [math.sqrt(max(0, p.likes_count or 0) + 1) for p in posts]
            total = sum(weights)
            if total == 0:
                chosen = random.choice(posts)
            else:
                probs = [w / total for w in weights]
                chosen = random.choices(posts, weights=probs, k=1)[0]

            return self._post_to_dict(chosen)
        finally:
            if close_sess:
                db_sess.close()

    @staticmethod
    def _post_to_dict(post: PostModel) -> dict:
        """Сериализует PostModel в словарь для JSON-ответа."""
        return {
            'id': post.id,
            'title': post.title or 'Без заголовка',
            'content': post.content[:200] + ('...' if len(post.content) > 200 else ''),
            'author': post.author,
            'user_id': post.user_id,
            'likes_count': post.likes_count,
            'created_at': post.created_at.isoformat() if post.created_at else None,
        }

    # ─── Пакетная генерация ленты ───────────────────

    def generate_feed_batch(
        self, user_id: int, batch_size: int = 10,
        initial_exclude_ids: set = None
    ) -> list:
        """
        Генерирует батч постов для infinite scroll.
        В рамках одного батча посты не дублируются.

        initial_exclude_ids — ID постов, уже показанных клиенту в предыдущих батчах.
        """
        posts = []
        exclude_ids: set = initial_exclude_ids.copy() if initial_exclude_ids else set()
        max_attempts = batch_size * 5  # предохранитель от бесконечного цикла

        for _ in range(max_attempts):
            if len(posts) >= batch_size:
                break
            post = self.get_feed_post(user_id, exclude_ids)
            if post is None:
                break
            exclude_ids.add(post['id'])
            posts.append(post)

        return posts


# Глобальный экземпляр движка (синглтон)
engine = RecommendationEngine()
