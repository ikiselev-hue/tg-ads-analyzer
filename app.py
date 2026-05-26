import streamlit as st
import pandas as pd
import requests
import time
import json
import google.generativeai as genai
from io import BytesIO
import traceback

# =====================================================================
# 1. СИСТЕМНЫЕ НАСТРОЙКИ И СТИЛИЗАЦИЯ ИНТЕРФЕЙСА
# =====================================================================
st.set_page_config(
    layout="wide", 
    page_title="Telemetr AI Professional Parser", 
    page_icon="🎯"
)

# Внедрение кастомных CSS-стилей для создания премиального темного UI
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
# 2. ПРОДЖЕКТ-КЛАСС ДЛЯ РАБОТЫ С API TELEMETR.IO
# =====================================================================
class TelemetrProductionAPI:
    """Профессиональный клиент для работы с API Telemetr.io с обработкой лимитов и ошибок"""
    def __init__(self, api_key: str):
        self.api_key = api_key.strip() if api_key else None
        # Базовый URL API Telemetr (актуализируйте эндпоинт при необходимости согласно докам вашего тарифа)
        self.base_url = "https://api.telemetr.io/v1"
        
        # Разные версии тарифов Telemetr могут требовать X-Auth-Token или Authorization Bearer
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Auth-Token": self.api_key
        }

    def fetch_dictionaries(self):
        """Возвращает справочники ГЕО, языков и категорий"""
        # Предустановленные системные списки для исключения лишних холостых запросов к серверам
        return {
            "categories": ["Криптовалюта", "Бизнес и стартапы", "Финансы и инвестиции", "Ставки и беттинг", "Маркетинг и реклама", "Блоги / Эксперты", "Психология", "Новостные каналы"],
            "geos": ["RU", "TR", "IN", "BR", "US", "UZ", "KZ", "AE", "DE", "ES"],
            "languages": ["ru", "tr", "hi", "pt", "en", "uz", "kk", "ar", "de", "es"]
        }

    def execute_matrix_parsing(self, geo: str, lang: str, category: str, max_pages: int = 5):
        """Потоковый сбор данных из Telemetr по жесткой связке параметров с пагинацией"""
        # Если ключи не переданы, активируется защищенный демонстрационный симулятор данных
        if not self.api_key:
            return self._execute_mock_simulation(geo, lang, category)

        collected_channels = []
        page = 1
        limit_per_page = 50

        # Маппинг категорий на латиницу / внутренние ID Telemetr (при необходимости настроить под доки)
        category_mapping = {
            "Криптовалюта": "crypto", "Бизнес и стартапы": "business", "Финансы и инвестиции": "finance",
            "Ставки и беттинг": "betting", "Маркетинг и реклама": "marketing", "Блоги / Эксперты": "blogs",
            "Психология": "psychology", "Новостные каналы": "news"
        }
        api_category = category_mapping.get(category, "crypto")

        while page <= max_pages:
            # Названия параметров запроса полностью соответствуют стандартной спецификации поисковых методов
            query_params = {
                "geo": geo.lower(),
                "lang": lang.lower(),
                "category": api_category,
                "page": page,
                "limit": limit_per_page
            }
            
            try:
                # Внутренний эндпоинт поиска каналов
                response = requests.get(
                    f"{self.base_url}/channels/search", 
                    headers=self.headers, 
                    params=query_params, 
                    timeout=20
                )
                
                # Обработка защиты от превышения лимитов запросов (Rate Limit)
                if response.status_code == 429:
                    time.sleep(4)
                    continue
                elif response.status_code == 401:
                    st.error("❌ Ошибка авторизации: Неверный API ключ Telemetr.io")
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
                        "recent_posts": " | ".join([p.get("text", "") for p in item.get("recent_posts", [])[:3]]) or "Контент постов недоступен через API"
                    })
                
                if len(items) < limit_per_page:
                    break
                    
                page += 1
                time.sleep(0.6) # Безопасный интервал между страницами пагинации
                
            except Exception as ex:
                st.sidebar.error(f"Сбой транспорта API: {str(ex)}")
                break

        return collected_channels

    def _execute_mock_simulation(self, geo, lang, category):
        """Высокоточный имитатор ответов для отладки и проверки бизнес-логики софта"""
        time.sleep(0.15)
        return [
            {
                "geo": geo, "lang": lang, "category": category,
                "title": f"🚀 {category} | Target TG Channel",
                "link": f"https://t.me/mock_channel_{geo.lower()}_1",
                "subs": 48200, "views": 7600, "er": 15.8,
                "about": f"Лучший экспертный ресурс по теме {category} на рынке ГЕО: {geo}.",
                "recent_posts": "Пост 1: Анализ рынка на сегодня. Пост 2: Срочные новости индустрии. Пост 3: Как избежать ошибок при закупке."
            },
            {
                "geo": geo, "lang": lang, "category": category,
                "title": f"💰 Инсайды Ниши [{category}]",
                "link": f"https://t.me/mock_channel_{geo.lower()}_2",
                "subs": 124000, "views": 11300, "er": 9.1,
                "about": "Приватный контент для специалистов. Закрытые разборы и статистика.",
                "recent_posts": "Пост 1: Новый кейс масштабирования. Пост 2: Графики и прогнозы на текущий квартал."
            },
            {
                "geo": geo, "lang": lang, "category": category,
                "title": f"Агрегатор Мемов ({category})",
                "link": f"https://t.me/mock_channel_{geo.lower()}_3",
                "subs": 12000, "views": 250, "er": 2.1,
                "about": "Просто развлекательный контент. Смеемся всей командой, подписывайся.",
                "recent_posts": "Пост 1: Смешная картинка. Пост 2: Ссылки на партнерские казино и розыгрыши."
            }
        ]

# =====================================================================
# 3. МОДУЛЬ ГЛУБОКОГО СМЫСЛОВОГО ИИ-АНАЛИЗА (GEMINI API)
# =====================================================================
def run_gemini_intelligence(title, about, posts, product_info, api_key):
    """Отправляет текстовый профиль канала нейросети Gemini для глубокой оценки"""
    if not api_key:
        return {"score": "5", "verdict": "Режим симулятора: Введите ключ Gemini для активации ИИ.", "banner": "—"}
        
    try:
        genai.configure(api_key=api_key.strip())
        # Использование актуальной, быстрой и экономичной модели Gemini 1.5 Flash
        ai_engine = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Ты — главный аналитик данных и специалист по закупке трафика в Telegram Ads.
        Тебе необходимо провести аудит контента Telegram-канала и рассчитать его полезность для рекламы нашего продукта.
        
        НАШ ПРОДУКТ/УСЛУГА:
        "{product_info}"
        
        ДАННЫЕ ИЗ БАЗЫ ТЕЛЕМЕТРА ПО КАНАЛУ:
        - Имя канала: {title}
        - Биография (описание): {about}
        - Тексты последних публикаций: {posts}
        
        ИНСТРУКЦИЯ ДЛЯ ВЫПОЛНЕНИЯ:
        1. Оцени смысловую релевантность контента канала нашему продукту. Поставь строго оценку от 1 до 10.
        2. Напиши детальный экспертный вердикт на русском языке (почему канал подходит или не подходит, есть ли признаки спама/кликбейта или нецелевой аудитории).
        3. Разработай готовый рекламный текст для объявления Telegram Ads. Текст должен строго укладываться в лимит до 160 символов, цеплять боли аудитории и мотивировать перейти.
        
        Верни ответ ИСКЛЮЧИТЕЛЬНО в формате чистого JSON без использования разметки markdown, без символов ```json или ```. Структура JSON:
        {{
            "score": "оценка от 1 до 10",
            "verdict": "текст вердикта на русском языке",
            "banner": "текст рекламного объявления до 160 символов"
        }}
        """
        response = ai_engine.generate_content(prompt)
        
        # Защитная очистка строки от возможных артефактов markdown-ответа ИИ
        sanitized_json_str = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(sanitized_json_str)
        
    except Exception as error:
        return {
            "score": "Ошибка",
            "verdict": f"Не удалось декодировать структуру ответа ИИ: {str(error)}",
            "banner": "—"
        }

# =====================================================================
# 4. ФУНКЦИЯ ДИНАМИЧЕСКОГО СКОРИНГА ПО МЕТРИКАМ
# =====================================================================
def compute_mathematical_tier(row, limit_views, limit_er):
    """Присваивает категорию качества на основе математических матриц вовлеченности"""
    er_val = float(row.get('er', 0.0))
    views_val = int(row.get('views', 0))
    
    if er_val >= 10.0 and views_val >= (limit_views * 1.5):
        return "Good", "Высокий уровень вовлеченности (ER >= 10%) и отличный охват постов."
    elif er_val >= limit_er and views_val >= limit_views:
        return "Medium", "Показатели стабильны и соответствуют базовым критериям качества ниши."
    else:
        return "Bad", "Внимание! Слишком низкий ER или охваты. Подозрение на ботов или выжженную базу."

# =====================================================================
# 5. ЯДРО СЕРВИСА (ИНТЕРФЕЙС И КЛИЕНТСКАЯ ЛОГИКА СЕССИЙ)
# =====================================================================

# Создание изолированного пространства имен для каждого пользователя
if "database_state" not in st.session_state:
    st.session_state.database_state = None

# --- ЛЕВАЯ ПАНЕЛЬ С ФИЛЬТРАМИ (САЙДБАР) ---
with st.sidebar:
    st.header("🔑 Конфигурация Доступов")
    
    with st.expander("Ввод приватных API токенов", expanded=False):
        input_telemetr_key = st.text_input("Telemetr API Токен", type="password", help="Ваш токен из личного кабинета Telemetr")
        input_gemini_key = st.text_input("Google Gemini API Токен", type="password", help="Ключ для работы ИИ модуля аналитики")
        st.caption("🔒 Если оставить поля пустыми, сервис запустится в демонстрационном режиме на безопасной локальной базе данных.")

    st.markdown("---")
    st.header("🎯 Матрица Парсинга")
    
    # Инициализация клиента
    api_engine = TelemetrProductionAPI(input_telemetr_key)
    schema_dicts = api_engine.fetch_dictionaries()
    
    ui_category = st.selectbox("Тематическая категория каналов", schema_dicts["categories"])
    ui_geo = st.selectbox("ГЕО-локация (Матричный перебор)", ["Собрать все доступные ГЕО"] + schema_dicts["geos"])
    ui_lang = st.selectbox("Язык каналов (Матричный перебор)", ["Собрать все доступные языки"] + schema_dicts["languages"])
    
    st.markdown("---")
    st.header("📊 Математические Фильтры")
    ui_min_subs = st.number_input("Минимум подписчиков (Subs от)", value=5000, step=1000)
    ui_min_views = st.number_input("Минимум средних просмотров (Views от)", value=1000, step=500)
    ui_min_er = st.slider("Минимальный уровень вовлеченности (ER от %)", min_value=0.0, max_value=100.0, value=5.0, step=0.5)

    st.markdown("---")
    st.header("🤖 Настройки Нейросети")
    ui_ai_active = st.checkbox("Активировать ИИ-скоринг контента", value=False, help="Включение ИИ-модуля для анализа постов и генерации креативов")
    ui_product_desc = st.text_area(
        "Описание вашего оффера / продукта под запуск:", 
        value="Услуги агентства по лидогенерации и настройке таргетированной рекламы Telegram Ads под ключ.",
        disabled=not ui_ai_active
    )

    st.markdown("---")
    action_trigger = st.button("🚀 ЗАПУСТИТЬ АНАЛИЗ БАЗЫ", use_container_width=True, type="primary")

# --- ГЛАВНЫЙ ЭКРАН СЕРВИСА (РАБОЧАЯ ОБЛАСТЬ) ---
st.title("🎯 Умный Сервис Подбора Таргетов Telegram Ads")
st.caption("Автоматизация сбора баз данных через API Telemetr.io с глубоким семантическим ИИ-аудитом каналов")

# ЛОГИКА ОБРАБОТКИ НАЖАТИЯ КНОПКИ СБОРА
if action_trigger:
    with st.spinner("Запущен матричный сбор связок `ГЕО × Язык × Категория`. Пожалуйста, подождите..."):
        
        # Вычисление списков перебора для формирования матрицы связок
        geos_matrix = schema_dicts["geos"] if ui_geo == "Собрать все доступные ГЕО" else [ui_geo]
        langs_matrix = schema_dicts["languages"] if ui_lang == "Собрать все доступные языки" else [ui_lang]
        
        raw_aggregated_pool = []
        
        # Перебор сетки связок
        for current_geo in geos_matrix:
            for current_lang in langs_matrix:
                batch_data = api_engine.execute_matrix_parsing(geo=current_geo, lang=current_lang, category=ui_category)
                raw_aggregated_pool.extend(batch_data)
                
        if raw_aggregated_pool:
            processing_df = pd.DataFrame(raw_aggregated_pool)
            
            # Строгое исключение дубликатов по уникальной ссылке на канал (защита от сквозных пересечений базы)
            processing_df = processing_df.drop_duplicates(subset=["link"])
            
            # Отсечение по жестким числовым лимитам пользователя
            processing_df = processing_df[
                (processing_df['subs'] >= ui_min_subs) & 
                (processing_df['views'] >= ui_min_views) & 
                (processing_df['er'] >= ui_min_er)
            ]
            
            if not processing_df.empty:
                # Накатываем математическую оценку
                tier_results = processing_df.apply(lambda row: compute_mathematical_tier(row, ui_min_views, ui_min_er), axis=1)
                processing_df['Score'] = [t[0] for t in tier_results]
                processing_df['Reason'] = [t[1] for t in tier_results]
                
                # Накатываем ИИ-скоринг и генерацию креативов, если чекбокс активен
                if ui_ai_active:
                    ai_scores, ai_verdicts, ai_banners = [], [], []
                    progress_ui_bar = st.progress(0, text="ИИ подключается к лингвистическому аудиту...")
                    total_records = len(processing_df)
                    
                    for index, record in enumerate(processing_df.itertuples()):
                        ai_data = run_gemini_intelligence(
                            title=record.title,
                            about=record.about,
                            posts=record.recent_posts,
                            product_info=ui_product_desc,
                            api_key=input_gemini_key
                        )
                        ai_scores.append(ai_data.get("score", "5"))
                        ai_verdicts.append(ai_data.get("verdict", "—"))
                        ai_banners.append(ai_data.get("banner", "—"))
                        
                        # Обновление прогресс-бара для пользователя на экране в реальном времени
                        progress_ui_bar.progress((index + 1) / total_records, text=f"Нейросеть сканирует контент: {index + 1} из {total_records} каналов")
                    
                    processing_df['AI Relevance'] = ai_scores
                    processing_df['AI Content Review'] = ai_verdicts
                    processing_df['AI Telegram Ads Banner'] = ai_banners
                    progress_ui_bar.empty()
                else:
                    # Заполнение заглушками, если ИИ-модуль не был задействован
                    processing_df['AI Relevance'] = "Выключен"
                    processing_df['AI Content Review'] = "Активируйте чекбокс 'ИИ-скоринг' на панели управления"
                    processing_df['AI Telegram Ads Banner'] = "—"
                
                st.session_state.database_state = processing_df
            else:
                st.session_state.database_state = pd.DataFrame()
        else:
            st.session_state.database_state = pd.DataFrame()

# ОТРИСОВКА ВЕРХНИХ МЕТРИК И СМАРТ-ТАБЛИЦЫ С ДАННЫМИ
if st.session_state.database_state is not None:
    active_working_df = st.session_state.database_state.copy()
    
    if active_working_df.empty:
        st.warning("⚠️ По указанной комбинации параметров каналов не найдено. Попробуйте снизить пороговые фильтры вовлеченности или просмотров.")
    else:
        # Расчет аналитических показателей верхнего уровня
        count_total = len(active_working_df)
        count_good = len(active_working_df[active_working_df['Score'] == "Good"])
        count_medium = len(active_working_df[active_working_df['Score'] == "Medium"])
        count_bad = len(active_working_df[active_working_df['Score'] == "Bad"])
        
        # Вывод плиток верхних метрик
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1: st.markdown(f"<div class='metric-box'>🛑 Найдено таргетов<br><h2>{count_total}</h2></div>", unsafe_allow_html=True)
        with col_m2: st.markdown(f"<div class='metric-box'>🟢 Качественных (Good)<br><h2>{count_good}</h2></div>", unsafe_allow_html=True)
        with col_m3: st.markdown(f"<div class='metric-box'>🟡 Средних (Medium)<br><h2>{count_medium}</h2></div>", unsafe_allow_html=True)
        with col_m4: st.markdown(f"<div class='metric-box'>🔴 Рискованных (Bad)<br><h2>{count_bad}</h2></div>", unsafe_allow_html=True)
            
        st.markdown("---")
        
        # Функциональная панель инструментов: Сквозной поиск и Скачивание файлов
        layout_col1, layout_col2, layout_col3 = st.columns([2, 1, 1])
        with layout_col1:
            live_search_query = st.text_input("🔍 Быстрый живой фильтр по ключевому слову в названии канала:", "")
            if live_search_query:
                active_working_df = active_working_df[active_working_df['title'].str.contains(live_search_query, case=False)]
                
        with layout_col2:
            # Генератор выгрузки CSV
            csv_raw_bytes = active_working_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Экспорт базы в CSV", 
                data=csv_raw_bytes, 
                file_name="telegram_ads_target_database.csv", 
                mime="text/csv", 
                use_container_width=True
            )
            
        with layout_col3:
            # Генератор выгрузки Excel
            excel_memory_buffer = BytesIO()
            with pd.ExcelWriter(excel_memory_buffer, engine='openpyxl') as excel_writer:
                active_working_df.to_excel(excel_writer, index=False, sheet_name='Таргеты Рекламы')
            st.download_button(
                label="📥 Экспорт базы в Excel", 
                data=excel_memory_buffer.getvalue(), 
                file_name="telegram_ads_target_database.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                use_container_width=True
            )
            
        # Интерактивный интеллектуальный вывод таблицы с возможностью сортировки в один клик
        st.dataframe(
            active_working_df,
            column_config={
                "geo": st.column_config.TextColumn("ГЕО"),
                "lang": st.column_config.TextColumn("Язык"),
                "category": st.column_config.TextColumn("Категория"),
                "title": st.column_config.TextColumn("Название Telegram-канала"),
                "link": st.column_config.LinkColumn("Кликабельная ссылка (t.me)"),
                "subs": st.column_config.NumberColumn("Подписчики", format="%d"),
                "views": st.column_config.NumberColumn("Просмотры на пост", format="%d"),
                "er": st.column_config.NumberColumn("ER (%)", format="%.2f%%"),
                "Score": st.column_config.SelectboxColumn("Оценка Системы", options=["Good", "Medium", "Bad"]),
                "Reason": st.column_config.TextColumn("Техническое Обоснование"),
                "AI Relevance": st.column_config.TextColumn("ИИ Релевантность (1-10)"),
                "AI Content Review": st.column_config.TextColumn("Смысловой ИИ-Анализ Контента"),
                "AI Telegram Ads Banner": st.column_config.TextColumn("Готовый ИИ Креатив (до 160 симв.)")
            },
            hide_index=True,
            use_container_width=True
        )
