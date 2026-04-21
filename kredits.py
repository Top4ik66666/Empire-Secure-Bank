from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from db_manager import add_credit_request, get_user_credits, get_user_data

kredits_bp = Blueprint("kredits", __name__)


LOAN_CATALOG = {
    "consumer": {
        "name": "Потребительский кредит",
        "rate": "от 5.9%",
        "max_amount": "до 5 000 000 ₽",
    },
    "auto": {"name": "Автокредит", "rate": "от 8.5%", "max_amount": "до 8 000 000 ₽"},
    "mortgage": {"name": "Ипотека", "rate": "от 7.3%", "max_amount": "до 30 000 000 ₽"},
}


@kredits_bp.route("/dashboard")
def dashboard():
    user = session.get("user_id")
    if not user:
        return redirect(url_for("register.register_page"))
    user_info = get_user_data(user)
    credits = get_user_credits(user)
    return render_template("dashboard.html", username=user, user_info=user_info, credits=credits)


@kredits_bp.route("/loans")
def loans_page():
    user = session.get("user_id")
    return render_template("loans.html", username=user, loan_catalog=LOAN_CATALOG)


@kredits_bp.route("/apply-credit/<string:c_type>", methods=["GET", "POST"])
def apply_credit(c_type):
    user = session.get("user_id")
    if not user:
        return redirect(url_for("register.login_page"))
    if c_type not in LOAN_CATALOG:
        return redirect(url_for("kredits.loans_page"))

    if request.method == "POST":
        amount = request.form.get("amount", "").strip()
        term_months = request.form.get("term_months", "").strip()
        comment = request.form.get("comment", "").strip()

        if not amount or not term_months:
            flash("Заполните обязательные поля: сумма и срок.")
            return redirect(url_for("kredits.apply_credit", c_type=c_type))
        if not term_months.isdigit():
            flash("Срок должен быть числом в месяцах.")
            return redirect(url_for("kredits.apply_credit", c_type=c_type))

        if add_credit_request(user, c_type, amount, int(term_months), comment):
            return render_template(
                "apply_success.html",
                username=user,
                product=LOAN_CATALOG[c_type]["name"],
            )
        flash("Ошибка при подаче заявки. Попробуйте позже.")
        return redirect(url_for("kredits.apply_credit", c_type=c_type))

    return render_template(
        "apply_credit.html",
        username=user,
        c_type=c_type,
        product=LOAN_CATALOG[c_type],
    )
