import os
import json
import time
import random
import urllib.request
import urllib.parse
from datetime import datetime

# CONFIGURATION
COMFYUI_URL = "http://127.0.0.1:8188"
WORKFLOW_FILE = "workflow_api.json"
CHECKPOINTS_DIR = os.path.expanduser("~/ComfyUI/models/checkpoints")
SHARED_OUTPUT_BASE = os.path.expanduser("~/shared")
DURATION_HOURS = 4

# ELITE RTX 5090 VISUAL PROMPTS
PROMPTS = [
    "Hyper-realistic macro photography of a mechanical biological scarab beetle, shimmering iridescent titanium shell, visible micro-gears, fiber optic veins pulsing with blue light, resting on a wet cybernetic circuit board leaf, 8k resolution, razor-sharp macro focus, subsurface scattering, octane render engine style.",
    "A massive gothic cathedral floating inside a nebulous cosmic rift. Swirling galaxies visible through broken stained glass windows, cosmic dust clouds illuminating floating marble pillars, ethereal light rays piercing the void, hyper-detailed architecture, celestial surrealism, intricate carvings, volumetric dark ambient lighting.",
    "Cinematic dark fantasy close-up portrait of an ancient elven warrior king. Weathered skin, silver intricate hair, deep emerald eyes with procedural reflections, ornate matte-black obsidian armor with glowing gold filigree runes, smoky background, intense side-key lighting, photorealistic skin pores, 35mm anamorphic lens.",
    "A hyper-detailed subterranean cyberpunk bazaar at night. Neon signs refracting through thick steam and heavy rain, flying hover-vehicles passing between colossal steel skyscrapers, crowds of diverse androids and humans with cybernetic implants, muddy puddle reflections, ultra-realistic wet surfaces, global illumination ray-tracing.",
    "A surrealist architectural masterwork of a palace carved entirely out of translucent emerald green ice, situated in the middle of a blazing desert. Sun rays refracting violently through the ice walls onto the golden sand, heat distortion waves in the air, hyper-detailed crystalline structures, architectural digest photography style.",
    "An overgrown post-apocalyptic control room. Giant supercomputers reclaimed by glowing bioluminescent moss and fluorescent hanging vines, a rusted mainframe terminal displaying cascading matrix green code, volumetric light shafts filtering through cracked concrete ceiling grids, dust motes floating in mid-air.",
    "Hyper-detailed macro view of an astronaut's visor reflecting a collapsing supernova. Perfect reflection of cosmic fire and swirling black holes on the gold-tinted glass, microscopic scratches and space dust on the helmet texture, hyper-realistic fabric weave of the spacesuit, deep space stark shadows.",
    "A massive, hyper-detailed mechanical dragon constructed from polished chrome and brass steampunk clockwork mechanisms, emerging from a dense cloud of white steam. Piercing amber LED eyes, thousands of moving interlocking gears, individual metallic scales, dramatic high-contrast studio lighting, cinematic 8k masterpiece."
]

def get_best_model():
    """Scans checkpoints folder to dynamically select the highest-performing available model."""
    if not os.path.exists(CHECKPOINTS_DIR):
        print(f"Error: Checkpoint path {CHECKPOINTS_DIR} not found.")
        return None
    
    files = [f for f in os.listdir(CHECKPOINTS_DIR) if f.endswith(('.safetensors', '.ckpt'))]
    if not files:
        return None

    # Prioritize advanced architectures perfect for an RTX 5090
    priorities = ["flux", "sd3", "sdxl", "v2", "v1"]
    for keyword in priorities:
        for f in files:
            if keyword in f.lower():
                print(f"🎯 Selected Model: {f} (Matches template rule: '{keyword}')")
                return f
    
    print(f"🎯 Selected Model: {files[0]} (Default fallback)")
    return files[0]

def queue_prompt(prompt_workflow):
    """Dispatches the configured workflow directly into the ComfyUI API loop."""
    p = {"prompt": prompt_workflow}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"{COMFYUI_URL}/prompt", data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"❌ Failed to queue prompt: {e}")
        return None

def run_automation():
    # 1. Prepare target output directory inside ~/shared
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_dir = os.path.join(SHARED_OUTPUT_BASE, f"generation_{timestamp}")
    os.makedirs(target_dir, exist_ok=True)
    print(f"📁 Target output folder created at: {target_dir}")

    # 2. Select the optimal model dynamically
    model_name = get_best_model()
    if not model_name:
        print("❌ No models found in ComfyUI checkpoints folder! Exiting script.")
        return

    # 3. Load the exported user API workflow JSON
    try:
        with open(WORKFLOW_FILE, 'r') as f:
            workflow = json.load(f)
    except FileNotFoundError:
        print(f"❌ Could not find {WORKFLOW_FILE}. Ensure it is exported from Dev Mode as API format and saved alongside this script.")
        return

    # 4. Inject configurations dynamically into standard node templates
    for node_id, node in workflow.items():
        if node.get("class_type") in ["CheckpointLoaderSimple", "LoadDiffusionModel"]:
            node["inputs"]["ckpt_name"] = model_name
        elif node.get("class_type") == "SaveImage":
            node["inputs"]["filename_prefix"] = os.path.join(target_dir, "5090_render")
        elif node.get("class_type") == "EmptyLatentImage":
            if any(k in model_name.lower() for k in ["flux", "sd3", "sdxl"]):
                node["inputs"]["width"] = 1024
                node["inputs"]["height"] = 1024

    # 5. Continuous execution loop for exactly 4 hours
    start_time = time.time()
    end_time = start_time + (DURATION_HOURS * 3600)
    count = 1

    print(f"🚀 Initializing generation cycle. Running until {datetime.fromtimestamp(end_time).strftime('%H:%M:%S')}")
    
    while time.time() < end_time:
        current_prompt_text = random.choice(PROMPTS)
        
        for node_id, node in workflow.items():
            if "seed" in node.get("inputs", {}):
                node["inputs"]["seed"] = int(time.time() * 1000) % 1125899906842624
            
            if node.get("class_type") == "CLIPTextEncode" and "text" in node.get("inputs", {}):
                current_text = str(node.get("inputs", {}).get("text", "")).lower()
                if "negative" not in str(node_id).lower() and "bad" not in current_text and "embedding:" not in current_text:
                    node["inputs"]["text"] = current_prompt_text

        print(f"⏳ Dispatching batch #{count}...")
        res = queue_prompt(workflow)
        
        if res:
            print(f"✅ Batch #{count} successfully queued. Prompt ID: {res.get('prompt_id')}")
            count += 1
        
        time.sleep(10) 

    print(f"🏁 4-Hour run completed! All contents generated safely inside: {target_dir}")

if __name__ == "__main__":
    run_automation()
