import os
from flask import Flask, render_template, request, redirect, url_for, session, flash

import pyone

app = Flask(__name__, template_folder=".")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# --- Configuration -----------------------------------------------------
# ONE_XMLRPC: the URL of your OpenNebula master's XML-RPC endpoint.
# When running locally on master, this is usually http://localhost:2633/RPC2
# When deployed on Render/etc, point this at your ngrok/Cloudflare Tunnel URL
# that forwards to master's port 2633, e.g. https://xxxx.ngrok-free.app/RPC2
ONE_XMLRPC = os.environ.get("ONE_XMLRPC", "http://localhost:2633/RPC2")

# ONE_ADMIN_AUTH: "oneadmin:<password>" — used only server-side, for the
# actions that must run as admin (creating new user accounts). Never send
# this to the browser.
ONE_ADMIN_AUTH = os.environ.get("ONE_ADMIN_AUTH", "oneadmin:changeme")


def get_admin_client():
    return pyone.OneServer(ONE_XMLRPC, session=ONE_ADMIN_AUTH)


def get_user_client():
    return pyone.OneServer(ONE_XMLRPC, session=session["one_auth"])


# --- Routes --------------------------------------------------------------

@app.route("/")
def index():
    if "one_auth" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        try:
            client = pyone.OneServer(ONE_XMLRPC, session=f"{username}:{password}")
            client.userpool.info()  # test call to confirm credentials work
            session["one_auth"] = f"{username}:{password}"
            session["username"] = username
            return redirect(url_for("dashboard"))
        except Exception as e:
            flash(f"Login failed: {e}")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        admin = get_admin_client()
        try:
            # "core" auth driver = built-in username/password auth
            admin.user.allocate(username, password, "core", [])
            flash("Account created — you can log in now.")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Registration failed: {e}")
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if "one_auth" not in session:
        return redirect(url_for("login"))

    client = get_user_client()

    # -2 = only the logged-in user's own VMs; use -1 for filter flag "all"
    vm_pool = client.vmpool.info(-2, -1, -1, -1)
    vms = vm_pool.VM

    # Everyone can see the list of existing member accounts
    user_pool = client.userpool.info()
    users = user_pool.USER

    # Fetch available templates so the create-VM form can list them
    template_pool = client.templatepool.info(-2, -1, -1, -1)
    templates = template_pool.VMTEMPLATE

    return render_template(
        "dashboard.html",
        vms=vms,
        users=users,
        templates=templates,
        username=session["username"],
    )


@app.route("/vms/create", methods=["POST"])
def create_vm():
    if "one_auth" not in session:
        return redirect(url_for("login"))

    client = get_user_client()
    template_id = int(request.form["template_id"])
    vm_name = request.form["vm_name"]

    try:
        # instantiate(template_id, name, hold, extra_template, persistent)
        client.template.instantiate(template_id, vm_name, False, "", False)
        flash(f"VM '{vm_name}' creation requested.")
    except Exception as e:
        flash(f"VM creation failed: {e}")

    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
