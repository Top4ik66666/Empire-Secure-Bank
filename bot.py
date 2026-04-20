"""
Банковский админ-бот (pyTelegramBotAPI).

- Push-уведомления о новых заявках приходят с кнопками «Одобрить» / «Отклонить»
  (отправляет веб через db_manager.send_admin_notification).
- Здесь же: long polling, обработка нажатий и команда /status.

Прокси к api.telegram.org: см. db_manager.telegram_http_proxies() (TELEGRAM_HTTP_PROXY).

Запуск: python bot.py. Не поднимайте второй процесс с тем же TELEGRAM_TOKEN.
"""
import os

import telebot
import telebot.apihelper as apihelper
from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

from db_manager import get_connection, telegram_http_proxies

load_dotenv()

PENDING = "На рассмотрении"
APPROVED = "Одобрено"
REJECTED = "Отклонено"

TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

if not TOKEN or not ADMIN_CHAT_ID:
    raise SystemExit("Задайте TELEGRAM_TOKEN и ADMIN_CHAT_ID в .env")

_tg_proxy = telegram_http_proxies()
if _tg_proxy:
    apihelper.proxy = _tg_proxy

bot = telebot.TeleBot(TOKEN)


def _is_admin_chat(chat_id: int) -> bool:
    return str(chat_id) == str(ADMIN_CHAT_ID)


def _is_status_panel_text(text: str) -> bool:
    return bool(text and "Новых заявок:" in text)


def _fetch_pending():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, username, type, COALESCE(amount, '')
        FROM credit_requests
        WHERE status = %s
        ORDER BY id DESC
        LIMIT 30
        """,
        (PENDING,),
    )
    rows = cur.fetchall()
    cur.execute(
        "SELECT COUNT(*) FROM credit_requests WHERE status = %s",
        (PENDING,),
    )
    (total,) = cur.fetchone()
    cur.close()
    conn.close()
    return total, rows


def _set_status(request_id: int, status: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE credit_requests SET status = %s WHERE id = %s AND status = %s",
        (status, request_id, PENDING),
    )
    updated = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return updated > 0


def _build_status_message_and_keyboard():
    total, rows = _fetch_pending()
    if total == 0:
        return "Новых заявок на кредит нет.", None

    lines = [f"Новых заявок: {total}\n"]
    for rid, username, ctype, amount in rows:
        lines.append(
            f"#{rid} — {username} — {ctype} — {amount or '—'}"
        )
    if total > len(rows):
        lines.append(
            f"\n(Показаны последние {len(rows)}; сначала обработайте их, затем снова /status.)"
        )

    markup = InlineKeyboardMarkup(row_width=2)
    for rid, username, ctype, _ in rows:
        markup.row(
            InlineKeyboardButton(
                f"Одобрить #{rid}",
                callback_data=f"ap:{rid}",
            ),
            InlineKeyboardButton(
                f"Отклонить #{rid}",
                callback_data=f"rj:{rid}",
            ),
        )

    return "\n".join(lines), markup


@bot.message_handler(commands=["start"])
def cmd_start(message):
    if not _is_admin_chat(message.chat.id):
        return
    bot.reply_to(
        message,
        "Команды:\n"
        "/status — список новых заявок и кнопки.\n\n"
        "О новых заявках бот также пришлёт сообщение с сайта.",
    )


@bot.message_handler(commands=["status"])
def cmd_status(message):
    if not _is_admin_chat(message.chat.id):
        return
    text, markup = _build_status_message_and_keyboard()
    bot.reply_to(message, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data and c.data[:3] in ("ap:", "rj:"))
def on_decision(call):
    if not _is_admin_chat(call.from_user.id):
        bot.answer_callback_query(call.id, "Нет доступа.", show_alert=True)
        return

    try:
        action, rid_s = call.data.split(":", 1)
        request_id = int(rid_s)
    except (ValueError, AttributeError):
        bot.answer_callback_query(call.id, "Неверные данные.", show_alert=True)
        return

    if action == "ap":
        ok = _set_status(request_id, APPROVED)
        note = f"Заявка #{request_id} одобрена." if ok else "Заявка не найдена или уже обработана."
    else:
        ok = _set_status(request_id, REJECTED)
        note = f"Заявка #{request_id} отклонена." if ok else "Заявка не найдена или уже обработана."

    msg_text = call.message.text or ""

    if _is_status_panel_text(msg_text):
        text, markup = _build_status_message_and_keyboard()
        try:
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
            )
        except ApiTelegramException:
            pass
    elif ok:
        suffix = "\n\nОдобрено" if action == "ap" else "\n\nОтклонено"
        try:
            bot.edit_message_text(
                msg_text + suffix,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=None,
            )
        except ApiTelegramException:
            pass

    bot.answer_callback_query(call.id, note, show_alert=not ok)


def main():
    print("Бот запущен (уведомления + кнопки, /status).")
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    main()
