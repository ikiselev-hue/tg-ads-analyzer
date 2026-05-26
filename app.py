import streamlit as st
import pandas as pd
import requests
import time
import json
import google.generativeai as genai
from io import BytesIO

# =====================================================================
# 1. СИСТЕМНЫЕ НАСТРОЙКИ И СТИЛИЗАЦИЯ ИНТЕРФЕЙСА
# =====================================================================
st.set_page_config(
    layout="wide", 
    page_title="Telemetr AI Professional Parser", 
    page_icon="🎯"
)

# Кастомные стили для темной темы админки
st.markdown("""
    <style>
    .metric-box {
        background-color: #1e222b;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #2d3139;
        text-align: center;
    }
    .stDataFrame {
        border: 1px solid #2d3139;
        border-radius: 8px;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #2d3139 !important;
        border-radius: 8px !important;
    }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. КЛИЕНТ ДЛЯ РАБОТЫ С API TELEMETR.IO
# =====================================================================
class TelemetrProductionAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key.strip() if api_key else None
        self.base_url = "https://api.telemetr.io/v1"
        
        # Передаем авторизацию строго по документации Telemetr через x-api-key
        self.headers = {
            "accept": "application/json",
            "x-api-key": self.api_key if self.api_key else ""
        }

    def fetch_dictionaries(self):
        """Возвращает справочники ГЕО, языков и категорий"""
        return {
            "categories": ["Криптовалюта", "Бизнес и стартапы", "Финансы и инвестиции", "Ставки и беттинг", "Маркетинг и реклама", "Блоги / Эксперты", "Психология", "Новостные каналы"],
            "geos": ["Russia", "Turkey", "India", "Brazil", "USA", "Uzbekistan", "Kazakhstan"],
            "languages": ["ru", "tr", "hi", "pt", "en", "uz", "kk"]
        }

    def execute_matrix_parsing(self, geo: str, lang: str, category: str, max_pages: int = 5):
        """Потоковый сбор данных из Telemetr по связке параметров"""
        if not self.api_key:
            return self._execute_mock_simulation(geo, lang, category)

        collected_channels = []
        page = 1
        limit_per_page = 50

        category_mapping = {
            "Криптовалюта": "crypto", "Бизнес и стартапы": "business", "Финансы и инвестиции": "finance",
            "Ставки и беттинг": "betting", "Маркетинг и реклама": "marketing", "Блоги / Эксперты": "blogs",
            "Психология": "psychology", "Новостные каналы": "news"
        }
        api_category = category_mapping.get(category, "crypto")

        while page <= max_pages:
            query_params = {
                "country_id": geo.lower(),
                "geo": geo.lower(),
                "lang": lang.lower(),
                "language": lang.lower(),
                "category": api_category,
                "page": page,
                "limit": limit_per_page
            }
            
            try:
                response = requests.get(
                    f"{self.base_url}/channels/search", 
                    headers=self.headers, 
                    params=query_params, 
                    timeout=20
                )
                
                if response.status_code == 429:
                    time.sleep(4)
                    continue
                elif response.status_code == 401:
                    st.sidebar.error("❌ Ошибка авторизации: Проверьте ваш x-api-key!")
                    break
                elif response.status_code != 200:
                    break
                
                payload = response.json()
                items = payload.get("channels", [])
                
                if not items:
                    break
                
                for item in items:
                    collected_channels.append({
                        "geo": geo,
                        "lang": lang,
                        "category": category,
                        "title": item.get("title", "Без названия"),
                        "link": item.get("link") or f"https://t.me/{item.get('username', '')}",
                        "subs": int(item.get("participants_count") or item.get("subs", 0)),
                        "views": int(item.get("views_per_post") or item.get("views", 0)),
                        "er": float(item.get("er") or 0.0),
                        "about": item.get("about", "Описание отсутствует"),
                        "recent_posts": " | ".join([p.get("text", "") for p in item.get("recent_posts", [])[:3]]) or "Контент постов недоступен"
                    })
                
                if len(items) < limit_per_page:
                    break
                    
                page += 1
                time.sleep(0.5)
                
            except Exception as ex:
                st.sidebar.error(f"Сбой транспорта API: {str(ex)}")
                break

        return collected_channels

    def _execute_mock_simulation(self, geo, lang, category):
        """Локальный симулятор для демонстрационного режима"""
        time.sleep(0.1)
        return [
            {
                "geo": geo, "lang": lang, "category": category,
                "title": f"🚀 {category} | Channel {geo}",
                "link": f"https://t.me/mock_channel_{geo.lower()}_1",
                "subs": 48200, "views": 7600, "er": 15.8,
                "about": f"Ресурс по теме {category} на рынке ГЕО: {geo}.",
                "recent_posts": "Пост 1: Аналитика рынка. Пост 2: Срочные новости рекламы."
            },
            {
                "geo": geo, "lang": lang, "category": category,
                "title": f"💰 Инсайды [{category}]",
                "link": f"https://t.me/mock_channel_{geo.lower()}_2",
                "subs": 124000, "views": 11300, "er": 9.1,
                "about": "Закрытые разборы и статистика для закупщиков.",
                "recent_posts": "Пост 1: Новый кейс масштабирования. Пост 2: Прогнозы трендов."
            }
        ]

# =====================================================================
# 3. МОДУЛЬ ИСКУССТВЕННОГО ИНТЕЛЛЕКТА (GEMINI API)
# =====================================================================
def run_gemini_intelligence(title, about, posts, product_info, api_key):
    if not api_key:
        return {"score": "5", "verdict": "Демо-режим: укажите ключ Gemini.", "banner": "—"}
    try:
        genai.configure(api_key=api_key.strip())
        ai_engine = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Ты — аналитик Telegram Ads. Проанализируй канал. Продукт: "{product_info}"
        Канал: {title}. Описание: {about}. Посты: {posts}
        Верни ответ строго в формате JSON:
        {{"score": "от 1 до 10", "verdict": "пояснение на русском", "banner": "текст объявления до 160 симв"}}
        """
        response = ai_engine.generate_content(prompt)
        sanitized = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(sanitized)
    except:
        return {"score": "5", "verdict": "Ошибка обработки ИИ", "banner": "—"}

# =====================================================================
# 4. МАТЕМАТИЧЕСКИЙ СКОРИНГ
# =====================================================================
def compute_mathematical_tier(row, limit_views, limit_er):
    if float(row.get('er', 0.0)) >= 10.0 and int(row.get('views', 0)) >= (limit_views * 1.5):
        return "Good", "Высокий ER и отличный охват постов."
    elif float(row.get('er', 0.0)) >= limit_er and int(row.get('views', 0)) >= limit_views:
        return "Medium", "Показатели стабильны и соответствуют критериям."
    else:
        return "Bad", "Низкий ER или охваты. Подозрение на ботов."

# Инициализация состояния базы данных
if "database_state" not in st.
