import streamlit as st
import pandas as pd
import requests
import time
import json
import google.generativeai as genai
from io import BytesIO

st.set_page_config(
    layout="wide", 
    page_title="Telemetr PRO", 
    page_icon="🎯"
)

st.markdown(
    """
    <style>
    .metric-box { 
        background-color: #1e222b; 
        padding: 15px; 
        border-radius: 8px; 
        border: 1px solid #2d3139; 
        text-align: center; 
    }
    </style>
    """, 
    unsafe_allow_html=True
)

cat_map = {
    "Криптовалюта": "crypto",
    "Бизнес и стартапы": "business",
    "Финансы и инвестиции": "finance",
    "Маркетинг и реклама": "marketing",
    "Блоги / Эксперты": "blogs",
    "Новостные каналы": "news",
    "Юмор и развлечения": "humor",
    "Технологии и софт": "tech",
    "Образование и наука": "education",
    "Ставки и беттинг": "betting",
    "Психология": "psychology"
}

GEOS_LIST = [
    "russia", "turkey", "india", "brazil", "usa", 
    "uzbekistan", "kazakhstan", "belarus", "ukraine"
]

LANGS_LIST = [
    "Все языки", "ru", "tr", "en", "hi", "pt", 
    "uz", "kk", "be", "uk", "de", "fr"
]

def run_gemini(title, about, posts, product, key):
    if not key: 
        return {
            "score": "5", 
            "verdict": "Демо", 
            "banner": "—"
        }
    try:
        genai.configure(api_key=key.strip())
        prompt = (
            f"Ты аналитик Telegram Ads. Продукт: '{product}'. "
            f"Канал: {title}. Био: {about}. Посты: {posts}. "
            f"СТРОГО JSON: {{\"score\":\"1-10\","
            f"\"verdict\":\"текст\",\"banner\":\"текст\"}}"
        )
        model = genai.GenerativeModel('gemini-1.5-flash')
        resp = model.generate_content(prompt)
        clean = resp.text.replace("```json", "")
        clean = clean.replace("```", "").strip()
        return json.loads(clean)
    except: 
        return {
            "score": "5", 
            "verdict": "Ошибка ИИ", 
            "banner": "—"
        }

if "database_state" not in st.session_state: 
    st.session_state.database_state = None

with st.sidebar:
    st.header("🔑 Доступы и Поиск")
    t_key = st.text_input("Telemetr API Токен", type="password")
    g_key = st.text_input("Gemini API Токен", type="password")
    ui_term = st.text_input("Поисковое слово (Ключевик)")
    
    st.header("🎯 Данные о канале")
    ui_geo = st.selectbox("Страна (Обязательно)", GEOS_LIST)
    ui_cat = st.selectbox("Категория", ["Все категории"] + list(cat_map.keys()))
    ui_lang = st.selectbox("Язык", LANGS_LIST)
    ui_max_ch = st.selectbox("Сколько собрать (макс)", [20, 40, 60, 100], index=1)
    
    with st.expander("📈 Фильтры прироста"):
        cg1, cg2 = st.columns(2)
        g24_min = cg1.number_input("Прирост 24ч от", value=0)
        g24_max = cg2.number_input("Прирост 24ч до", value=0)
        
    with st.expander("👁 Просмотры и ER"):
        cv1, cv2 = st.columns(2)
        v_min = cv1.number_input("Просмотры от", value=0)
        v_max = cv2.number_input("Просмотры до", value=
