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

# Стилизация темной темы админки
st.markdown("""
    <style>
    .metric-box { 
        background-color: #1e222b; 
        padding: 15px; 
        border-radius: 8px; 
        border: 1px solid #2d3139; 
        text-align: center; 
    }
    </style>
""", unsafe_allow_html=True)

# Словарь категорий (короткие строки во избежание обрезки)
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
        return {"score": "5", "verdict": "Демо", "banner": "—"}
    try:
        genai.configure(api_key=key.strip())
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = (
            f"Ты аналитик Telegram Ads. Продукт: '{product}'. "
            f"Канал: {title}. Био: {about}. Посты: {posts}. "
            f"СТРОГО JSON: {{\"score\":\"1-10\",\"verdict\":\"текст\",\"banner\":\"текст\"}}"
        )
        resp = model.generate_content(prompt)
        sanitized = resp.text.replace("```json", "").replace("```", "").strip()
        return json.loads(sanitized)
    except: 
        return {"score": "5", "verdict": "Ошибка ИИ", "banner": "—"}

if "database_state" not in st.session_state: 
    st.session_state.database_state = None

# --- ИНТЕРФЕЙС ФИЛЬТРОВ (САЙДБАР) ---
with st.sidebar:
    st.header("🔑 Доступы и Поиск")
    t_key = st.text_input("Telemetr API Токен", type="password")
    g_key = st.text_input("Gemini API Токен", type="password")
    ui_term = st.text_input("Поисковое слово (Ключевик)")
    
    st.header("🎯 Данные о канале")
    ui_geo = st.selectbox("Страна (Обязательно)", GEOS_LIST)
    ui_cat = st.selectbox("Категория", ["Все категории"] + list(cat_map.keys()))
    ui_lang = st.selectbox("Язык", LANGS_LIST)
    
    # Расширенные фильтры из скриншота
    with st.expander("📈 Фильтры прироста"):
        cg1, cg2 = st.columns(2)
        g24_min = cg1.number_input("Прирост 24ч от", value=0)
        g24_max = cg2.number_input("Прирост 24ч до", value=0)
        
    with st.expander("👁 Просмотры и ER"):
        cv1, cv2 = st.columns(2)
        v_min = cv1.number_input("Просмотры от", value=0)
        v_max = cv2.number_input("Просмотры до", value=0)
        cv3, cv4 = st.columns(2)
        er_min = cv3.number_input("ER% от", value=0.0, step=0.5)
        er_max = cv4.number_input("ER% до", value=0.0, step=0.5)
        
    with st.expander("📊 Рекламные метрики"):
        ca1, ca2 = st.columns(2)
        ads_min = ca1.number_input("Ads Index от", value=0)
        ads_max = ca2.number_input("Ads Index до", value=0)
        
    ui_ai = st.checkbox("Включить ИИ-анализ контента")
    ui_prod = st.text_area("Описание оффера:", value="Услуги по закупке рекламы.")
    action = st.button("🚀 ЗАПУСТИТЬ АНАЛИЗ БАЗЫ", type="primary", use_container_width=True)

st.title("🎯 Умный Сервис Подбора Таргетов Telegram Ads")

# --- ЛОГИКА ОБРАБОТКИ ЗАПРОСА ---
if action:
    p = {"country": ui_geo.lower(), "page": 1, "limit": 40}
    if ui_term.strip(): p["term"] = ui_term.strip()
    if ui_cat != "Все категории": p["category"] = cat_map[ui_cat]
    if ui_lang != "Все языки": p["language"] = ui_lang.lower()
    
    # Наполнение словаря диапазонами
    if g24_min > 0: p["growth_24h_min"] = g24_min
    if g24_max > 0: p["growth_24h_max"] = g24_max
    if v_min > 0: p["views_min"] = v_min
    if v_max > 0: p["views_max"] = v_max
    if er_min > 0.0: p["er_min"] = er_min
    if er_max > 0.0: p["er_max"] = er_max
    if ads_min > 0: p["ads_index_min"] = ads_min
    if ads_max > 0: p["ads_index_max"] = ads_max

    res = []
    if not t_key.strip():
        # Демо-данные, если токен пустой
        res = [
            {"geo": ui_geo, "lang": "ru", "category": "Бизнес", "title": "🚀 Демо Канал 1", "link": "https://t.me/mock_1", "subs": 75000, "views": 12000, "er": 15.5, "growth_24h": 450, "ads_index": 82, "about": "Тест", "recent_posts": "Посты"},
            {"geo": ui_geo, "lang": "ru", "category": "Бизнес", "title": "💰 Демо Канал 2", "link": "https://t.me/mock_2", "subs": 120000, "views": 8500, "er": 6.2, "growth_24h": -120, "ads_index": 45, "about": "Тест", "recent_posts": "Посты"}
        ]
    else:
        try:
            url = "https://api.telemetr.io/v1/channels/search"
            h = {"accept": "application/json", "x-api-key": t_key.strip()}
            r = requests.get(url, headers=h, params=p, timeout=20)
            
            if r.status_code == 200:
                data = r.json()
                items = data.get("channels") or data.get("data") or data.get("items") or []
                for i in items:
                    res.append({
                        "geo": ui_geo, 
                        "lang": i.get("language") or i.get("lang") or "—", 
                        "category": i.get("category") or "—",
                        "title": i.get("title", "Без названия"), 
                        "link": i.get("link") or f"https://t.me/{i.get('username','')}",
                        "subs": int(i.get("participants_count") or i.get("subs", 0)), 
                        "views": int(i.get("views_per_post") or i.get("views", 0)),
                        "er": float(i.get("er") or 0.0), 
                        "growth_24h": int(i.get("growth_24h") or i.get("growth", 0)),
                        "ads_index": int(i.get("ads_index") or i.get("members_ads_count", 0)), 
                        "about": i.get("about", "—"),
                        "recent_posts": " | ".join([posts.get("text", "") for posts in i.get("recent_posts", [])[:3]]) or "—"
                    })
            else: 
                st.error(f"⛔️ Ошибка Telemetr ({r.status_code}): {r.text}")
        except Exception as e: 
            st.error(f"💥 Ошибка: {str(e)}")

    if res:
        df = pd.DataFrame(res).drop_duplicates(subset=["link"])
        df['Score'] = df.apply(lambda r: "Good" if r['er'] >= 10.0 and r['views'] >= 5000 else ("Medium" if r['er'] >= 4.0 else "Bad"), axis=1)
        df['Reason'] = df.apply(lambda r: "Отличные показатели" if r['Score'] == "Good" else "Стабильные показатели", axis=1)
        
        if ui_ai and g_key.strip():
            sc, vd, bn = [], [], []
            p_bar = st.progress(0, text="ИИ работает...")
            for idx, rec in enumerate(df.itertuples()):
                ai = run_gemini(rec.title, rec.about, rec.recent_posts, ui_prod, g_key)
                sc.append(ai.get("score", "5"))
                vd.append(ai.get("verdict", "—"))
                bn.append(ai.get("banner", "—"))
                p_bar.progress((idx + 1) / len(df))
            df['AI Relevance'], df['AI Content Review'], df['AI Telegram Ads Banner'] = sc, vd, bn
            p_bar.empty()
        else: 
            df['AI Relevance'], df['AI Content Review'], df['AI Telegram Ads Banner'] = "Выключен", "Включите ИИ", "—"
        st.session_state.database_state = df
    else: 
        st.session_state.database_state = pd.DataFrame()

# --- ОТРИСОВКА РЕЗУЛЬТАТОВ ---
if st.session_state.database_state is not None:
    df_act = st.session_state.database_state.copy()
    if df_act.empty: 
        st.warning("⚠️ Каналов не найдено. Снизьте диапазоны фильтров.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='metric-box'>🛑 Всего<br><h2>{len(df_act)}</h2></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-box'>🟢 Good<br><h2>{len(df_act[df_act['Score']=='Good'])}</h2></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-box'>🟡 Medium<br><h2>{len(df_act[df_act['Score']=='Medium'])}</h2></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='metric-box'>🔴 Bad<br><h2>{len(df_act[df_act['Score']=='Bad'])}</h2></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        l1, l2, l3 = st.columns([2, 1, 1])
        q = l1.text_input("🔍 Быстрый фильтр по названию:")
        if q: 
            df_act = df_act[df_act['title'].str.contains(q, case=False)]
            
        l2.download_button("📥 Экспорт CSV", df_act.to_csv(index=False).encode('utf-8'), "target.csv", "text/csv", use_container_width=True)
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as w: 
            df_act.to_excel(w, index=False)
        l3.download_button("📥 Экспорт Excel", buf.getvalue(), "target.xlsx", use_container_width=True)
        
        st.dataframe(df_act, hide_index=True, use_container_width=True)
