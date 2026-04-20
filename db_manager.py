import os
import random
import time

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")

# HTTP-прокси для api.telegram.org (ошибка 101 / блокировка без прокси).
# Свой прокси: TELEGRAM_HTTP_PROXY=http://host:port
# Прямое подключение: TELEGRAM_HTTP_PROXY=
_DEFAULT_TELEGRAM_HTTP_PROXY = "http://45.67.215.18:80"


def telegram_http_proxies():
    raw = os.getenv("TELEGRAM_HTTP_PROXY")
    if raw is not None and str(raw).strip() == "":
        return None
    url = (raw or _DEFAULT_TELEGRAM_HTTP_PROXY).strip()
    return {"http": url, "https": url}


def get_connection():
    while True:
        try:
            conn = psycopg2.connect(
                dbname=os.getenv("DB_NAME", "bank_db"),
                user=os.getenv("DB_USER", "admin_user"),
                password=os.getenv("DB_PASSWORD", "password123"),
                host=os.getenv("DB_HOST", "db"),
                port="5432",
            )
            return conn
        except psycopg2.OperationalError as e:
            print(f"База еще не готова, ждем 2 секунды... ({e})")
            time.sleep(2)


def register_user_in_db(login, password, code):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password, sms_code) VALUES (%s, %s, %s)",
            (login, password, code),
        )
        conn.commit()
        return True
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        print(f"Пользователь {login} уже существует!")
        return False
    finally:
        cur.close()
        conn.close()


def start_registration(login, password, phone):
    code = str(random.randint(100000, 999999))
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, password, phone, sms_code) VALUES (%s, %s, %s, %s) RETURNING id",
        (login, password, phone, code),
    )
    user_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return user_id, code


def get_all_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, phone, sms_code FROM users ORDER BY id DESC")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return users


def check_user_credentials(login, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM users WHERE username = %s AND password = %s",
        (login, password),
    )
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user


def get_user_data(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT balance FROM users WHERE username = %s", (username,))
    res = cur.fetchone()
    cur.close()
    conn.close()
    return {"balance": res[0] if res else 0}


def get_user_credits(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT type, status FROM credit_requests WHERE username = %s",
        (username,),
    )
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res


def add_credit_request(username, type):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO credit_requests (username, type) VALUES (%s, %s) RETURNING id",
            (username, type),
        )
        request_id = cur.fetchone()[0]
        conn.commit()
        send_admin_notification(
            f"Новая заявка!\nЮзер: {username}\nТип: {type}",
            request_id=request_id,
        )
        return True
    except Exception as e:
        print(f"Ошибка при записи кредита: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()


def approve_credit(request_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE credit_requests SET status = 'Одобрено' WHERE id = %s",
        (request_id,),
    )
    conn.commit()
    cur.close()
    conn.close()


def send_admin_notification(text, request_id=None):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("ADMIN_CHAT_ID")

    proxies = telegram_http_proxies()

    if not token or not chat_id:
        return

    payload = {"chat_id": chat_id, "text": text}
    if request_id is not None:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [
                    {"text": "Одобрить", "callback_data": f"ap:{request_id}"},
                    {"text": "Отклонить", "callback_data": f"rj:{request_id}"},
                ]
            ]
        }

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(
            url,
            json=payload,
            timeout=10,
            proxies=proxies,
        )
    except Exception as e:
        print(f"Ошибка отправки в TG: {e}")
