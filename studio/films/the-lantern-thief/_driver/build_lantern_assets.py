#!/usr/bin/env python3
"""Build every asset for THE LANTERN THIEF through the foundry API, exactly as
a user clicking the selectors would."""
import json, sys, time, urllib.request

BASE = "http://127.0.0.1:8777"

def post(path, body):
    r = urllib.request.Request(BASE + path, json.dumps(body).encode(),
                               {"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=120) as f:
        return json.load(f)

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as f:
        return json.load(f)

def wait_job(jid, label):
    t0 = time.time()
    while True:
        j = get("/api/foundry/job/" + jid)
        j = j.get("job", j)
        st = j.get("state")
        if st != "running":
            mins = (time.time() - t0) / 60
            print(f"  [{label}] {st} in {mins:.1f}m"
                  + (f"  ERROR: {j.get('error')}" if j.get("error") else ""), flush=True)
            if st == "failed":
                for line in (j.get("log") or [])[-6:]:
                    print("    |", line, flush=True)
            return st == "done"
        time.sleep(6)

# ── film ──────────────────────────────────────────────────────────────────────
film = post("/api/film/new", {"title": "The Lantern Thief", "look": "anime"})["id"]
print("film:", film, flush=True)

# ── assets ────────────────────────────────────────────────────────────────────
A = {}
def new(key, type_, name, sel, notes=""):
    j = post("/api/foundry/new", {"type": type_, "name": name, "style": "anime",
                                  "selections": sel, "notes": notes})
    A[key] = j["id"]
    print(f"new {type_} {name} -> {j['id']}", flush=True)

new("jin", "character", "Jin",
    {"archetype": "human_female", "age": "twenties", "height": "short",
     "build": "slight", "skin": "pale", "face_shape": "heart",
     "eye_color": "green", "eye_shape": "narrow", "brows": "thin",
     "hair_style": "short_messy", "hair_color": "white", "facial_hair": "none",
     "marks": ["tattoo_neck", "earring"], "personality": "wry",
     "voice": "mabel"})
new("keeper", "character", "The Keeper",
    {"archetype": "human_male", "age": "old", "height": "average",
     "build": "lean", "skin": "tan", "face_shape": "long",
     "eye_color": "grey", "eye_shape": "hooded", "brows": "bushy",
     "hair_style": "topknot", "hair_color": "grey", "facial_hair": "beard",
     "marks": [], "personality": "gentle", "voice": "male_02"})
new("hoshi", "character", "Hoshi",
    {"archetype": "beast", "age": "child", "height": "short", "build": "slight",
     "skin": "fur", "face_shape": "muzzle", "eye_color": "amber",
     "eye_shape": "wide", "brows": "soft", "hair_style": "mane",
     "hair_color": "auburn", "facial_hair": "none", "marks": ["markings"],
     "personality": "cocky", "voice": "belinda"},
    notes="a small fox spirit the size of a cat, two tails, ember-tipped fur")
new("market", "place", "Night Market",
    {"base": "market", "condition": "festival", "time_of_day": ["night", "dawn"],
     "weather": "clear", "crowd": "busy", "palette": "warm"})
new("rooftops", "place", "Old Quarter Rooftops",
    {"base": "rooftops", "condition": "lived", "time_of_day": ["night"],
     "weather": "clear", "crowd": "empty", "palette": "cool"})
new("temple", "place", "Hilltop Temple",
    {"base": "temple", "condition": "old", "time_of_day": ["dawn"],
     "weather": "fog", "crowd": "empty", "palette": "muted"})
new("alley", "place", "Back Alley",
    {"base": "alley", "condition": "lived", "time_of_day": ["night"],
     "weather": "rain", "crowd": "empty", "palette": "cool"})
new("dark", "costume", "Thief Cloak",
    {"category": "cloak", "primary": "charcoal", "secondary": "black",
     "material": "cotton", "condition": "worn", "closure": "closed",
     "accessories": ["hood_down", "satchel", "gloves"]})
new("festival", "costume", "Festival Silks",
    {"category": "festival", "primary": "red", "secondary": "gold",
     "material": "silk", "condition": "new", "closure": "closed",
     "accessories": ["charms"]})
new("lantern", "prop", "Paper Lantern",
    {"category": "lantern", "material": "paper", "condition": "cared",
     "aura": "glow_warm"})
new("theme", "music", "Lantern Theme",
    {"mood": "wistful", "tempo": "slow", "instruments": ["strings", "guzheng", "bells"]})
new("chase", "music", "Rooftop Chase",
    {"mood": "tense", "tempo": "driving", "instruments": ["taiko", "strings", "synth"]})

json.dump({"film": film, **A}, open("/tmp/lantern_ids.json", "w"), indent=1)

# ── seed packs, sequential ────────────────────────────────────────────────────
ok = True
for key, type_ in [("jin", "character"), ("keeper", "character"), ("hoshi", "character"),
                   ("market", "place"), ("rooftops", "place"), ("temple", "place"),
                   ("alley", "place"), ("dark", "costume"), ("festival", "costume"),
                   ("lantern", "prop")]:
    j = post("/api/foundry/seeds", {"type": type_, "id": A[key]})
    print(f"seeds {key} job {j['job']}", flush=True)
    ok &= wait_job(j["job"], f"seeds {key}")

# ── costumes onto Jin ─────────────────────────────────────────────────────────
for c in ("dark", "festival"):
    j = post("/api/foundry/apply", {"character": A["jin"], "costume": A[c]})
    print(f"apply {c} job {j['job']}", flush=True)
    ok &= wait_job(j["job"], f"apply {c}")

# ── into the film ─────────────────────────────────────────────────────────────
r = post("/api/foundry/send", {
    "film": film,
    "characters": [{"id": A["jin"], "costume": A["dark"]},
                   {"id": A["keeper"], "costume": ""},
                   {"id": A["hoshi"], "costume": ""}]})
print("send characters:", r, flush=True)
print("ALL DONE" if ok else "DONE WITH FAILURES", flush=True)
