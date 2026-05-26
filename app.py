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

    def execute_parsing(self, geo: str, lang: str, category: str, term: str, max_pages: int = 2):
        if not self.api_key:
            time.sleep(0.1)
            return [
                {"geo": geo, "lang": lang, "category": category, "title": "🚀 Демо Канал Рекламы", "link": "https://t.me/mock_1", "subs": 45000, "views": 8000, "er": 14.5, "about": "Тестовое описание.", "recent_posts": "Пост 1. Пост 2."},
                {"geo": geo, "lang": lang, "category": category, "title": "💰 Демо Инсайды Бизнеса", "link": "https://t.me/mock_2", "subs": 85000, "views": 9000, "er": 8.2, "about": "Аналитика ниши.", "recent_posts": "Кейс по таргету."}
            ]

        collected_channels = []
        page = 1
        limit_per_page = 20
        
        cat_map = {
            "Криптовалюта": "crypto", "Бизнес и стартапы": "business", "Финансы и инвестиции": "finance",
            "Ставки и беттинг": "betting", "Маркетинг и реклама": "marketing", "Блоги / Эксперты": "blogs",
            "Психология": "psychology", "Новостные каналы": "news"
        }
        
        # Исправлено: строго передаем 'country' и 'term' по требованию Кода 400
        query_params = {
            "page": page, 
            "limit": limit_per_page,
            "country": geo.lower()
        }
        
        if term.strip():
            query_params["term"] = term.strip()
        if category != "Все категории":
            query_params["category"] = cat_map.get(category, "crypto")
        if lang != "Все языки":
            query_params["language"] = lang.lower()

        while page <= max_pages:
            query_params["page"] = page
            try:
                response = requests.get(f"{self.base_url}/channels/search", headers=self.headers, params=query_params, timeout=20)
                
                if response.status_code != 200:
                    st.error(f"⛔️ Сигнал от Telemetr (Код {response.status_code}): {response.text}")
                    break
                
                payload = response.json()
                items = []
                
                if isinstance(payload, list): 
                    items = payload
                elif isinstance(payload, dict):
                    for k in ["channels", "data", "items", "result"]:
                        if k in payload:
                            items = payload[k]
                            break
                
                if not items: 
                    break
                
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
                
                if len(items) < limit_per_page: 
                    break
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

def compute_mathematical_tier(row, limit_views, limit_er):
    if float(row.get('er', 0.0)) >= 10.0 and int(row.get('views', 0)) >= (limit_views * 1.5): return "Good", "Высокий ER и охват."
    elif float(row.get('er', 0.0)) >= limit_er and int(row.get('views', 0)) >= limit_views: return "Medium", "Показатели в норме."
    return "Bad", "Низкие показатели."

if "database_state" not in st.session_state: st.session_state.database_state = None

with st.sidebar:
    st.header("🔑 Доступы")
    with st.expander("API Токены", expanded=True):
        input_telemetr_key = st.text_input("Telemetr API Токен", type="password")
        input_gemini_key = st.text_input("Gemini API Токен", type="password")
    
    st.markdown("---")
    st.header("🎯 Настройки")
    api_engine = TelemetrProductionAPI(input_telemetr_key)
    
    ui_term = st.text_input("Поисковое слово (Ключевик)", placeholder="Например: крипта (можно пусто ставить)")
    ui_category = st.selectbox("Категория", ["Все категории", "Криптовалюта", "Бизнес и стартапы", "Финансы и инвестиции", "Ставки и беттинг", "Маркетинг и реклама", "Блоги / Эксперты", "Психология", "Новостные каналы"])
    ui_geo = st.selectbox("ГЕО (Обязательно)", ["russia", "turkey", "india", "brazil", "usa", "uzbekistan", "kazakhstan"])
    ui_lang = st.selectbox("Язык", ["Все языки", "ru", "tr", "en", "uz", "kk"])
    
    st.markdown("---")
    ui_min_subs = st.number_input("Подписчики от", value=1000, step=500) 
    ui_min_views = st.number_input("Просмотры от", value=100, step=100)   
    ui_min_er = st.slider("Минимальный ER %", min_value=0.0, max_value=100.0, value=1.0, step=0.5)

    st.markdown("---")
    ui_ai_active = st.checkbox("Включить ИИ-анализ контента", value=False)
    ui_product_desc = st.text_area("Описание оффера:", value="Услуги по настройке Telegram Ads.")

    st.markdown("---")
    action_trigger = st.button("🚀 ЗАПУСТИТЬ АНАЛИЗ БАЗЫ", use_container_width=True, type="primary")

st.title("🎯 Умный Сервис Подбора Таргетов Telegram Ads")

if action_trigger:
    with st.spinner("Связь с сервером Telemetr..."):
        raw_pool = api_engine.execute_parsing(geo=ui_geo, lang=ui_lang, category=ui_category, term=ui_term)
                
        if raw_pool:
            processing_df = pd.DataFrame(raw_pool).drop_duplicates(subset=["link"])
            
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

if st.session_state.database_state is not None:
    df_act = st.session_state.database_state.copy()
    if df_act.empty:
        st.warning("⚠️ Каналов не найдено. На сервере пусто по этой связке параметров или ваши ползунки фильтров (подписчики/просмотры) слишком завышены.")
    else:
        total_len = len(df_act)
        good_len = len(df_act[df_act['Score'] == 'Good'])
        med_len = len(df_act[df_act['Score'] == 'Medium'])
        bad_len = len(df_act[df_act['Score'] == 'Bad'])

        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f"<div class='metric-box'>🛑 Всего таргетов<br><h2>{total_len}</h2></div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='metric-box'>🟢 Хороших (Good)<br><h2>{good_len}</h2></div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='metric-box'>🟡 Средних (Medium)<br><h2>{med_len}</h2></div>", unsafe_allow_html=True)
        with c4: st.markdown(f"<div class='metric-box'>🔴 Рискованных (Bad)<br><h2>{bad_len}</h2></div>", unsafe_allow_html=True)
            
        st.markdown("---")
        l1, l2, l3 = st.columns([2, 1, 1])
        with l1:
            query = st.text_input("🔍 Быстрый фильтр по названию:", "")
            if query: df_act = df_act[df_act['title'].str.contains(query, case=False)]
        with l2:
            st.download_button(label="📥 Экспорт в CSV", data=df_act.to_csv(index=False).encode('utf-8'), file_name="target.csv", mime="text/csv", use_container_width=True)
        with l3:
            buf = BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as w: df_act.to_excel(w, index=False, sheet_name='Таргеты')
            st.download_button(label="📥 Экспорт в Excel", data=buf.getvalue(), file_name="target.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            
        st.dataframe(
            df_act,
            column_config={
                "geo": st.column_config.TextColumn("ГЕО"), "lang": st.column_config.TextColumn("Язык"), "category": st.column_config.TextColumn("Категория"),
                "title": st.column_config.TextColumn("Название канала"), "link": st.column_config.LinkColumn("Ссылка (t.me)"),
                "subs": st.column_config.NumberColumn("Подписчики", format="%d"), "views": st.column_config.NumberColumn("Просмотры", format="%d"), "er": st.column_config.NumberColumn("ER (%)", format="%.2f%%"),
                "Score": st.column_config.SelectboxColumn("Оценка Системы", options=["Good", "Medium", "Bad"]), "Reason": st.column_config.TextColumn("Техническое Обоснование"),
                "AI Relevance": st.column_config.TextColumn("ИИ Релевантность (1-10)"), "AI Content Review": st.column_config.TextColumn("Смысловой ИИ-Анализ"), "AI Telegram Ads Banner": st.column_config.TextColumn("ИИ Креатив")
            },
            hide_index=True, use_container_width=True
        )
