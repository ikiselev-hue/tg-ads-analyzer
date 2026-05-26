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
# 2. КЛИЕНТ ДЛЯ РАБОТЫ С API TELEMETR.IO (ПОД ИСПРАВЛЕННУЮ ДОКУМЕНТАЦИЮ)
# =====================================================================
class TelemetrProductionAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key.strip() if api_key else None
        self.base_url = "https://api.telemetr.io/v1"
        
        # ИСПРАВЛЕНО: Строго по документации Telemetr передаем x-api-key
        self.headers = {
            "accept": "application/json",
            "x-api-key": self.api_key if self.api_key else ""
        }

    def fetch_dictionaries(self):
        """Возвращает справочники ГЕО (исправлено под формат API), языков и категорий"""
        # ИСПРАВЛЕНО: ГЕО переведены на полные английские названия согласно ответам из доков (india, russia, etc.)
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
            # ИСПРАВЛЕНО: дублируем параметры под разные версии поисковых эндпоинтов Telemetr для надежности
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
# 3. МОДУЛЬ ИИ И СКОРИНГА (ОСТАЛСЯ БЕЗ ИЗМЕНЕНИЙ)
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

def compute_mathematical_tier(row, limit_views, limit_er):
    if float(row.get('er', 0.0)) >= 10.0 and int(row.get('views', 0)) >= (limit_views * 1.5):
        return "Good", "Высокий ER и отличный охват постов."
    elif float(row.get('er', 0.0)) >= limit_er and int(row.get('views', 0)) >= limit_views:
        return "Medium", "Показатели стабильны и соответствуют критериям."
    else:
        return "Bad", "Низкий ER или охваты. Подозрение на ботов."

if "database_state" not in st.session_state:
    st.session_state.database_state = None

# --- ИНТЕРФЕЙС (САЙДБАР) ---
with st.sidebar:
    st.header("🔑 Конфигурация Доступов")
    with st.expander("Ввод приватных API токенов", expanded=True):
        input_telemetr_key = st.text_input("Telemetr API Токен", type="password")
        input_gemini_key = st.text_input("Google Gemini API Токен", type="password")
    
    st.markdown("---")
    st.header("🎯 Матрица Парсинга")
    api_engine = TelemetrProductionAPI(input_telemetr_key)
    schema_dicts = api_engine.fetch_dictionaries()
    
    ui_category = st.selectbox("Тематическая категория", schema_dicts["categories"])
    ui_geo = st.selectbox("ГЕО-локация", ["Собрать все доступные ГЕО"] + schema_dicts["geos"])
    ui_lang = st.selectbox("Язык каналов", ["Собрать все доступные языки"] + schema_dicts["languages"])
    
    st.markdown("---")
    st.header("📊 Фильтры качества")
    ui_min_subs = st.number_input("Подписчики от", value=5000, step=1000)
    ui_min_views = st.number_input("Просмотры от", value=1000, step=500)
    ui_min_er = st.slider("Минимальный ER %", min_value=0.0, max_value=100.0, value=5.0, step=0.5)

    st.markdown("---")
    st.header("🤖 Настройки Нейросети")
    ui_ai_active = st.checkbox("Активировать ИИ-скоринг контента", value=False)
    ui_product_desc = st.text_area("Описание вашего оффера:", value="Услуги по настройке Telegram Ads.")

    st.markdown("---")
    action_trigger = st.button("🚀 ЗАПУСТИТЬ АНАЛИЗ БАЗЫ", use_container_width=True, type="primary")

# --- ГЛАВНЫЙ ЭКРАН ---
st.title("🎯 Умный Сервис Подбора Таргетов Telegram Ads")

if action_trigger:
    with st.spinner("Запущен матричный сбор данных..."):
        geos_matrix = schema_dicts["geos"] if ui_geo == "Собрать все доступные ГЕО" else [ui_geo]
        langs_matrix = schema_dicts["languages"] if ui_lang == "Собрать все доступные языки" else [ui_lang]
        
        raw_aggregated_pool = []
        for current_geo in geos_matrix:
            for current_lang in langs_matrix:
                batch_data = api_engine.execute_matrix_parsing(geo=current_geo, lang=current_lang, category=ui_category)
                raw_aggregated_pool.extend(batch_data)
                
        if raw_aggregated_pool:
            processing_df = pd.DataFrame(raw_aggregated_pool)
            processing_df = processing_df.drop_duplicates(subset=["link"])
            processing_df = processing_df[
                (processing_df['subs'] >= ui_min_subs) & 
                (processing_df['views'] >= ui_min_views) & 
                (processing_df['er'] >= ui_min_er)
            ]
            
            if not processing_df.empty:
                tier_results = processing_df.apply(lambda row: compute_mathematical_tier(row, ui_min_views, ui_min_er), axis=1)
                processing_df['Score'] = [t[0] for t in tier_results]
                processing_df['Reason'] = [t[1] for t in tier_results]
                
                if ui_ai_active and input_gemini_key:
                    ai_scores, ai_verdicts, ai_banners = [], [], []
                    progress_ui_bar = st.progress(0, text="ИИ анализирует посты...")
                    total_records = len(processing_df)
                    
                   for index, record in enumerate(processing_df.itertuples()):
                        ai_data = run_gemini_intelligence(record.title, record.about, record.recent_posts, ui_product_desc, input_gemini_key)
                        ai_scores.append(ai_data.get("score", "5"))
                        ai_verdicts.append(ai_data.get("verdict", "—"))
                        ai_banners.append(ai_data.get("banner", "—"))
                        progress_ui_bar.progress((index + 1) / total_records, text=f"ИИ обработал: {index + 1}/{total_records}")
