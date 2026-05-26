import streamlit as st
import pandas as pd
import requests
import time
import json
import google.generativeai as genai
from io import BytesIO

st.set_page_config(layout="wide", page_title="Telemetr PRO Parser", page_icon="🎯")

st.markdown("""
    <style>
    .metric-box { background-color: #1e222b; padding: 15px; border-radius: 8px; border: 1px solid #2d3139; text-align: center; }
    .stDataFrame { border: 1px solid #2d3139; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

class TelemetrProductionAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key.strip() if api_key else None
        self.base_url = "https://api.telemetr.io/v1"
        self.headers = {"accept": "application/json", "x-api-key": self.api_key if self.api_key else ""}

    def execute_parsing(self, params_dict: dict, max_pages: int = 2):
        if not self.api_key:
            time.sleep(0.1)
            return [
                {"geo": params_dict.get("country", "russia"), "lang": "ru", "category": "Бизнес", "title": "🚀 Тестовый Мега-Канал", "link": "https://t.me/mock_1", "subs": 75000, "views": 12000, "er": 15.5, "growth_24h": 450, "ads_index": 82, "about": "Описание.", "recent_posts": "Посты канала."},
                {"geo": params_dict.get("country", "russia"), "lang": "ru", "category": "Бизнес", "title": "💰 Тестовый Инсайд", "link": "https://t.me/mock_2", "subs": 120000, "views": 8500, "er": 6.2, "growth_24h": -120, "ads_index": 45, "about": "Аналитика ниши.", "recent_posts": "Рекламный контент."}
            ]

        collected_channels = []
        page = 1
        limit_per_page = 20
        
        while page <= max_pages:
            params_dict["page"] = page
            params_dict["limit"] = limit_per_page
            try:
                response = requests.get(f"{self.base_url}/channels/search", headers=self.headers, params=params_dict, timeout=20)
                if response.status_code != 200:
                    st.error(f"⛔️ Ошибка Telemetr ({response.status_code}): {response.text}")
                    break
                
                payload = response.json()
                items = []
                if isinstance(payload, list): items = payload
                elif isinstance(payload, dict):
                    for k in ["channels", "data", "items", "result"]:
                        if k in payload:
                            items = payload[k]
                            break
                
                if not items: break
                
                for item in items:
                    collected_channels.append({
                        "geo": params_dict.get("country", "—"),
                        "lang": item.get("language") or item.get("lang") or "—",
                        "category": item.get("category") or "—",
                        "title": item.get("title", "Без названия"),
                        "link": item.get("link") or f"https://t.me/{item.get('username', '')}",
                        "subs": int(item.get("participants_count") or item.get("subs", 0)),
                        "views": int(item.get("views_per_post") or item.get("views", 0)),
                        "er": float(item.get("er") or 0.0),
                        "growth_24h": int(item.get("growth_24h") or item.get("growth", 0)),
                        "ads_index": int(item.get("ads_index") or item.get("members_ads_count", 0)),
                        "about": item.get("about", "Описание отсутствует"),
                        "recent_posts": " | ".join([p.get("text", "") for p in item.get("recent_posts", [])[:3]]) or "Контент недоступен"
                    })
                if len(items) < limit_per_page: break
                page += 1
                time.sleep(0.5)
            except Exception as e:
                st.error(f"💥 Ошибка кода: {str(e)}")
                break
        return collected_channels

def run_gemini_intelligence(title, about, posts, product_info, api_key):
    if not api_key: return {"score": "5", "verdict": "Демо-режим", "banner": "—"}
    try:
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Ты аналитик Telegram Ads. Продукт: '{product_info}'. Канал: {title}. Био: {about}. Посты: {posts}. Верни СТРОГО JSON: {{\"score\": \"1-10\", \"verdict\": \"текст\", \"banner\": \"текст до 160 симв\"}}"
        response = model.generate_content(prompt)
        sanitized = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(sanitized)
    except:
        return {"score": "5", "verdict": "Ошибка ИИ", "banner": "—"}

if "database_state" not in st.session_state: st.session_state.database_state = None

# --- ПОДГОТОВКА ПОЛНЫХ СПРАВОЧНИКОВ СЛОВАРЕЙ ---
CATEGORIES_LIST = ["Все категории", "Криптовалюта", "Бизнес и стартапы", "Финансы и инвестиции", "Маркетинг и реклама", "Блоги / Эксперты", "Новостные каналы", "Юмор и развлечения", "Технологии и софт", "Образование и наука", "Кино и книги", "Музыка", "Спорт", "Мода и стиль", "Еда и кулинария", "Психология", "Ставки и беттинг"]
GEOS_LIST = ["russia", "turkey", "india", "brazil", "usa", "uzbekistan", "kazakhstan", "belarus", "ukraine", "germany", "france", "indonesia", "united_arab_emirates"]
LANGS_LIST = ["Все языки", "ru", "tr", "en", "hi", "pt", "uz", "kk", "be", "uk", "de", "fr", "id", "ar"]

cat_map = {"Криптовалюта": "crypto", "Бизнес и стартапы": "business", "Финансы и инвестиции": "finance", "Маркетинг и реклама": "marketing", "Блоги / Эксперты": "blogs", "Новостные каналы": "news", "Юмор и развлечения": "humor", "Технологии и софт": "tech", "Образование и наука": "education", "Ставки и беттинг":
