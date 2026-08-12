#!/usr/bin/env python3
"""What are the possibilities for one character? Render the axes side by side.

A character is a stack, the same way a shot is:
    identity   tags + trained LoRA      who she is
    costume    a named outfit           what she is wearing
    wear       damage 0-4 on that       what state it is in
    style      130 cards                how it is drawn
    engine     illustration / photo     which model draws it

This renders two of those axes for one character so the range is visible in one picture.
IPAdapter is held at 0.0 throughout and identity is carried by the trained LoRA alone,
because a reference sheet was MEASURED to suppress style - four styles came back as one
render repeated. Dropping the sheet is what lets the style layer through.
"""
import json, os, subprocess, sys
ROOT = os.path.expanduser("~/shared/comfy-studio")
sys.path.insert(0, os.path.join(ROOT, "scripts")); sys.path.insert(0, os.path.join(ROOT, "studio"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run, set_path
from epic import load_wf, ensure_local, HOST
import compose

SEED = 5150
NEG = "1boy, male focus, masculine, multiple girls, lowres, worst quality, bad anatomy, watermark, text"
PLACE = "ornate stone hall, tall windows, banners"

def sh(*a): return subprocess.run(a, capture_output=True, text=True)

def libs():
    L = {}
    for g in ("styles","places","looks","characters","loras","emotions","cues","weather",
              "lighting","wear","cameras","transitions","shots","motions"):
        d = os.path.join(ROOT,"studio",g); L[g] = {}
        if os.path.isdir(d):
            for fn in os.listdir(d):
                if fn.endswith(".json"):
                    try: L[g][fn[:-5]] = json.load(open(os.path.join(d,fn),encoding="utf-8"))
                    except Exception: pass
    return L

def cell(tag, prompt, lora, st):
    wf = load_wf("22_anime_kf_ipadapter.json")
    set_path(wf,"1.inputs.ckpt_name","animagine-xl-4.0.safetensors")
    set_path(wf,"4.inputs.weight",0.0)
    set_path(wf,"5.inputs.text",prompt); set_path(wf,"6.inputs.text",NEG)
    set_path(wf,"8.inputs.seed",SEED)
    for n in ("7","10"):
        set_path(wf,f"{n}.inputs.width",1024); set_path(wf,f"{n}.inputs.height",1024)
    if lora and st>0:
        wf["90"]={"class_type":"LoraLoaderModelOnly",
                  "inputs":{"model":["1",0],"lora_name":lora,"strength_model":float(st)}}
        for nid,node in list(wf.items()):
            if nid in ("1","90") or not isinstance(node,dict): continue
            for k,v in (node.get("inputs") or {}).items():
                if isinstance(v,list) and len(v)==2 and v[0]=="1" and v[1]==0:
                    node["inputs"][k]=["90",0]
    set_path(wf,"11.inputs.filename_prefix",f"claude-generated/terra_poss/{tag}")
    _,outs = run(HOST,wf,quiet=True)
    if not outs: return None
    loc = ensure_local(outs[0], f"/tmp/_tp_{tag}.png", required=False)
    if not loc: return None
    out=f"/tmp/tp_{tag}.webp"
    sh("ffmpeg","-y","-v","error","-i",loc,"-vf","scale=500:-1","-quality","84",out)
    return out

def main():
    L = libs()
    c = L["characters"]["TERRA"]; lora = c.get("lora")
    cells = []
    # AXIS 1 - style, costume held at default
    for sid in ("cel_anime_90s","watercolour","ukiyo_e","oil_painting","gothic_illustration"):
        r = compose.resolve(L, {"character":"TERRA","style":sid,"wear":0,"place":PLACE})
        p = cell(f"style_{sid}", r["prompt"], lora, 0.5)
        if p: cells.append((f"style · {sid}", p))
        print("  style %s"%sid, flush=True)
    # AXIS 2 - costume, style held at cel_anime_90s
    for cid,label in (("default","traveller"),("armour","imperial plate"),
                      ("court","court dress"),("field","field coat")):
        r = compose.resolve(L, {"character":"TERRA","style":"cel_anime_90s","costume":cid,
                                "wear":0,"place":PLACE})
        p = cell(f"cost_{cid}", r["prompt"], lora, 0.5)
        if p: cells.append((f"costume · {label}", p))
        print("  costume %s"%cid, flush=True)

    os.system("rm -rf /tmp/_tpg && mkdir -p /tmp/_tpg")
    for i,(lab,p) in enumerate(cells):
        sh("ffmpeg","-y","-v","error","-i",p,"-vf",
           "scale=480:-1,drawtext=text='%s':fontcolor=yellow:fontsize=19:x=6:y=6:"
           "box=1:boxcolor=black@0.85:boxborderw=5"%lab.replace(":", r"\:"),
           "/tmp/_tpg/%02d.png"%i)
    dst=os.path.join(ROOT,"studio","samples","cast","terra_possibilities.jpg")
    rows=(len(cells)+4)//5
    sh("ffmpeg","-y","-v","error","-pattern_type","glob","-i","/tmp/_tpg/*.png",
       "-filter_complex","tile=5x%d:margin=6:padding=6:color=0x111111"%rows,
       "-frames:v","1","-q:v","3",dst)
    print("\n%s (%d cells)"%(dst,len(cells)))

if __name__=="__main__": main()
