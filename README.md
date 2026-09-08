# OneCloud — Web Interface for the OpenNebula Cluster

A small Flask app that lets members log in, create accounts, see who else
has access, and deploy VMs onto your master/worker1 cluster — all through
OpenNebula's XML-RPC API (via the `pyone` library), the same API FireEdge
itself uses.

## 1. Run it locally on master first (sanity check)

```bash
cd onecloud-app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# OpenNebula's XML-RPC endpoint is normally on port 2633 on master
export ONE_XMLRPC="http://localhost:2633/RPC2"
export ONE_ADMIN_AUTH="oneadmin:<your-oneadmin-password>"
export SECRET_KEY="something-random"

python3 app.py
```

Open `http://localhost:5000` in a browser on master. Log in with any
existing OpenNebula user (e.g. `oneadmin:<password>`), or register a new
account first.

If `pyone` can't connect, confirm the XML-RPC port:
```bash
sudo ss -tlnp | grep 2633
```

## 2. Expose master to the internet (so a deployed site can reach it)

Install ngrok (free tier) on **master**:
```bash
curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok
ngrok config add-authtoken <your-ngrok-token>   # free signup at ngrok.com
```

Tunnel OpenNebula's XML-RPC port:
```bash
ngrok http 2633
```

This gives you a public URL like `https://abcd1234.ngrok-free.app`. Your
deployed app's `ONE_XMLRPC` env var should be set to
`https://abcd1234.ngrok-free.app/RPC2` (note the free ngrok tier gives a
**new random URL every time you restart** — update the deployed app's env
var each time, or upgrade to a reserved domain if your plan allows it).

> Keep this ngrok session running on master for as long as you need the
> deployed site to work — closing the terminal kills the tunnel.

## 3. Deploy the web app itself (free hosting)

**Render.com (recommended, simplest for Flask):**
1. Push this `onecloud-app/` folder to a GitHub repo.
2. On Render: New → Web Service → connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add environment variables in Render's dashboard:
   - `ONE_XMLRPC` = your ngrok URL + `/RPC2`
   - `ONE_ADMIN_AUTH` = `oneadmin:<password>`
   - `SECRET_KEY` = any random string

Render gives you a public URL like `https://onecloud.onrender.com` —
that's what you share for "accessibility from any node."

**Alternatives:** Railway.app and Fly.io both have similar free-tier flows
if Render doesn't work for you.

## 4. Test from another node/network

From worker1, or a phone on mobile data, open the Render URL and confirm
you can log in, see the member list, and deploy a VM. Then check on
master:
```bash
onevm list
```
The new VM should appear — proof the whole chain (public site → ngrok
tunnel → OpenNebula on master → worker1) works end to end.

## Ideas for extra creativity marks

- Show live VM state with auto-refresh (poll `/dashboard` every few
  seconds via JS, or add a `/api/vms` JSON endpoint).
- Add a simple cluster topology diagram (master/worker1, VM placement).
- Show CPU/memory usage per VM using the monitoring fields already
  returned by `vmpool.info` (`vm.MONITORING`).
- Let users delete/stop their own VMs (`client.vm.action("terminate", id)`).
- Add basic role distinction (e.g. only `oneadmin` sees all VMs, others
  only their own — already partially true since `dashboard()` queries
  the logged-in user's own VMs).
