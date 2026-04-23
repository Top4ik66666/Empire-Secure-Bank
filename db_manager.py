import os
import random
import time

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
_SCHEMA_ENSURED = False

# HTTP-прокси для api.telegram.org (ошибка 101 / блокировка без прокси).
# Свой прокси: TELEGRAM_HTTP_PROXY=http://host:port
# Прямое подключение: TELEGRAM_HTTP_PROXY=
_DEFAULT_TELEGRAM_HTTP_PROXY = os.getenv("TELEGRAM_HTTP_PROXY", "")


def telegram_http_proxies():
    raw = os.getenv("TELEGRAM_HTTP_PROXY")
    if raw is not None and str(raw).strip() == "":
        return None
    url = (raw or _DEFAULT_TELEGRAM_HTTP_PROXY).strip()
    return {"http": url, "https": url}


def get_connection(max_retries=10, retry_delay=2):
    last_error = None
    for _ in range(max_retries):
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
            last_error = e
            print(f"База еще не готова, ждем {retry_delay} секунды... ({e})")
            time.sleep(retry_delay)
    raise RuntimeError(
        f"Не удалось подключиться к БД после {max_retries} попыток: {last_error}"
    )


def ensure_schema():
    global _SCHEMA_ENSURED
    if _SCHEMA_ENSURED:
        return
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20)"
        )
        cur.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE"
        )
        cur.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS sms_code VARCHAR(6)"
        )
        cur.execute(
            "ALTER TABLE credit_requests ADD COLUMN IF NOT EXISTS amount TEXT DEFAULT '500 000'"
        )
        cur.execute(
            "ALTER TABLE credit_requests ADD COLUMN IF NOT EXISTS term_months INTEGER"
        )
        cur.execute(
            "ALTER TABLE credit_requests ADD COLUMN IF NOT EXISTS comment TEXT DEFAULT ''"
        )
        cur.execute(
            "ALTER TABLE credit_requests ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()"
        )
        conn.commit()
        _SCHEMA_ENSURED = True
    finally:
        cur.close()
        conn.close()


def register_user_in_db(login, password, code, phone=None):
    ensure_schema()
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password, sms_code, phone) VALUES (%s, %s, %s, %s)",
            (login, password, code, phone),
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
    ensure_schema()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, phone, sms_code FROM users ORDER BY id DESC")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return users


def check_user_credentials(login, password):
    ensure_schema()
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
    ensure_schema()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT balance, phone, is_verified FROM users WHERE username = %s",
        (username,),
    )
    res = cur.fetchone()
    cur.close()
    conn.close()
    if not res:
        return {"balance": 0, "phone": "", "is_verified": False}
    return {
        "balance": res[0],
        "phone": res[1] or "",
        "is_verified": bool(res[2]),
    }


def get_user_credits(username):
    ensure_schema()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'credit_requests'
        """
    )
    available = {row[0] for row in cur.fetchall()}

    # Backward-compatible query for old DB schemas.
    if {"amount", "term_months", "created_at"}.issubset(available):
        cur.execute(
            """
            SELECT type, amount, term_months, status, created_at
            FROM credit_requests
            WHERE username = %s
            ORDER BY created_at DESC, id DESC
            """,
            (username,),
        )
    else:
        cur.execute(
            """
            SELECT type, '500 000' AS amount, NULL AS term_months, status, NULL AS created_at
            FROM credit_requests
            WHERE username = %s
            ORDER BY id DESC
            """,
            (username,),
        )
    res = cur.fetchall()
    cur.close()
    conn.close()
    return res


def add_credit_request(username, type, amount="500 000", term_months=None, comment=""):
    ensure_schema()
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO credit_requests (username, type, amount, term_months, comment)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (username, type, str(amount), term_months, comment),
        )
        request_id = cur.fetchone()[0]
        conn.commit()
        send_admin_notification(
            (
                f"Новая заявка!\n"
                f"Юзер: {username}\n"
                f"Тип: {type}\n"
                f"Сумма: {amount}\n"
                f"Срок: {term_months or '-'} мес."
            ),
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
