from flask import redirect, url_for
from flask_login import logout_user, current_user
from app import create_app

app = create_app()

@app.route("/")
def default():
    return redirect(url_for("member.login"))

@app.route("/logout")
def logout():
    role = current_user.role
    logout_user()
    return redirect(url_for(f"{role}.login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
