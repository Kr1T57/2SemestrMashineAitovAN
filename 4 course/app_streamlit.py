import streamlit as st
import pandas as pd
import plotly.express as px
import requests

st.set_page_config(page_title="Прогнозирование стоимости недвижимости", layout="wide")

API_URL = "http://127.0.0.1:8000"


@st.cache_data(ttl=600)
def fetch_metadata():
    try:
        r = requests.get(f"{API_URL}/metadata", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {
        "cities": ["İstanbul", "Aydın", "Ankara", "İzmir", "Antalya", "Balıkesir", "Bursa", "Muğla"],
        "districts": ["Merkez", "Didim", "Kuşadası", "Esenyurt", "Edremit", "Çankaya", "Kadıköy", "Beşiktaş"],
        "subtypes": ["Квартира", "Вилла", "Частный дом", "Резиденция", "Дача"],
        "heatings": ["Kombi (Doğalgaz)", "Klima", "Merkezi Sistem", "Merkezi Sistem (Isı Payı Ölçer)", "Не указано"],
        "mape": 29.18
    }


metadata = fetch_metadata()

# Ровно 3 вкладки по заданию
tab_predict, tab_dashboard, tab_help = st.tabs(
    ["Прогноз стоимости", "Дашборд и аналитика", "Справка"]
)

# ==========================================
# ВКЛАДКА 1: Прогноз стоимости
# ==========================================
with tab_predict:
    st.title("Калькулятор рыночной стоимости недвижимости")
    st.write("Заполните характеристики объекта для расчета рекомендованной цены продажи.")

    with st.form("prediction_form"):
        st.subheader("1. Физические параметры")
        col1, col2 = st.columns(2)

        with col1:
            size = st.number_input("1. Общая площадь (кв. м)", min_value=15.0, max_value=800.0, value=110.0, step=1.0)
            room_count = st.number_input("2. Количество комнат", min_value=1, max_value=20, value=3, step=1)
            building_age = st.number_input("3. Возраст здания (лет, 0 — новостройка)", min_value=0, max_value=100,
                                           value=5, step=1)

        with col2:
            total_floor_count = st.number_input("4. Всего этажей в здании", min_value=1, max_value=60, value=6, step=1)
            floor_no = st.number_input("5. Этаж объекта (0 — цоколь/первый)", min_value=0, max_value=60, value=2,
                                       step=1)
            tom = st.number_input("6. Дней на рынке (планируемый срок продажи)", min_value=0, max_value=365, value=30,
                                  step=1)

        st.subheader("2. Локация и характеристики дома")
        col3, col4 = st.columns(2)
        with col3:
            city_name = st.selectbox("7. Город расположения", options=metadata["cities"])
            district_name = st.selectbox("8. Район", options=metadata["districts"])
        with col4:
            sub_type_name = st.selectbox("9. Тип недвижимости", options=metadata["subtypes"])
            heating_type_name = st.selectbox("10. Тип системы отопления", options=metadata["heatings"])

        submit_button = st.form_submit_button("Рассчитать стоимость")

    if submit_button:
        if floor_no > total_floor_count:
            st.error("Ошибка валидации: этаж объекта не может превышать этажность здания.")
        else:
            payload = {
                "size": float(size),
                "room_count": int(room_count),
                "building_age": int(building_age),
                "floor_no": int(floor_no),
                "total_floor_count": int(total_floor_count),
                "tom": int(tom),
                "city": city_name,
                "district": district_name,
                "sub_type": sub_type_name,
                "heating_type": heating_type_name,
            }

            try:
                with st.spinner("Выполняется расчет стоимости..."):
                    res = requests.post(f"{API_URL}/predict", json=payload, timeout=5)

                if res.status_code == 200:
                    data = res.json()
                    price = data["predicted_price"]
                    interval = data["confidence_interval"]

                    st.success(f"### Прогнозируемая стоимость: {price:,.0f} TRY")
                    st.info(
                        f"**Ожидаемый рыночный диапазон (±{interval['mape']:.1f}%):** "
                        f"от **{interval['lower']:,.0f} TRY** до **{interval['upper']:,.0f} TRY** "
                        f"(Расчетная погрешность: ±{interval['margin']:,.0f} TRY)"
                    )
                else:
                    st.error(f"Ошибка бэкенда: {res.json().get('detail')}")

            except Exception as e:
                st.error(f"Не удалось связаться с бэкендом: {e}")


# ==========================================
# ВКЛАДКА 2: Дашборд и аналитика
# ==========================================
@st.cache_data
def load_dashboard_data():
    try:
        return pd.read_csv("housing.csv")
    except Exception:
        return None


with tab_dashboard:
    st.title("Аналитический дашборд рынка недвижимости")

    df_dash = load_dashboard_data()

    if df_dash is None:
        st.warning("Файл 'housing.csv' не найден. Выполните ячейку сохранения данных в блокноте.")
    else:
        cities_avail = sorted([str(c) for c in df_dash["city"].dropna().unique().tolist()])

        st.subheader("Панель фильтров")

        # Кнопки быстрого выбора
        btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 3])
        if "selected_cities" not in st.session_state:
            st.session_state.selected_cities = cities_avail[:5]

        if btn_col1.button("Выбрать ТОП-5 городов"):
            st.session_state.selected_cities = cities_avail[:5]
        if btn_col2.button("Сбросить выбор"):
            st.session_state.selected_cities = []
        if btn_col3.button("Выбрать все города"):
            st.session_state.selected_cities = cities_avail

        selected_cities = st.multiselect(
            "Города для выборки:", options=cities_avail, default=st.session_state.selected_cities
        )

        f_col1, f_col2 = st.columns(2)
        min_p, max_p = float(df_dash["price"].min()), float(df_dash["price"].quantile(0.98))
        with f_col1:
            p_range = st.slider("Диапазон цен (TRY):", min_value=min_p, max_value=max_p, value=(min_p, max_p),
                                format="%.0f")
        with f_col2:
            s_range = st.slider("Диапазон площади (кв. м):", min_value=20.0, max_value=500.0, value=(20.0, 350.0))

        mask = (
                (df_dash["city"].astype(str).isin(selected_cities)) &
                (df_dash["price"].between(p_range[0], p_range[1])) &
                (df_dash["size"].between(s_range[0], s_range[1]))
        )
        df_filtered = df_dash[mask]

        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Найдено объектов", f"{len(df_filtered):,}")
        m2.metric("Медианная цена", f"{df_filtered['price'].median():,.0f} TRY" if len(df_filtered) > 0 else "0 TRY")
        m3.metric("Средняя площадь", f"{df_filtered['size'].mean():.1f} кв. м" if len(df_filtered) > 0 else "0 кв. м")
        m4.metric("Медианная цена за м²",
                  f"{df_filtered['price_per_m2'].median():,.0f} TRY" if len(df_filtered) > 0 else "0 TRY")

        st.markdown("---")
        st.subheader("Визуальный анализ выборки")

        sample_plot = df_filtered.sample(min(2500, len(df_filtered)), random_state=42) if len(
            df_filtered) > 2500 else df_filtered

        row1_1, row1_2 = st.columns(2)
        with row1_1:
            fig_scatter = px.scatter(
                sample_plot, x="size", y="price", color="city",
                hover_data=["room_count", "sub_type"],
                labels={"size": "Площадь (кв. м)", "price": "Цена (TRY)", "city": "Город"},
                title="1. Взаимосвязь цены и площади объектов",
                log_y=True
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

        with row1_2:
            fig_box = px.box(
                df_filtered, x="city", y="price", color="city",
                labels={"city": "Город", "price": "Цена (TRY)"},
                title="2. Распределение цен по городам",
                log_y=True
            )
            st.plotly_chart(fig_box, use_container_width=True)

        row2_1, row2_2 = st.columns(2)
        with row2_1:
            sub_counts = df_filtered["sub_type"].value_counts().reset_index()
            sub_counts.columns = ["sub_type", "count"]
            fig_pie = px.pie(
                sub_counts, names="sub_type", values="count",
                title="3. Структура предложения по типам недвижимости",
                hole=0.4
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with row2_2:
            m2_by_city = df_filtered.groupby("city")["price_per_m2"].median().sort_values(ascending=False).reset_index()
            fig_bar = px.bar(
                m2_by_city, x="city", y="price_per_m2", color="city",
                labels={"city": "Город", "price_per_m2": "Медиана цены за м² (TRY)"},
                title="4. Медианная стоимость кв. метра по городам"
            )
            st.plotly_chart(fig_bar, use_container_width=True)

# ==========================================
# ВКЛАДКА 3: Справка (СИНХРОНИЗИРОВАНЫ ВСЕ 10 ПОЛЕЙ)
# ==========================================
with tab_help:
    st.title("Справка и документация проекта")
    st.markdown("""
    ### 1. Назначение системы
    Веб-приложение разработано для оценки рыночной стоимости объектов жилой недвижимости Турции на основе алгоритмов машинного обучения.

    ### 2. Описание входных параметров формы (10 характеристик):
    1. **Общая площадь (кв. м)**: общая площадь помещения в квадратных метрах (допустимый диапазон от 15 до 800 кв. м).
    2. **Количество комнат**: общее число жилых комнат, спален и гостиных (целое число от 1 до 20).
    3. **Возраст здания**: возраст постройки в годах (0 — новое сданное здание).
    4. **Всего этажей в здании**: общая этажность дома (от 1 до 60).
    5. **Этаж объекта**: фактический этаж расположения квартиры (0 — цоколь/первый этаж).
    6. **Дней на рынке (TOM)**: планируемый срок экспозиции объявления в днях (от 0 до 365).
    7. **Город**: административный центр региона нахождения объекта.
    8. **Район**: муниципальный район или округ внутри выбранного города.
    9. **Тип недвижимости**: классификация объекта (Квартира, Вилла, Частный дом, Резиденция, Дача).
    10. **Тип отопления**: система обогрева (Индивидуальный котел Kombi, Кондиционер, Центральное и др.).

    ### 3. Используемая модель машинного обучения
    * **Алгоритм**: Ансамбль деревьев решений (Random Forest Regressor) с нормализацией через RobustScaler и One-Hot кодированием категорий в рамках единого Scikit-Learn Pipeline.
    * **Качество модели на отложенной тестовой выборке (Test Set)**:
        * Коэффициент детерминации (R²): **0.3543**;
        * Относительная погрешность (MAPE): **29.18%**;
        * Средняя абсолютная ошибка (MAE): **194 788 TRY**.

    ### 4. Ограничения модели
    * Базовая регрессионная модель обучена на сделках купли-продажи;
    * Модель не учитывает субъективные характеристики: вид из окон, дизайнерский ремонт, шумность района;
    * Для редких элитных объектов стоимостью свыше 30 000 000 TRY погрешность может возрастать.
    """)