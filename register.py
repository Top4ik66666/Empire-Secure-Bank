import random
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from db_manager import check_user_credentials, get_connection, register_user_in_db

register_bp = Blueprint("register", __name__)


@register_bp.route("/register-page", methods=["GET"])
def register_page():
    return render_template("register.html")


@register_bp.route("/login-page", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        login = request.form.get("login")
        password = request.form.get("password")
        if check_user_credentials(login, password):
            session["user_id"] = login
            return redirect(url_for("index"))
        flash("Неверный логин или пароль.")
        return redirect(url_for("register.login_page"))
    return render_template("login.html")


@register_bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.pop("user_id", None)
    session.pop("pending_user_login", None)
    return redirect(url_for("index"))


@register_bp.route("/create-account", methods=["POST"])
def create_account():
    login = request.form.get("new_login")
    pwd = request.form.get("new_password")
    phone = request.form.get("phone", "").strip()
    code = str(random.randint(100000, 999999))

    print(f"\n!!! ВНИМАНИЕ, КОД ДЛЯ {login}: {code} !!!\n")

    try:
        if register_user_in_db(login, pwd, code, phone):
            session["pending_user_login"] = login
            return redirect(url_for("register.verify_page"))
        return "Ошибка: не удалось сохранить в базу."
    except Exception as e:
        return f"Ошибка регистрации (возможно, логин занят): {e}"


@register_bp.route("/admin-zone")
def admin_zone():
    from db_manager import get_all_users

    try:
        users_data = get_all_users()
        return render_template("admin.html", users=users_data)
    except Exception as e:
        return f"Ошибка доступа к админ-панели: {e}", 500


@register_bp.route("/verify-page")
def verify_page():
    return render_template("verify.html")


@register_bp.route("/verify-code", methods=["POST"])
def verify_code():
    code_entered = request.form.get("sms_code")
    username = session.get("pending_user_login")
    if not username:
        return redirect(url_for("register.register_page"))

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT sms_code FROM users WHERE username = %s", (username,))
    result = cur.fetchone()
    if result and str(result[0]) == str(code_entered):
        cur.execute(
            "UPDATE users SET is_verified = TRUE WHERE username = %s",
            (username,),
        )
        conn.commit()
        cur.close()
        session.pop("pending_user_login", None)
        session["user_id"] = username
        conn.close()
        return redirect(url_for("index"))
    cur.close()
    conn.close()
    return "Неверный код!"


@register_bp.route("/login-process", methods=["POST"])
def login_process():
    login = request.form.get("login")
    pwd = request.form.get("password")

    if check_user_credentials(login, pwd):
        session["user_id"] = login
        return redirect(url_for("index"))
    return (
        f"Неверный логин или пароль! <a href=\"{url_for('register.login_page')}\">Назад</a>"
    )
