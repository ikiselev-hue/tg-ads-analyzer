import streamlit as st, pandas as pd, requests, time, json, google.generativeai as genai
from io import BytesIO

st.set_page_config(layout="wide", page_title="Telemetr PRO", page_icon="🎯")
st.markdown("<style>.metric-box { background-color: #1e222b; padding: 15px; border-radius: 8px; border: 1px solid #2d3139; text-align: center; }</style>", unsafe_allow_html=True)

cat_map = {"Криптовалюта": "crypto", "Бизнес и стартапы": "business", "Финансы и инвестиции": "finance", "Маркетинг и реклама": "marketing", "Блоги / Эксперты", "blogs", "Новостные каналы": "news", "Юмор и развлечения": "humor", "Технологии и софт": "tech", "Образование и наука": "education", "Ставки и беттинг": "betting", "Психология": "psychology"}
GEOS_LIST = ["russia", "turkey", "india", "brazil", "usa", "uzbekistan", "kazakhstan", "belarus", "ukraine"]
LANGS_LIST = ["Все языки", "ru", "tr", "en", "hi", "pt", "uz", "kk", "be", "uk", "de", "fr"]

def run_gemini(title, about, posts, product, key):
    if not key: return {"score": "5", "verdict": "Демо", "banner": "—"}
    try:
        genai.configure(api_key=key.strip())
        prompt = f"Ты аналитик Telegram Ads. Продукт: '{product}'. Канал: {title}. Био: {about}. Посты: {posts}. СТРОГО JSON: {{\"score\":\"1-10\",\"verdict\":\"текст\",\"banner\":\"текст\"}}"
        resp = genai.GenerativeModel('gemini-1.5-flash').generate_content(prompt)
        return json.loads(resp.text.replace("```json", "").replace("```", "").strip())
    except: return {"score": "5", "verdict": "Ошибка ИИ", "banner": "—"}

if "database_state" not in st.session_state: st.session_state.database_state = None

with st.sidebar:
    st.header("🔑 Доступы и Поиск")
    t_key = st.text_input("Telemetr API Токен", type="password")
    g_key = st.text_input("Gemini API Токен", type="password")
    ui_term = st.text_input("Поисковое слово (Ключевик)")
    st.header("🎯 Данные о канале")
    ui_geo = st.selectbox("Страна (Обязательно)", GEOS_LIST)
    ui_cat = st.selectbox("Категория", ["Все категории"] + list(cat_map.keys()))
    ui_lang = st.selectbox("Язык", LANGS_LIST)
    ui_max_ch = st.selectbox("Сколько каналов собрать (макс)", [20, 40, 60, 100], index=1)
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
    with st.expander("📊 Реклама"):
        ca1, ca2 = st.columns(2)
        ads_min = ca1.number_input("Ads Index от", value=0)
        ads_max = ca2.number_input("Ads Index до", value=0)
    ui_ai = st.checkbox("Включить ИИ-анализ контента")
    ui_prod = st.text_area("Описание оффера:", value="Услуги по закупке рекламы.")
    action = st.button("🚀 ЗАПУСТИТЬ АНАЛИЗ БАЗЫ", type="primary", use_container_width=True)

st.title("🎯 Умный Сервис Подбора Таргетов Telegram Ads")

if action:
    p = {"country": ui_geo.lower()}
    if ui_term.strip(): p["term"] = ui_term.strip()
    if ui_cat != "Все категории": p["category"] = cat_map[ui_cat]
    if ui_lang != "Все языки": p["language"] = ui_lang.lower()
    if g24_min > 0: p["growth_24h_min"] = g24_min
    if g24_max > 0: p
