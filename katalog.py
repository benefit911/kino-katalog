# Каталог фильмов для мини-приложения Telegram.
# Этот файл живёт на бесплатном хостинге (Render), поэтому:
#   - ключ Кинопоиска спрятан здесь, а не в браузере;
#   - адрес постоянный, туннель не нужен;
#   - работает даже когда ваш компьютер выключен.
#
# Запуск на компьютере: python katalog.py  (откроется на http://127.0.0.1:5000)
# Запуск на хостинге: хостинг сам запускает этот файл и задаёт порт в PORT.

import os
import requests
from flask import Flask, jsonify, request

KP_KEY = "V7M9NP1-0PW4JD0-M3VAMTB-PF0RPWP"
KP_URL = "https://api.poiskkino.dev/v1.5"
headers = {"X-API-KEY": KP_KEY}

app = Flask(__name__)

CATALOG_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Каталог</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
  :root {
    --bg: var(--tg-theme-bg-color, #0f1115);
    --text: var(--tg-theme-text-color, #ffffff);
    --hint: var(--tg-theme-hint-color, #8a8f98);
    --btn: var(--tg-theme-button-color, #2ea6ff);
    --card: var(--tg-theme-secondary-bg-color, #1a1d24);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
  body { background: var(--bg); color: var(--text); font-family: -apple-system, system-ui, sans-serif; padding: 12px; }
  h1 { font-size: 20px; margin: 2px 0 12px; }
  .search { display: flex; gap: 8px; margin-bottom: 14px; }
  input { flex: 1; padding: 10px 12px; border: none; border-radius: 10px; background: var(--card);
          color: var(--text); font-size: 15px; outline: none; }
  input::placeholder { color: var(--hint); }
  button { padding: 10px 14px; border: none; border-radius: 10px; background: var(--btn);
           color: #fff; font-size: 15px; font-weight: 600; }
  .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
  .film { cursor: pointer; }
  .film img { width: 100%; border-radius: 8px; aspect-ratio: 2/3; object-fit: cover;
              background: var(--card); display: block; }
  .film .name { font-size: 11px; margin-top: 4px; line-height: 1.25;
                display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .film .meta { font-size: 10px; color: var(--hint); }
  .status { color: var(--hint); font-size: 13px; text-align: center; padding: 20px 0; }
</style>
</head>
<body>
<h1>Каталог</h1>
<div class="search">
  <input id="q" placeholder="Название фильма или сериала">
  <button onclick="find()">Найти</button>
</div>
<div id="grid" class="grid"></div>
<div id="status" class="status">загружаем…</div>

<script>
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

function esc(s) {
  return (s || "").replace(/[&<>"']/g, c =>
    ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

function card(m) {
  const rating = m.rating ? "⭐ " + Number(m.rating).toFixed(1) : "";
  const poster = m.poster
    ? '<img src="' + esc(m.poster) + '" onerror="this.style.visibility=\\'hidden\\'">'
    : '';
  return '<div class="film" onclick="pick(' + m.id + ')">' + poster +
         '<div class="name">' + esc(m.name) + '</div>' +
         '<div class="meta">' + esc(m.year || "") + " " + rating + '</div></div>';
}

function render(list) {
  const grid = document.getElementById("grid");
  const status = document.getElementById("status");
  if (!list.length) { status.textContent = "Ничего не нашлось"; grid.innerHTML = ""; return; }
  status.textContent = "";
  grid.innerHTML = list.map(card).join("");
}

function load(q, attempt) {
  attempt = attempt || 1;
  const status = document.getElementById("status");
  status.textContent = "загружаем…";
  fetch("/api/movies?q=" + encodeURIComponent(q || ""))
    .then(r => {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(d => render(d.movies || []))
    .catch(() => {
      // хостинг может просыпаться до минуты — пробуем настойчиво
      if (attempt < 10) {
        status.textContent = "сервер просыпается, попытка " + attempt + " из 10…";
        setTimeout(() => load(q, attempt + 1), 3000);
      } else {
        status.innerHTML = 'Сервер не ответил. <span id="again" style="color:var(--btn);text-decoration:underline">Повторить</span>';
        document.getElementById("again").onclick = () => load(document.getElementById("q").value.trim(), 1);
      }
    });
}

function find() { load(document.getElementById("q").value.trim()); }

function pick(id) {
  // отправляем выбранный фильм в чат — боту придёт сообщение
  tg.sendData(JSON.stringify({action: "movie", id: id}));
}

document.getElementById("q").addEventListener("keydown", e => { if (e.key === "Enter") find(); });

load("");
</script>
</body>
</html>"""


def build_api_json(items):
    out = []
    for m in items:
        if not (m.get("name") or m.get("alternativeName")):
            continue
        rating = m.get("rating") or {}
        poster = m.get("poster") or {}
        out.append({
            "id": m.get("id"),
            "name": m.get("name") or m.get("alternativeName"),
            "year": m.get("year"),
            "rating": rating.get("kp"),
            "poster": poster.get("url") if isinstance(poster, dict) else poster,
        })
    return out


def fetch_movies(q, limit):
    """Запрос к базе Кинопоиска."""
    if q:
        response = requests.get(
            KP_URL + "/movie/search", headers=headers,
            params={"query": q, "limit": limit, "page": 1}, timeout=20)
    else:
        response = requests.get(
            KP_URL + "/movie", headers=headers,
            params={"lists": "top250", "sortField": "rating.kp", "sortType": "-1",
                    "limit": limit}, timeout=20)
    response.raise_for_status()
    return response.json().get("docs", [])


@app.route("/")
def index():
    return CATALOG_HTML


@app.route("/ping")
def ping():
    return "ok"


@app.route("/api/movies")
def api_movies():
    q = (request.args.get("q") or "").strip()
    try:
        items = fetch_movies(q, 20)
    except Exception:
        return jsonify({"movies": []})
    return jsonify({"movies": build_api_json(items)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("Каталог запущен на порту", port)
    app.run(host="0.0.0.0", port=port)
