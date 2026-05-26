import streamlit as st
import pandas as pd
import requests
import time
import json
import google.generativeai as genai
from io import BytesIO

st.set_page_config(
    layout="wide", 
    page_title="Telemetr PRO"
)

# Компактный дизайн карточек
st.markdown(
    "<style>.metric-box { background-color: #1e222b; "
    "padding: 15px; border-radius: 8px; "
    "border: 1px solid #2d3139; "
    "text-align: center; }</style>", 
    unsafe_allow_html=True
)

# Справочник категорий Telemetr
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
    "usa", "uzbekistan", "kazakhstan"
]

LANGS_LIST = [
    "Все языки", "ru", "tr", "en", "hi", 
    "pt", "uz", "kk"
]

def run_gemini(title, about, posts, product, key):
    if not key: 
        return {"score": "5", "verdict": "Демо", "banner": "—"}
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
        return {"score": "5", "verdict": "Ошибка ИИ", "banner": "—"}

if "database_state" not in st.session_state: 
    st.session_state.database_state = None

# --- ПОЛНОСТЬЮ ПЛОСКИЙ ИНТЕРФЕЙС САЙДБАРА ---
t_key = st.sidebar.text_input("Telemetr Token", type="password")
g_key = st.sidebar.text_input("Gemini Token", type="password")
ui_term = st.sidebar.text_input("Ключевое слово (term)")

st.sidebar.markdown("---")
ui_geo = st.sidebar.selectbox("Страна (country)", GEOS_LIST)
ui_cat = st.sidebar.selectbox("Категория (category)", ["Все категории"] + list(cat_map.keys()))
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

# --- СБОРКА И ПАРСИНГ ПАРАМЕТРОВ ---
if action:
    p = {}
    p["country"] = ui_geo.lower()
    
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
        # Плоские демо-данные без риска обрезки строк
        d1 = {"geo": ui_geo, "lang": "ru", "category": "Бизнес"}
        d1["title"] = "🚀 Демо Канал 1"
        d1["link"] = "https://t.me/mock_1"
        d1["subs"], d1["views"], d1["er"] = 75000, 12000, 15.5
        d1["growth_24h"], d1["ads_index"] = 450, 82
        d1["about"], d1["recent_posts"] = "Тест", "Посты"
        res.append(d1)
        
        d2 = {"geo": ui_geo, "lang": "ru", "category": "Бизнес"}
        d2["title"] = "💰 Демо Канал 2"
        d2["link"] = "https://t.me/mock_2"
        d2["subs"], d2["views"], d2["er"] = 120000, 8500, 6.2
        d2["growth_24h"], d2["ads_index"] = -120, 45
        d2["about"], d2["recent_posts"] = "Тест", "Посты"
        res.append(d2)
    else:
        try:
            url = "https://api.telemetr.io/v1/channels/search"
            h = {"accept": "application/json", "x-api-key": t_key.strip()}
            pages = max(1, ui_max_ch // 20)
            
            for current_page in range(1, pages + 1):
                p["page"] = current_page
                p["limit"] = 20
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
                    
                    row = {}
                    row["geo"] = ui_geo
                    row["lang"] = r_lang
                    row["category"] = i.get("category") or "—"
                    row["title"] = i.get("title", "Без названия")
                    row["link"] = i.get("link") or f"https://t.me/{i.get('username','')}"
                    row["subs"] = int(i.get("participants_count") or i.get("subs", 0))
                    row["views"] = int(i.get("views_per_post") or i.get("views", 0))
                    row["er"] = float(i.get("er") or 0.0)
                    row["growth_24h"] = int(i.get("growth_24h") or i.get("growth", 0))
                    row["ads_index"] = int(i.get("ads_index") or i.get("members_ads_count", 0))
                    row["about"] = i.get("about", "—")
                    row["recent_posts"] = r_posts
                    res.append(row)
                    
                if len(items) < 20: 
                    break
                time.sleep(0.6)
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
            df['AI Relevance'] = "Выключен"
            df['AI Content Review'] = "Включите ИИ"
            df['AI Telegram Ads Banner'] = "—"
        st.session_state.database_state = df
    else: 
        st.session_state.database_state = pd.DataFrame()

# --- ОТРИСОВКА ИНТЕРФЕЙСА ТАБЛИЦЫ ---
if st.session_state.database_state not in [None]:
    df_act = st.session_state.database_state.copy()
    if df_act.empty: 
        st.warning("⚠️ Каналов не найдено. Измените диапазоны фильтров.")
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
            
        l2.download_button("📥 Экспорт CSV", df_act.to_csv(index=False).encode('utf-8'), "target.csv", "text/csv", use_container_width=True)
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as w: 
            df_act.to_excel(w, index=False)
        l3.download_button("📥 Экспорт Excel", buf.getvalue(), "target.xlsx", use_container_width=True)
        
        st.dataframe(
            df_act, 
            column_config={
                "geo": st.column_config.TextColumn("ГЕО"),
                "lang": st.column_config.TextColumn("Язык"),
                "category": st.column_config.TextColumn("Категория"),
                "title": st.column_config.TextColumn("Название канала"),
                "link": st.column_config.LinkColumn("Ссылка (t.me)"),
                "subs": st.column_config.NumberColumn("Подписчики", format="%d"),
                "views": st.column_config.NumberColumn("Просмотры", format="%d"),
                "er": st.column_config.NumberColumn("ER (%)", format="%.2f%%"),
                "growth_24h": st.column_config.NumberColumn("Прирост 24ч", format="%d"),
                "ads_index": st.column_config.NumberColumn("Ads Index", format="%d"),
                "Score": st.column_config.SelectboxColumn("Оценка Системы", options=["Good", "Medium", "Bad"]),
                "Reason": st.column_config.TextColumn("Техническое Обоснование"),
                "AI Relevance": st.column_config.TextColumn("ИИ Релевантность (1-10)"),
                "AI Content Review": st.column_config.TextColumn("Смысловой ИИ-Анализ"),
                "AI Telegram Ads Banner": st.column_config.TextColumn("ИИ Креатив")
            },
            hide_index=True, 
            use_container_width=True
        )
