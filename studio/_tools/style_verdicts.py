#!/usr/bin/env python3
"""Write the measured verdict onto every style card.

Every value here was set by LOOKING at that style's render against the no-style control,
at the same seed with the same subject. Nothing is inferred from the card's own claim -
the library shipped with 46 cards marked `ready` and not one of them had been rendered.

Three fields carry the finding:

  engine   the model that actually renders it, chosen from pixels rather than from the
           card's guess. Qwen-Image cannot be steered off photography by prompt at ANY
           cfg - measured: 20 steps at cfg 4.0, Lightning LoRA off, negative containing
           "painting, illustration", still returned a photograph - so painterly and
           graphic styles belong on the SDXL path. "anime" is a misnomer for that engine.
           It is the ILLUSTRATION engine and it does watercolour, ukiyo-e and oil paint
           beautifully.

  compose  how the style behaves stacked with the other layers - the field the wizard
           needs:
             safe     re-renders the same scene in a new idiom. Composes with place,
                      character and look.
             replaces re-renders AND overrides the setting. A real style, but it fights a
                      place card - shojo_soft put her in a flower field, art_nouveau
                      behind an ornamental arch.
             injects  the noun in the style's NAME becomes a prop in the frame instead of
                      an idiom. chalkboard drew a chalkboard, food_photography drew a
                      plate of food, wildlife_photo added a fox. This is the project's
                      governing rule - the model renders nouns, not adjectives - biting in
                      a new place. These corrupt any scene they touch.
             inert    no visible change from the control.

  status   ready / weak / unavailable, from the same look.
"""
import json, os

import argparse
argparse.ArgumentParser(description='style verdicts').parse_args()
# ^ the CLI contract: --help exits HERE, before any work below runs.
HERE = os.path.dirname(os.path.abspath(__file__))
STYLES = os.path.join(os.path.dirname(HERE), "styles")
if not os.path.isdir(STYLES):
    STYLES = "studio/styles"

# id: (engine, compose, status, what was actually seen)
V = {
 # --- illustration engine, faithful idiom, composes ---------------------------------
 "cel_anime_90s": ("anime", "safe", "ready", "Heavier uneven line, duller warm palette, hard flat shadow. Reads unmistakably as a 90s OVA cel beside the control."),
 "modern_anime": ("anime", "safe", "ready", "Clean digital line, cool flat grade. Separates from cel_anime_90s in exactly the intended direction."),
 "manga_inked": ("anime", "safe", "ready", "Black and white, clean ink, no tone. Stayed distinct from manga_screentone - the authoring agent predicted these two would collapse together and they did not."),
 "manga_screentone": ("anime", "safe", "ready", "B&W with visible dot tone and grainier texture. Genuinely separate from manga_inked."),
 "ukiyo_e": ("anime", "safe", "ready", "Woodblock line, flat inked colour, period signage. Strong."),
 "ink_wash": ("anime", "safe", "ready", "Sumi-e: bare paper, wet bleed, a red seal. Among the strongest in the library, 89.4 from control."),
 "watercolour": ("anime", "safe", "ready", "Paper bleed and pigment pooling. Strongest measured result in the set, 92.1 from control. This card was authored engine=qwen, where it produced a plain photograph and did nothing."),
 "gouache": ("anime", "safe", "ready", "Flat opaque paint, limited palette, poster-like. The authoring agent called this the weakest card in its batch and asked for it to be rendered first - right to flag it, and the answer is that it works, but only on this engine."),
 "oil_painting": ("anime", "safe", "ready", "Visible brush loading and warm impasto light."),
 "impressionist": ("anime", "safe", "ready", "Broken colour, soft bokeh light. Works here; was a plain photograph on qwen."),
 "concept_art": ("anime", "safe", "ready", "Painted, moody, loose edges. Works here; was a plain photograph on qwen."),
 "baroque_painting": ("anime", "safe", "ready", "Chiaroscuro - single warm source, deep falloff. Strong."),
 "charcoal_drawing": ("anime", "safe", "ready", "Smudged black and white with paper tooth."),
 "pencil_sketch": ("anime", "safe", "ready", "Graphite hatch, unfinished edges, white ground."),
 "gothic_illustration": ("anime", "safe", "ready", "High-contrast B&W, tall architecture, ornamental."),
 "storybook_illustration": ("anime", "safe", "ready", "Soft pastel wash and open line. Reads as a children's book plate."),
 "chibi": ("anime", "safe", "ready", "Head-to-body proportion collapses to roughly 1:2. Note it also forces a wider framing - a chibi cannot be a mid-shot."),
 "webtoon_flat": ("anime", "safe", "ready", "Bold flat colour and heavy saturation, no rendering."),
 "flat_vector": ("anime", "safe", "ready", "Hard-edged shapes and clean fills. Works here; on qwen it barely moved."),
 "silhouette_poster": ("anime", "safe", "ready", "Figure reduced to solid black against a lit ground. Strong and unambiguous."),
 "low_poly_3d": ("anime", "safe", "ready", "Faceted planes, visible polygon edges."),
 "pixel_art": ("anime", "safe", "ready", "Convincing pixel grid and clamped palette. The authoring agent concluded neither engine could produce a pixel grid and that the card needed a post-process instead - that was wrong, animagine does it directly."),
 "dark_fantasy_anime": ("anime", "safe", "ready", "Desaturated to near-black, heavy shadow, a single red accent."),
 "seinen_grounded": ("anime", "safe", "ready", "Muted palette, restrained line, adult proportion. Subtle by design at 20.6 from control, but doing the intended thing."),
 "slice_of_life_anime": ("anime", "safe", "ready", "Soft pastel daylight, gentle line."),
 "idol_bright": ("anime", "safe", "ready", "Sparkle, bloom, saturated rainbow light."),
 "vaporwave": ("anime", "safe", "ready", "Cyan and magenta, hard neon, flattened depth."),
 "ova_80s": ("anime", "safe", "ready", "80s hair mass and cel paint - clearly separate from cel_anime_90s despite both carrying the retro tail two agents warned would collide. Keep both."),

 # --- real style, but it overrides the setting --------------------------------------
 "ghibli_pastoral": ("anime", "replaces", "ready", "Painted skies and warm village architecture, but it REPLACED the city street with a village lane. Do not stack on a place card."),
 "shojo_soft": ("anime", "replaces", "ready", "Sparkle, pastel, glazed eyes - and it replaced the street with a field of flowers. Very strong at 81.4, but it overwrites any place you choose."),
 "shonen_action": ("anime", "replaces", "ready", "Hard black line and speed fragments; it shattered the background into abstract shards. Style and setting cannot both survive this one."),
 "art_nouveau": ("anime", "replaces", "ready", "Mucha ornament, gold line, flat decorative ground - it replaced the street with an ornamental arch. Beautiful, but it is a frame, not a lens."),
 "mecha_anime": ("anime", "injects", "weak", "Rendered a giant robot into the frame. That is a subject, not a style - the mech belongs in the shot description."),
 "sakuga_impact": ("anime", "injects", "weak", "Changed her POSE - arm thrown at camera, scarf streaming. Motion is a shot property; this card silently rewrites blocking."),

 # --- photographic engine ------------------------------------------------------------
 "photorealistic": ("qwen", "safe", "ready", "Skin texture and real lens falloff. Sits close to the control at 21.0 because qwen's baseline IS photographic - that is agreement, not failure."),
 "film_35mm": ("qwen", "safe", "ready", "Warmer, softer, slight halation. Subtle but present."),
 "cinematic_film_still": ("qwen", "safe", "ready", "Anamorphic-ish framing and graded contrast."),
 "documentary_photo": ("qwen", "safe", "ready", "Available light, candid stance, unposed."),
 "studio_portrait": ("qwen", "safe", "ready", "Controlled key, clean falloff, dropped background."),
 "architectural_photo": ("qwen", "safe", "ready", "Corrected verticals, building given equal weight to the figure."),
 "war_photography": ("qwen", "safe", "ready", "Desaturated, grainy, handheld feel."),
 "long_exposure_night": ("qwen", "safe", "ready", "Genuine light trails from traffic. Unambiguous."),
 "polaroid": ("qwen", "safe", "ready", "Real instant-film border and shifted colour. Among the strongest photographic results at 63.9."),
 "tintype": ("qwen", "safe", "ready", "Aged plate, vignette, silver tone."),
 "cyberpunk_neon": ("qwen", "safe", "ready", "Wet street, saturated neon signage. Low distance on the illustration engine at 17.3, but correct here."),
 "security_camera": ("qwen", "replaces", "ready", "Fisheye, timestamp burn-in, monochrome cast - convincing, but it also drew the camera itself into frame."),
 "editorial_fashion": ("qwen", "safe", "weak", "Slightly more posed and styled than the control, but the difference is small enough to be seed noise. Use studio_portrait unless you specifically need the styling."),
 "macro_photography": ("qwen", "safe", "weak", "Tightened the crop but produced no macro optics - no extreme shallow plane, no change in subject scale. The frame is a portrait, not a macro."),
 "drone_aerial": ("qwen", "injects", "weak", "Did NOT move the camera up. Still eye level, just a longer street. An aerial is a camera position - a shot property, not a style."),
 "wildlife_photo": ("qwen", "injects", "unavailable", "Rendered a FOX beside her. The noun in the name became an animal in the scene. Use a long lens plus documentary_photo instead."),
 "food_photography": ("qwen", "injects", "unavailable", "Put a plate of food on a table in front of her. Same failure as wildlife_photo."),
 "matte_painting": ("qwen", "inert", "unavailable", "Came back broken: horizontal banding and a doubled figure. This is the above-2MP composition-duplication failure the qwen checkpoint card documents, triggered by the style's own wide-vista prose."),

 # --- the noun-becomes-a-prop trap ---------------------------------------------------
 "chalkboard": ("qwen", "injects", "unavailable", "Drew a chalkboard on the wall next to her and left her photographic. Textbook noun-as-prop."),
 "technical_diagram": ("qwen", "injects", "unavailable", "Drew a floating exploded-view diagram beside an untouched photo."),
 "papercut_collage": ("qwen", "injects", "unavailable", "Drew torn-paper layers as a FRAME around an unmodified photograph."),
 "retro_scifi_paperback": ("qwen", "injects", "unavailable", "Added a starship and a gas giant behind a normal photo. Renders the genre's furniture, not its printing."),
 "screenprint_poster": ("qwen", "injects", "unavailable", "Produced garbled poster lettering over a photo. Neither engine screenprints, and both hallucinate text."),
 "comic_halftone": ("anime", "inert", "weak", "On qwen a plain photo; on the illustration engine ordinary anime with no dot screen. Use manga_screentone, which actually produces tone."),
 "stop_motion_felt": ("anime", "inert", "unavailable", "No felt fibre, no armature, no stop-motion staging on either engine. Ordinary anime."),
 "risograph": ("anime", "inert", "unavailable", "On qwen it drew a riso-coloured rectangle over the photo; on the illustration engine, nothing. Misregistration and spot ink are print artifacts neither model has."),
 "noir_comic": ("qwen", "safe", "ready", "On qwen this is a genuine high-contrast B&W ink comic - one of the better surprises. On the illustration engine it did nothing, which is why it was nearly marked unavailable."),
 "blueprint": ("qwen", "safe", "ready", "Cyanotype ground, drafting linework, plate lettering. Works on qwen; inert on the illustration engine."),
 "claymation": ("qwen", "safe", "ready", "Real modelled-clay surface and thumbprint form. Works on qwen; inert on the illustration engine."),
 "eight_bit": ("qwen", "safe", "ready", "Genuine chunky pixel quantisation. Works on qwen; inert on the illustration engine."),
}


def main():
    changed = rerouted = 0
    counts, comps = {}, {}
    for f in sorted(os.listdir(STYLES)):
        if not f.endswith(".json") or f == "_control.json":
            continue
        sid = f[:-5]
        p = os.path.join(STYLES, f)
        d = json.load(open(p, encoding="utf-8"))
        if sid not in V:
            print("  ! no verdict for %s - left untested" % sid)
            continue
        eng, comp, st, seen = V[sid]
        if d.get("engine") != eng:
            rerouted += 1
            print("  reroute %-24s %-6s -> %-6s" % (sid, d.get("engine"), eng))
        d["engine"] = eng
        d["compose"] = comp
        d["status"] = st
        d["verdict"] = seen
        d["verified_by"] = ("Looked at, against the no-style control at the same seed with "
                            "the same subject. studio/_tools/style_examples.py")
        counts[st] = counts.get(st, 0) + 1
        comps[comp] = comps.get(comp, 0) + 1
        json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        open(p, "a").write("\n")
        changed += 1
    print("\n  %d cards written, %d re-routed to a different engine" % (changed, rerouted))
    print("  status :", counts)
    print("  compose:", comps)


if __name__ == "__main__":
    main()
