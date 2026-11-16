import sqlite3
import requests
import time

API_URL = "http://127.0.0.1:8000"
TEST_USER = 999
DB_NAME = "cinema.db"

# Сброс оценок тестового пользователя
conn = sqlite3.connect(DB_NAME)
conn.cursor().execute("DELETE FROM ratings WHERE user_id = ?", (TEST_USER,))
conn.commit()
conn.close()

# 2. Получаем каталог
movies = requests.get(f"{API_URL}/movies").json()

def find_movie_id(name):
    for m in movies:
        if name.lower() in m["title"].lower():
            return m["id"], m["title"]
    return None, None

def rate(title, score=10.0):
    m_id, real_title = find_movie_id(title)
    if m_id:
        res = requests.post(f"{API_URL}/rate", json={"user_id": TEST_USER, "movie_id": m_id, "rating": float(score)})
        if res.status_code == 200:
            print(f"  + Оценили: '{real_title}' на {score}")
        else:
            print(f"  ! Ошибка сервера: {res.text}")
    else:
        print(f"  - Не найден фильм: '{title}'")
    time.sleep(0.1)

def show_recommendations(header):
    print(f"\n{'='*15} {header} {'='*15}")
    res = requests.get(f"{API_URL}/recommend/personal/{TEST_USER}").json()
    for idx, m in enumerate(res[:5], 1):
        print(f"{idx}. {m['title']} ({m['year']})")
        print(f"   Жанры: {m['genres']}")
        print(f"   Прогноз: {m['score']}")

# === ЭТАП 1: ФАНТАСТИКА ===
print("--- ЭТАП 1: Пользователь любит фантастику и космос ---")
for f in ["Интерстеллар", "Матрица", "Аватар", "Мстители"]:
    rate(f, 10.0)

show_recommendations("РЕКОМЕНДАЦИИ ПОСЛЕ ФАНТАСТИКИ")

#=== ЭТАП 2: ДЕТЕКТИВЫ ===
print("\n--- ЭТАП 2: Пользователь начинает ставить десятки детективам ---")
for f in ["Шерлок Холмс", "Бойцовский клуб", "Законопослушный гражданин", "Игра"]:
    rate(f, 10.0)

show_recommendations("РЕКОМЕНДАЦИИ ПОСЛЕ ДЕТЕКТИВОВ")