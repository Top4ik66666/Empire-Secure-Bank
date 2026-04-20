import os

from flask import Flask, render_template, session

from kredits import kredits_bp
from register import register_bp

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-in-production")

app.register_blueprint(register_bp)
app.register_blueprint(kredits_bp)


@app.route("/")
def index():
    user = session.get("user_id")
    if user:
        from db_manager import get_user_credits, get_user_data

        user_info = get_user_data(user)
        credits = get_user_credits(user)
        return render_template(
            "home.html",
            username=user,
            balance=user_info["balance"],
            credits=credits,
        )
    return render_template("home.html", username=None, balance=0, credits=[])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
