import streamlit as st
import pandas as pd
import requests
import time
import json
import google.generativeai as genai
from io import BytesIO

st.set_page_config(layout="wide", page_title="Telemetr AI Parser", page_icon="🎯")

st.markdown("""
    <style>
    .metric-box { background-color: #1e222b; padding: 20px; border-radius: 8px; border: 1px solid #2d3139; text-align: center; }
    .stDataFrame { border: 1px solid #2d3139; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

class TelemetrProductionAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key.strip() if api_key else None
        self.base_url = "https://api.telemetr.io/v1"
        self.headers = {"accept": "application/json", "x-api-key": self.api_key if self.api_key else ""}

    def fetch_dictionaries(self):
        return {
            "categories": ["Криптовалюта", "Бизнес и стартапы", "Финансы и инвестиции", "Ставки и беттинг", "Маркетинг и реклама", "Блоги / Эксперты", "Психология", "Новостные каналы"],
            "geos": ["Russia", "Turkey", "India", "Brazil", "USA", "Uzbekistan", "Kazakhstan"],
            "languages": ["ru", "tr", "hi", "pt", "en", "uz", "kk"]
        }

    def execute_matrix_parsing(self, geo: str, lang: str, category: str, max_pages: int = 3):
        if not self.api_key:
            return self._execute_mock_simulation(geo, lang, category)

        collected_channels = []
        page = 1
        limit_per_page = 50
        cat_map = {
            "Криптовалюта": "crypto", "Бизнес и стартапы": "business", "Финансы и инвестиции": "finance",
            "Ставки и беттинг": "betting", "Маркетинг и реклама": "marketing", "Блоги / Эксперты": "blogs",
            "Психология": "psychology", "Новостные каналы": "news"
        }
        api_category = cat_map.get(category, "crypto")

        while page <= max_pages:
            query_params = {
                "country_id": geo.lower(), "geo": geo.lower(), "lang": lang.lower(),
                "language": lang.lower(), "category": api_category, "page": page, "limit": limit_per_page
            }
            try:
                response = requests.get(f"{self.base_url}/channels/search", headers=self.headers, params=query_params, timeout=20)
                if response.status_code == 429:
                    time.sleep(4)
                    continue
                elif response.status_code == 401:
                    st.sidebar.error("❌ Неверный API ключ Telemetr.io")
                    break
                elif response.status_code != 200:
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
                        "geo": geo, "lang": lang, "category": category,
                        "title": item.get("title", "Без названия"),
                        "link": item.get("link") or f"https://t.me/{item.get('username', '')}",
                        "subs": int(item.get("participants_count") or item.get("subs", 0)),
                        "views": int(item.get("views_per_post") or item.get("views", 0)),
                        "er": float(item.get("er") or 0.0),
                        "about": item.get("about", "Описание отсутствует"),
                        "recent_posts": " | ".join([p.get("text", "") for p in item.get("recent_posts", [])[:3]]) or "Контент недоступен"
                    })
                if len(items) < limit_per_page: break
                page += 1
                time.sleep(0.5)
            except:
                break
        return collected_channels

    def _execute_mock_simulation(self, geo, lang, category):
        time.sleep(0.1)
        return [
            {"geo": geo, "lang": lang, "category": category, "title": f"🚀 {category} | Channel {geo}", "link": f"https://t.me/mock_1", "subs": 45000, "views": 8000, "er": 14.5, "about": "Блог эксперта.", "recent_posts": "Пост 1. Пост 2."},
            {"geo": geo, "lang": lang, "category": category, "title": f"💰 Инсайды [{category}]", "link": f"https://t.me/mock_2", "subs": 85000, "views": 9000, "er": 8.2, "about": "Аналитика ниши.", "recent_posts": "Кейс по таргету."}
        ]

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

def compute_mathematical_tier(row, limit_views, limit_er):
    if float(row.get('er', 0.0)) >= 10.0 and int(row.get('views', 0)) >= (limit_views * 1.5): return "Good", "Высокий ER и охват."
    elif float(row.get('er', 0.0)) >= limit_er and int(row.get('views', 0)) >= limit_views: return "Medium", "Показатели в норме."
    return "Bad", "Низкие показатели."

if "database_state" not in st.session_state: st.session_state.database_state = None
if "diagnostic_info" not in st.session_state: st.session_state.diagnostic_info = ""

with st.sidebar:
    st.header("🔑 Доступы")
    with st.expander("API Токены", expanded=True):
        input_telemetr_key = st.text_input("Telemetr API Токен", type="password")
        input_gemini_key = st.text_input("Gemini API Токен", type="password")
    
    st.markdown("---")
    st.header("🎯 Настройки")
    api_engine = TelemetrProductionAPI(input_telemetr_key)
    schema_dicts = api_engine.fetch_dictionaries()
    
    ui_category = st.selectbox("Категория", schema_dicts["categories"])
    ui_geo = st.selectbox("ГЕО", ["Собрать все доступные ГЕО"] + schema_dicts["geos"])
    ui_lang = st.selectbox("Язык", ["Собрать все доступные языки"] + schema_dicts["languages"])
    
    st.markdown("---")
    ui_min_subs = st.number_input("Подписчики от", value=5000, step=1000)
    ui_min_views = st.number_input("Просмотры от", value=1000, step=500)
    ui_min_er = st.slider("Минимальный ER %", min_value=0.0, max_value=100.0, value=5.0, step=0.5)

    st.markdown("---")
    ui_ai_active = st.checkbox("Включить ИИ-анализ контента", value=False)
    ui_product_desc = st.text_area("Описание оффера:", value="Услуги по настройке Telegram Ads.")

    st.markdown("---")
    action_trigger = st.button("🚀 ЗАПУСТИТЬ АНАЛИЗ БАЗЫ", use_container_width=True, type="primary")

st.title("🎯 Умный Сервис Подбора Таргетов Telegram Ads")

if action_trigger:
    st.session_state.diagnostic_info = ""
    with st.spinner("Сбор данных..."):
        geos_matrix = schema_dicts["geos"] if ui_geo == "Собрать все доступные ГЕО" else [ui_geo]
        langs_matrix = schema_dicts["languages"] if ui_lang == "Собрать все доступные языки" else [ui_lang]
        
        raw_pool = []
        for cg in geos_matrix:
            for cl in langs_matrix:
                raw_pool.extend(api_engine.execute_matrix_parsing(geo=cg, lang=cl, category=ui_category))
                
        if raw_pool:
            processing_df = pd.DataFrame(raw_pool).drop_duplicates(subset=["link"])
            st.session_state.diagnostic_info = f"🔌 Диагностика: Из Telemetr загружено {len(processing_df)} каналов. Фильтруем..."
            
            processing_df = processing_df[
                (processing_df['subs'] >= ui_min_subs) & (processing_df['views'] >= ui_min_views) & (processing_df['er'] >= ui_min_er)
            ]
            
            if not processing_df.empty:
                tiers = processing_df.apply(lambda r: compute_mathematical_tier(r, ui_min_views, ui_min_er), axis=1)
                processing_df['Score'] = [t[0] for t in tiers]
                processing_df['Reason'] = [t[1] for t in tiers]
                
                if ui_ai_active and input_gemini_key:
                    ai_scores, ai_verdicts, ai_banners = [], [], []
                    p_bar = st.progress(0, text="ИИ работает...")
                    total = len(processing_df)
                    
                    for idx, rec in enumerate(processing_df.itertuples()):
                        ai_data = run_gemini_intelligence(rec.title, rec.about, rec.recent_posts, ui_product_desc, input_gemini_key)
                        ai_scores.append(ai_data.get("score", "5"))
                        ai_verdicts.append(ai_data.get("verdict", "—"))
                        ai_banners.append(ai_data.get("banner", "—"))
                        p_bar.progress((idx + 1) / total, text=f"ИИ обработал: {idx + 1}/{total}")
                    
                    processing_df['AI Relevance'] = ai_scores
                    processing_df['AI Content Review'] = ai_verdicts
                    processing_df['AI Telegram Ads Banner'] = ai_banners
                    p_bar.empty()
                else:
                    processing_df['AI Relevance'], processing_df['AI Content Review'], processing_df['AI Telegram Ads Banner'] = "Выключен", "Включите ИИ слева", "—"
                st.session_state.database_state = processing_df
            else:
                st.session_state.database_state = pd.DataFrame()
        else:
            st.session_state.database_state = pd.DataFrame()
            st.session_state.diagnostic_info = "🔌 Диагностика: Сервер Telemetr вернул пустой список. Проверьте ГЕО/ключ."

if st.session_state.diagnostic_info:
    st.info(st.session_state.diagnostic_info)

if st.session_state.database_state is not None:
    df_act = st.session_state.database_state.copy()
    if df_act.empty:
        st.warning("⚠️ Каналов не найдено. Снизьте фильтры подписчиков, просмотров или ER.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f"<div class='metric-box'>🛑 Всего таргетов<br><h2>{len(df_act
