#!/usr/bin/env python3
"""studio/_tools/bambu.py - find, check and feed a Bambu X1C over the LAN.

    python3 studio/_tools/bambu.py discover              who is on the network
    python3 studio/_tools/bambu.py check                 can we reach and log in
    python3 studio/_tools/bambu.py status                what the printer is doing
    python3 studio/_tools/bambu.py send plate.3mf        upload a SLICED file
    python3 studio/_tools/bambu.py send plate.3mf --print   upload and start it

CREDENTIALS COME FROM THE ENVIRONMENT OR ~/.config/bambu.json, NEVER FROM A FLAG.
An access code on a command line ends up in shell history and in this repo's logs.

    ~/.config/bambu.json   {"ip": "192.168.1.x", "code": "12345678", "serial": "01P00A..."}
    or  BAMBU_IP / BAMBU_CODE / BAMBU_SERIAL

HOW THE PRINTER IS SPOKEN TO, AND WHY IT IS TWO PROTOCOLS. In LAN Mode an X1C exposes:

    FTPS  :990   implicit TLS, user `bblp`, password = the access code. This is where
                 files live, under /cache/ for print jobs.
    MQTTS :8883  user `bblp`, same password. Commands and telemetry.
                 Publish to  device/<serial>/request, listen on device/<serial>/report.

Uploading does NOT start a print. The file goes over FTPS, then an MQTT `project_file`
command tells the printer to run it. They are separate on purpose, and `send` keeps them
separate unless you pass --print.

THE FILE MUST ALREADY BE SLICED. A .3mf straight out of to_print.py is geometry - the
printer cannot slice. Open it in Bambu Studio, slice for your filament and plate, then
"Export plate sliced file", and send THAT. A geometry-only 3mf uploads happily and then
fails at the printer, which is the worst kind of failure: it looks like it worked.

TLS: Bambu ships a self-signed certificate, so verification is off here. That is safe
enough on your own LAN and is exactly why LAN Mode is worth using instead of the cloud -
but it does mean anything on the network could impersonate the printer.
"""
import argparse, json, os, socket, ssl, struct, sys, time

CFG = os.path.expanduser("~/.config/bambu.json")


def creds():
    c = {}
    if os.path.isfile(CFG):
        try:
            c = json.load(open(CFG, encoding="utf-8"))
        except Exception as e:
            print("  %s is not valid json: %s" % (CFG, e))
    for k, env in (("ip", "BAMBU_IP"), ("code", "BAMBU_CODE"), ("serial", "BAMBU_SERIAL")):
        if os.environ.get(env):
            c[k] = os.environ[env]
    return c


def need(c, *keys):
    missing = [k for k in keys if not c.get(k)]
    if missing:
        print("  missing %s. Put them in %s:" % (", ".join(missing), CFG))
        print('    {"ip": "192.168.1.x", "code": "12345678", "serial": "01P00A..."}')
        print("  On the printer: Settings -> Network -> turn ON LAN Only Mode.")
        print("  The IP and Access Code are both on that same screen.")
        return False
    return True


def discover(timeout=40):
    """Bambu printers announce over SSDP to 239.255.255.250:2021 every ~30s."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("", 2021))
    except OSError as e:
        print("  cannot listen on udp/2021: %s" % e)
        return {}
    s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                 struct.pack("4sl", socket.inet_aton("239.255.255.250"),
                             socket.INADDR_ANY))
    s.settimeout(timeout)
    found, t0 = {}, time.time()
    while time.time() - t0 < timeout:
        try:
            data, addr = s.recvfrom(4096)
        except socket.timeout:
            break
        txt = data.decode("utf-8", "replace")
        info = {"ip": addr[0]}
        for line in txt.splitlines():
            for key in ("USN", "DevModel", "DevName", "DevSignal"):
                if line.upper().startswith(key.upper() + ":"):
                    info[key.lower()] = line.split(":", 1)[1].strip()
        found[addr[0]] = info
    s.close()
    return found


def ports(ip):
    out = {}
    for name, p in (("ftps", 990), ("mqtts", 8883), ("camera", 6000)):
        s = socket.socket()
        s.settimeout(2.0)
        try:
            s.connect((ip, p))
            out[name] = True
        except Exception:
            out[name] = False
        finally:
            s.close()
    return out


def _ftps(c):
    """Implicit-TLS FTP. ftplib speaks explicit TLS by default, so the socket has to be
    wrapped before the greeting rather than after an AUTH command."""
    from ftplib import FTP_TLS

    class ImplicitFTP(FTP_TLS):
        def __init__(self, *a, **kw):
            self._sock = None
            super().__init__(*a, **kw)

        @property
        def sock(self):
            return self._sock

        @sock.setter
        def sock(self, value):
            if value is not None and not isinstance(value, ssl.SSLSocket):
                value = self.context.wrap_socket(value)
            self._sock = value

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE       # Bambu ships a self-signed cert
    f = ImplicitFTP(context=ctx)
    f.connect(host=c["ip"], port=990, timeout=25)
    f.login(user="bblp", passwd=c["code"])
    f.prot_p()
    return f


def cmd_check(c):
    if not need(c, "ip", "code"):
        return 1
    p = ports(c["ip"])
    print("  %s  ftps:%s  mqtts:%s  camera:%s"
          % (c["ip"], p["ftps"], p["mqtts"], p["camera"]))
    if not p["ftps"]:
        print("  nothing listening on 990. The printer is off, on another subnet, or "
              "LAN Only Mode is not enabled.")
        return 1
    try:
        f = _ftps(c)
        names = f.nlst("/cache")
        f.quit()
        print("  logged in. /cache holds %d file(s)" % len(names))
        for n in names[:8]:
            print("    %s" % n)
        return 0
    except Exception as e:
        print("  FTPS login failed: %s" % str(e)[:200])
        print("  The access code changes when you toggle LAN Only Mode - re-read it.")
        return 1


def cmd_send(c, path, start=False, timeout=180):
    # The FILE is checked before the credentials. Handing this an STL is a mistake about
    # what the printer can do, and it is worth saying so even when no printer is
    # configured yet - otherwise the only message is "missing ip, code", which sends you
    # looking for the wrong problem.
    if not os.path.isfile(path):
        print("  no such file: %s" % path)
        return 1
    if path.lower().endswith((".stl", ".obj", ".ply", ".glb")):
        print("  %s is geometry, not a sliced job. The printer cannot slice."
              % os.path.basename(path))
        print("  Slice it in Bambu Studio and export the PLATE SLICED FILE first.")
        return 1
    if not need(c, "ip", "code"):
        return 1
    name = os.path.basename(path)
    try:
        f = _ftps(c)
        with open(path, "rb") as fh:
            f.storbinary("STOR /cache/%s" % name, fh)
        f.quit()
    except Exception as e:
        print("  upload failed: %s" % str(e)[:200])
        return 1
    print("  uploaded %s (%.1f MB) to /cache/" % (name, os.path.getsize(path) / 1e6))
    if not start:
        print("  Not started. Pick it on the printer's screen, or re-run with --print.")
        return 0
    if not need(c, "serial"):
        return 1
    return _start(c, name, timeout)


def _start(c, name, timeout):
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        print("  paho-mqtt is not installed:  pip install --user paho-mqtt")
        return 1
    payload = {"print": {"sequence_id": "0", "command": "project_file",
                         "param": "Metadata/plate_1.gcode",
                         "url": "file:///sdcard/cache/%s" % name,
                         "subtask_name": name, "use_ams": False,
                         "timelapse": False, "bed_leveling": True,
                         "flow_cali": False, "vibration_cali": True,
                         "layer_inspect": True}}
    done = {"ok": False, "err": None}

    def on_connect(cl, u, flags, rc, props=None):
        if rc != 0:
            done["err"] = "mqtt refused connection (rc=%s) - check the access code" % rc
            return
        cl.publish("device/%s/request" % c["serial"], json.dumps(payload))
        done["ok"] = True

    cl = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    cl.username_pw_set("bblp", c["code"])
    cl.tls_set(cert_reqs=ssl.CERT_NONE)
    cl.tls_insecure_set(True)
    cl.on_connect = on_connect
    try:
        cl.connect(c["ip"], 8883, 30)
        cl.loop_start()
        t = time.time()
        while not done["ok"] and not done["err"] and time.time() - t < 30:
            time.sleep(0.4)
        cl.loop_stop()
        cl.disconnect()
    except Exception as e:
        print("  mqtt failed: %s" % str(e)[:200])
        return 1
    if done["err"]:
        print("  %s" % done["err"])
        return 1
    print("  print command sent. WATCH THE FIRST LAYER - nothing here checks the plate is "
          "clear or the filament is right.")
    return 0


def cmd_status(c):
    if not need(c, "ip", "code", "serial"):
        return 1
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        print("  paho-mqtt is not installed:  pip install --user paho-mqtt")
        return 1
    got = {}

    def on_connect(cl, u, f, rc, props=None):
        cl.subscribe("device/%s/report" % c["serial"])
        cl.publish("device/%s/request" % c["serial"],
                   json.dumps({"pushing": {"sequence_id": "0", "command": "pushall"}}))

    def on_message(cl, u, m):
        try:
            got.update(json.loads(m.payload.decode()).get("print", {}))
        except Exception:
            pass

    cl = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    cl.username_pw_set("bblp", c["code"])
    cl.tls_set(cert_reqs=ssl.CERT_NONE)
    cl.tls_insecure_set(True)
    cl.on_connect, cl.on_message = on_connect, on_message
    try:
        cl.connect(c["ip"], 8883, 30)
        cl.loop_start()
        t = time.time()
        while "gcode_state" not in got and time.time() - t < 20:
            time.sleep(0.4)
        cl.loop_stop()
        cl.disconnect()
    except Exception as e:
        print("  mqtt failed: %s" % str(e)[:200])
        return 1
    if not got:
        print("  connected but the printer said nothing - check the serial number.")
        return 1
    print("  state    : %s" % got.get("gcode_state"))
    print("  job      : %s" % got.get("subtask_name"))
    print("  progress : %s%%   layer %s/%s   %s min left"
          % (got.get("mc_percent"), got.get("layer_num"), got.get("total_layer_num"),
             got.get("mc_remaining_time")))
    print("  nozzle   : %s C -> %s      bed: %s C -> %s"
          % (got.get("nozzle_temper"), got.get("nozzle_target_temper"),
             got.get("bed_temper"), got.get("bed_target_temper")))
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("discover"); d.add_argument("--timeout", type=int, default=40)
    sub.add_parser("check")
    sub.add_parser("status")
    s = sub.add_parser("send"); s.add_argument("file")
    s.add_argument("--print", dest="start", action="store_true")
    a = ap.parse_args()
    c = creds()

    if a.cmd == "discover":
        found = discover(a.timeout)
        if not found:
            print("  no Bambu printer announced itself in %ds." % a.timeout)
            print("  It is off, on another network, or LAN Only Mode is not on.")
            return 1
        for ip, info in found.items():
            print("  %-15s %s %s" % (ip, info.get("devmodel", ""), info.get("devname", "")))
            print("     %s" % json.dumps(ports(ip)))
        return 0
    return {"check": cmd_check, "status": cmd_status}[a.cmd](c) if a.cmd != "send" \
        else cmd_send(c, a.file, a.start)


if __name__ == "__main__":
    raise SystemExit(main())
