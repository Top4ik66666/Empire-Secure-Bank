from flask import Blueprint, redirect, render_template, session, url_for

from db_manager import add_credit_request, get_user_credits, get_user_data

kredits_bp = Blueprint("kredits", __name__)


@kredits_bp.route("/dashboard")
def dashboard():
    user = session.get("user_id")
    if not user:
        return redirect(url_for("register.register_page"))
    user_info = get_user_data(user)
    credits = get_user_credits(user)
    return render_template(
        "home.html",
        username=user,
        balance=user_info["balance"],
        credits=credits,
    )


@kredits_bp.route("/apply-credit/<string:c_type>")
def apply_credit(c_type):
    user = session.get("user_id")
    if not user:
        return redirect(url_for("register.login_page"))

    if add_credit_request(user, c_type):
        return (
            f"<h1>Успех!</h1><p>Ваша заявка на {c_type} кредит принята. "
            f"<a href=\"{url_for('index')}\">Вернуться</a></p>"
        )
    return "Ошибка при подаче заявки. Попробуйте позже."
