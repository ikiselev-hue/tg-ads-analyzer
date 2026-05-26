import streamlit as st
import pandas as pd
import requests
import time
import json
import google.generativeai as genai
from io import BytesIO

# 1. НАСТРОЙКА СТРАНИЦЫ
st.set_page_config(
    layout="wide", 
    page_title="Telemetr PRO Analyzer"
)

# Кастомные стили метрик
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

# 2. СПРАВОЧНИКИ И НАСТРОЙКИ
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
    "russia", "turkey", "india", "brazil", 
    "usa", "uzbekistan", "kazakhstan", 
    "belarus", "ukraine"
]

LANGS_LIST = [
    "Все языки", "ru", "tr", "en", "hi", 
    "pt", "uz", "kk", "be", "uk"
]

# 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
def run_gemini(title, about, posts, product, key):
    if not key: 
        return {
            "score": "5", 
            "verdict": "Демо-режим", 
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

def compute_score(row):
    er = row.get("er", 0.0)
    views = row.get("views", 0)
    if er >= 10.0 and views >= 5000:
        return "Good"
    if er >= 4.0:
        return "Medium"
    return "Bad"

def compute_reason(row):
    score = row.get("Score")
    if score == "Good":
        return "Отличные охваты и вовлеченность"
    if score == "Medium":
        return "Стабильные средние показатели"
    return "Низкий ER. Риск накрутки контента"

# Инициализация состояния
if "database_state" not in st.session_state: 
    st.session_state.database_state = None

# 4. ИНТЕРФЕЙС ПАНЕЛИ УПРАВЛЕНИЯ
t_key = st.sidebar.text_input("Telemetr Token", type="password")
g_key = st.sidebar.text_input("Gemini Token", type="password")
ui_term = st.sidebar.text_input("Ключевое слово (term)")

st.sidebar.markdown("---")
ui_geo = st.sidebar.selectbox("Страна (country)", GEOS_LIST)
ui_cat = st.sidebar.selectbox("Категория", ["Все категории"] + list(cat_map.keys()))
ui_lang = st.sidebar.selectbox("Язык (language)", LANGS_LIST)
ui_max_ch = st.sidebar.selectbox("Макс каналов", [20, 40, 60, 100], index=1)

st.sidebar.markdown("---")
exp1 = st.sidebar.expander("📈 Фильтры прироста")
g24_min = exp1.number_input("Прирост 24ч от", value=0)
g24_max = exp1.number_input("Прирост 24ч до", value=0)

exp2 = st.sidebar.expander("👁 Просмотры и ER")
v_min = exp2.number_input("Просмотры от", value=0)
v_max = exp2.number_input("Просмотры до", value=0)
er_min = exp2.number_input("ER% от", value=0.0, step=0.5)
er_max = exp2.number_input("ER% до", value=0.0, step=0.5)

exp3 = st.sidebar.expander("📊 Реклама (Ads Index)")
ads_min = exp3.number_input("Ads Index от", value=0)
ads_max = exp3.number_input("Ads Index до", value=0)

st.sidebar.markdown("---")
ui_ai = st.sidebar.checkbox("Включить ИИ-анализ контента")
ui_prod = st.sidebar.text_area("Описание оффера:", value="Услуги рекламы.")
action = st.sidebar.button("🚀 ЗАПУСТИТЬ АНАЛИЗ", type="primary", use_container_width=True)

st.title("🎯 Умный Сервис Подбора Таргетов Telegram Ads")

# 5. СБОР И ФИЛЬТРАЦИЯ ДАННЫХ
if action:
    p = {"country": ui_geo.lower()}
    
    if ui_term.strip(): 
        p["term"] = ui_term.strip()
    if ui_cat != "Все категории": 
        p["category"] = cat_map[ui_cat]
    if ui_lang != "Все языки": 
        p["language"] = ui_lang.lower()
        
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
        # Генерация чистых демонстрационных данных
        for idx in range(1, 6):
            res.append({
                "geo": ui_geo, "lang": "ru", "category": "Бизнес",
                "title": f"🚀 Демо Канал {idx}", 
                "link": f"https://t.me/mock_channel_{idx}",
                "subs": 50000 + (idx * 10000), 
                "views": 4000 + (idx * 500), 
                "er": 3.5 + (idx * 1.5),
                "growth_24h": 150 * idx, "ads_index": 12 * idx,
                "about": "Описание тестового канала для проверки ИИ",
                "recent_posts": "Пост про маркетинг и закупки трафика."
            })
    else:
        try:
            url = "https://api.telemetr.io/v1/channels/search"
            h = {"accept": "application/json", "x-api-key": t_key.strip()}
            pages = max(1, ui_max_ch // 20)
            
            for current_page in range(1, pages + 1):
                p["page"] = current_page
                p["limit"] = 20  # Жесткий безопасный лимит Telemetr
                r = requests.get(url, headers=h, params=p, timeout=20)
                
                if r.status_code != 200:
                    st.error(f"⛔️ Ошибка ({r.status_code}): {r.text}")
                    break
                    
                data = r.json()
                items = data.get("channels") or data.get("data") or data.get("items") or []
                if not items: 
                    break
                    
                for i in items:
                    r_lang = i.get("language") or i.get("lang") or "—"
                    p_list = i.get("recent_posts", [])[:3]
                    p_text = [ps.get("text", "") for ps in p_list]
                    r_posts = " | ".join(p_text) or "—"
                    
                    row = {
                        "geo": ui_geo,
                        "lang": r_lang,
                        "category": i.get("category") or "—",
                        "title": i.get("title", "Без названия"),
                        "link": i.get("link") or f"https://t.me/{i.get('username','')}",
                        "subs": int(i.get("participants_count") or i.get("subs", 0)),
                        "views": int(i.get("views_per_post") or i.get("views", 0)),
                        "er": float(i.get("er") or 0.0),
                        "growth_24h": int(i.get("growth_24h") or i.get("growth", 0)),
                        "ads_index": int(i.get("ads_index") or i.get("members_ads_count", 0)),
                        "about": i.get("about", "—"),
                        "recent_posts": r_posts
                    }
                    res.append(row)
                    
                if len(items) < 20: 
                    break
                time.sleep(0.6)
        except Exception as e: 
            st.error(f"💥 Ошибка сбора данных: {str(e)}")

    if res:
        df = pd.DataFrame(res).drop_duplicates(subset=["link"])
        df['Score'] = df.apply(compute_score, axis=1)
        df['Reason'] = df.apply(compute_reason, axis=1)
        
        if ui_ai and g_key.strip():
            sc, vd, bn = [], [], []
            p_bar = st.progress(0, text="ИИ анализирует контент постов...")
            total_items = len(df)
            
            for idx, rec in enumerate(df.itertuples()):
                ai = run_gemini(rec.title, rec.about, rec.recent_posts, ui_prod, g_key)
                sc.append(ai.get("score", "5"))
                vd.append(ai.get("verdict", "—"))
                bn.append(ai.get("banner", "—"))
                p_bar.progress((idx + 1) / total_items)
            df['AI Relevance'] = sc
            df['AI Content Review'] = vd
            df['AI Telegram Ads Banner'] = bn
            p_bar.empty()
        else: 
            df['AI Relevance'] = "Выключен"
            df['AI Content Review'] = "Включите ИИ в меню слева"
            df['AI Telegram Ads Banner'] = "—"
        st.session_state.database_state = df
    else: 
        st.session_state.database_state = pd.DataFrame()

# 6.ОТРИСОВКА ИНТЕРФЕЙСА ТАБЛИЦЫ И ЭКСПОРТА
if st.session_state.database_state is not None:
    df_act = st.session_state.database_state.copy()
    if df_act.empty: 
        st.warning("⚠️ Каналов не найдено. Попробуйте расширить диапазоны фильтров.")
    else:
        t_len = len(df_act)
        g_len = len(df_act[df_act['Score'] == 'Good'])
        m_len = len(df_act[df_act['Score'] == 'Medium'])
        b_len = len(df_act[df_act['Score'] == 'Bad'])

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='metric-box'>🛑 Всего<br><h2>{t_len}</h2></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-box'>🟢 Good<br><h2>{g_len}</h2></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-box'>🟡 Medium<br><h2>{m_len}</h2></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='metric-box'>🔴 Bad<br><h2>{b_len}</h2></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        l1, l2, l3 = st.columns([2, 1, 1])
        q = l1.text_input("🔍 Быстрый фильтр по названию:")
        if q: 
            df_act = df_act[df_act['title'].str.contains(q, case=False)]
            
        l2.download_button(
            label="📥 Экспорт CSV", 
            data=df_act.to_csv(index=False).encode('utf-8'), 
            file_name="target.csv", 
            mime="text/csv", 
            use_container_width=True
        )
        
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as w: 
            df_act.to_excel(w, index=False)
            
        l3.download_button(
            label="📥 Экспорт Excel", 
            data=buf.getvalue(), 
            file_name="target.xlsx", 
            use_container_width=True
        )
        
        st.dataframe(
            df_act, 
            column_config={
                "geo": st.column_config.TextColumn("ГЕО"),
                "lang": st.column_config.TextColumn("Язык"),
                "category": st.column_config.TextColumn("Категория"),
                "title": st.column_config.TextColumn("Название канала"),
                "link": st.column_config.LinkColumn("Ссылка"),
                "subs": st.column_config.NumberColumn("Подписчики", format="%d"),
                "views": st.column_config.NumberColumn("Просмотры", format="%d"),
                "er": st.column_config.NumberColumn("ER (%)", format="%.2f%%"),
                "growth_24h": st.column_config.NumberColumn("Прирост 24ч", format="%d"),
                "ads_index": st.column_config.NumberColumn("Ads Index", format="%d"),
                "Score": st.column_config.SelectboxColumn("Оценка", options=["Good", "Medium", "Bad"]),
                "Reason": st.column_config.TextColumn("Обоснование"),
                "AI Relevance": st.column_config.TextColumn("Релевантность (1-10)"),
                "AI Content Review": st.column_config.TextColumn("ИИ-Анализ"),
                "AI Telegram Ads Banner": st.column_config.TextColumn("ИИ-Объявление")
            },
            hide_index=True, 
            use_container_width=True
        )
