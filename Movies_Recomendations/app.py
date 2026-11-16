import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Рекомендательная система фильмов", layout="wide")

st.markdown("""
<style>
div[data-testid="stImage"] img {
    height: 260px !important;
    width: 100% !important;
    object-fit: cover !important;
    border-radius: 6px;
}
.movie-title {
    font-size: 14px;
    font-weight: bold;
    height: 40px;
    overflow: hidden;
    margin-top: 6px;
    margin-bottom: 2px;
    line-height: 1.2;
}
.movie-genre {
    font-size: 12px;
    color: #888;
    height: 34px;
    overflow: hidden;
    margin-bottom: 6px;
    line-height: 1.2;
}
</style>
""", unsafe_allow_html=True)

st.title("Рекомендательная система фильмов")

@st.cache_data(ttl=60)
def get_movies():
    try:
        res = requests.get(f"{API_URL}/movies", timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return []

movies_data = get_movies()
movie_titles = [m["title"] for m in movies_data]

def display_movies_grid(movies, score_name="Оценка", show_score=True):
    if not movies:
        st.warning("Фильмы не найдены.")
        return

    chunk_size = 5
    for i in range(0, len(movies), chunk_size):
        row_movies = movies[i:i + chunk_size]
        cols = st.columns(chunk_size)
        
        for idx, movie in enumerate(row_movies):
            with cols[idx]:
                poster = movie.get("poster_url")
                if poster:
                    st.image(poster, use_container_width=True)
                else:
                    st.write("[Нет постера]")

                title_text = f"{movie.get('title')} ({movie.get('year')})"
                st.markdown(f'<div class="movie-title">{title_text}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="movie-genre">{movie.get("genres", "")}</div>', unsafe_allow_html=True)

                if show_score:
                    score = movie.get("score") or movie.get("w_score") or movie.get("rating_kp", 0)
                    st.info(f"{score_name}: {score:.3f}")

tab_catalog, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Каталог",
    "Топ-10",
    "Похожие (коллаборативные)",
    "По сюжету (контентные)",
    "Персональные",
    "Оценить фильм",
    "Справка"
])

# Каталог
with tab_catalog:
    st.subheader("Полный каталог фильмов")
    search_query = st.text_input("Поиск по названию:", "")
    filtered = [m for m in movies_data if search_query.lower() in m["title"].lower()] if search_query else movies_data
    st.caption(f"Всего фильмов: {len(filtered)}")
    display_movies_grid(filtered, show_score=False)

# Топ-10
with tab1:
    st.subheader("Топ-10 популярных фильмов")
    if st.button("Загрузить Топ-10"):
        res = requests.get(f"{API_URL}/recommend/top").json()
        display_movies_grid(res, score_name="Балл")

# Коллаборативная фильтрация по фильму
with tab2:
    st.subheader("Коллаборативная фильтрация: что смотрели вместе с этим фильмом")
    if movie_titles:
        selected_film = st.selectbox("Выберите фильм:", movie_titles, key="cb_movie")
        if st.button("Найти похожие по оценкам"):
            res = requests.get(f"{API_URL}/recommend/by-movie", params={"title": selected_film}).json()
            display_movies_grid(res, score_name="Сходство")

# Контентная фильтрация
with tab3:
    st.subheader("Контентная фильтрация: похожие по жанрам и описанию")
    if movie_titles:
        selected_film_content = st.selectbox("Выберите фильм:", movie_titles, key="content_movie")
        if st.button("Найти по сюжету"):
            res = requests.get(f"{API_URL}/recommend/by-content", params={"title": selected_film_content}).json()
            display_movies_grid(res, score_name="Сходство текста")

# Персональные рекомендации
with tab4:
    st.subheader("Персональная подборка для пользователя")
    user_id = st.number_input("ID пользователя:", min_value=1, max_value=1000, value=1, step=1)
    if st.button("Сформировать рекомендации"):
        res = requests.get(f"{API_URL}/recommend/personal/{user_id}").json()
        display_movies_grid(res, score_name="Прогноз")

# Оценка фильма и сохранение в БД
with tab5:
    st.subheader("Добавление оценки в базу данных")
    with st.form("rating_form"):
        r_user_id = st.number_input("Ваш User ID:", min_value=1, value=1, step=1)
        r_movie_title = st.selectbox("Фильм:", movie_titles)
        r_score = st.slider("Ваша оценка:", min_value=1.0, max_value=10.0, value=8.0, step=0.5)
        submitted = st.form_submit_button("Сохранить оценку")

        if submitted:
            movie_obj = next((m for m in movies_data if m["title"] == r_movie_title), None)
            if movie_obj:
                payload = {
                    "user_id": int(r_user_id),
                    "movie_id": movie_obj["id"],
                    "rating": float(r_score)
                }
                res = requests.post(f"{API_URL}/rate", json=payload)
                if res.status_code == 200:
                    st.success(f"Оценка {r_score} для фильма «{r_movie_title}» успешно сохранена!")
                else:
                    st.error("Ошибка при сохранении оценки.")

# Справка по API
with tab6:
    st.subheader("Справочник команд и параметров системы")
    try:
        help_info = requests.get(f"{API_URL}/help").json()
        endpoints = help_info.get("endpoints", {})
        for ep, desc in endpoints.items():
            st.markdown(f"`{ep}` — {desc}")
    except Exception:
        st.error("Не удалось подключиться к API для загрузки справки.")