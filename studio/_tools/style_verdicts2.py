#!/usr/bin/env python3
"""Measured verdicts for the second wave of 66 style cards.

Same method as wave one: every card rendered on BOTH engines against a no-style control at
the same seed with the same subject, then looked at. Nothing here is inferred.

WHAT THIS WAVE ESTABLISHED. Wave one found that a style naming an object gets the object
drawn. Wave two shows the failure has a specific and very consistent shape: THE OBJECT ENDS
UP IN THE SUBJECT'S HANDS. graffiti gave her a spray can. airbrush_70s gave her an
airbrush. pulp_cover gave her a paperback. persian_miniature gave her a golden tray.
cassette_futurism surrounded her with CRT monitors. tattoo_flash drew tattoos on her face.

That is a usable authoring rule: if the style's name is a thing a person could hold, the
model will hand it to them.

Predictions written into the cards before rendering, and how they scored:
  right  - graffiti, tattoo_flash, cassette_futurism and space_opera all injected props
           exactly as their notes predicted
  right  - surrealism and constructivist came back thin, as flagged
  WRONG  - cubism was marked weak on the grounds that neither model will abstract a face.
           The face did stay intact, but the BACKGROUND fractured into genuine cubist
           planes, which is a real result and better than predicted.
  WRONG  - iyashikei was marked weak on the grounds that "peaceful" is a quality and
           qualities do not render. It landed: soft muted calm, quiet composition. The
           palette clause carried it further than expected.
  WRONG  - voxel was guessed onto qwen, where it produced a small pixelated patch on one
           cheek. On the illustration engine it is a full voxel construction.
"""
import json, os

import argparse
argparse.ArgumentParser(description='style verdicts2').parse_args()
# ^ the CLI contract: --help exits HERE, before any work below runs.
HERE = os.path.dirname(os.path.abspath(__file__))
STYLES = os.path.join(os.path.dirname(HERE), "styles")
if not os.path.isdir(STYLES):
    STYLES = "studio/styles"

# id: (engine, compose, status, what was actually seen)
V = {
 # ---- genre worlds -------------------------------------------------------------------
 "steampunk": ("anime", "safe", "ready", "Brass and oxidised copper, gaslight, riveted plate - and the goggles landed on her belt as costume rather than as a floating prop, which is the distinction that separates a wearable noun from an injected one."),
 "dieselpunk": ("anime", "safe", "ready", "Olive drab, smoke haze, heavy muted industry. Real but restrained; it reads as a grade more than a world."),
 "solarpunk": ("anime", "replaces", "ready", "Greenery, planters and bright clean daylight took over the street. Strong, but it rebuilds the setting - do not stack on a place card."),
 "atompunk": ("anime", "inert", "weak", "Came back as generic neon city, indistinguishable from cyberpunk_neon; nothing at all on qwen. The turquoise landed, the 1950s did not. Raygun-gothic needs its object vocabulary, which is exactly what this library cannot safely use."),
 "cassette_futurism": ("anime", "injects", "weak", "Drew CRT monitors as props standing around her. The card's own note predicted this: 'CRT monitor is an object and may be drawn as a prop rather than as an environment treatment.' Confirmed."),
 "y2k_chrome": ("anime", "safe", "ready", "Iridescent holographic coat and blue-white flare. The chrome landed on the GARMENT, which keeps it composable."),
 "dark_academia": ("anime", "safe", "ready", "Warm oak and lamplight, brown-green palette. It did add a lantern, but as scenery rather than in her hands."),
 "cottagecore": ("anime", "replaces", "ready", "Soft warm daylight and flowers - which replaced the street. Same behaviour as ghibli_pastoral."),
 "grimdark": ("anime", "safe", "ready", "Mud, rust and near-black desaturation under flat light. Clearly separate from dark_fantasy_anime on material rather than value."),
 "wasteland": ("anime", "replaces", "ready", "Ruined overgrown structures and dust haze. Convincing, but it rebuilds the location."),
 "eldritch": ("anime", "safe", "ready", "Red tendril forms and light falling wrong, with no creature drawn - the card deliberately named none and that worked. One of the better surprises in the wave."),
 "wuxia": ("anime", "replaces", "ready", "Flowing silk, jade, Chinese architecture. Strong, and it replaces the setting."),
 "arcane_magitech": ("anime", "injects", "ready", "Teal rune-glow and crystal - the idiom lands, but it also spawned floating crystals as props. Usable if you want them; disruptive if you do not."),
 "space_opera": ("anime", "injects", "weak", "Starfield behind her plus an orb pendant added to her chest. The card predicted the starship risk; what arrived was jewellery instead. Weak either way."),
 "western_frontier": ("qwen", "replaces", "ready", "Frontier timber buildings, ochre dust, low hard sun. Strong, and it rebuilds the location."),
 "neo_noir": ("qwen", "safe", "ready", "Wet asphalt, saturated signage, deep blacks. Holds its own against cyberpunk_neon by staying non-futuristic."),
 "giallo": ("anime", "safe", "ready", "Saturated red and cold blue gels with hard black shadow - but ONLY on the illustration engine. On qwen it produced an ordinary photograph with no gels at all, so this was re-routed."),

 # ---- art movements ------------------------------------------------------------------
 "art_deco": ("anime", "safe", "ready", "Stepped geometry, sunburst halo, chevron. Notably it did NOT build an enclosing frame the way art_nouveau did, so it composes."),
 "bauhaus": ("anime", "replaces", "ready", "Abstracted the city into primary-coloured blocks. Genuinely Bauhaus and better than expected - the note predicted both models would refuse to abstract. They refused for the face and complied for everything else."),
 "constructivist": ("anime", "inert", "weak", "Muted, with a diagonal scarf and nothing else. No red-black agitprop palette, no heroic angle. Nothing on qwen either."),
 "surrealism": ("anime", "safe", "weak", "Atmospheric dark frame with a red ribbon motif - moody, but no impossible juxtaposition. As predicted: surrealism is a semantic property and semantics sit at the bottom of this project's effect tiers."),
 "cubism": ("anime", "safe", "ready", "The BACKGROUND fractured into genuine faceted planes while the face stayed intact. Marked weak before rendering; that was too pessimistic and is corrected here."),
 "expressionism": ("anime", "safe", "ready", "Harsh angular line, crushed value, skewed space. Distinct from gothic_illustration."),
 "pop_art": ("anime", "safe", "ready", "Flat primaries and hard graphic shapes. Works where comic_halftone failed, because it leans on flat colour rather than on a dot screen neither engine can produce."),
 "psychedelic_60s": ("anime", "safe", "ready", "Writhing organic colour in vibrating complementaries. Strong."),
 "pre_raphaelite": ("anime", "safe", "ready", "Jewel-toned local colour, flowing hair, even shadowless light. Among the most attractive results in the wave."),
 "pointillism": ("anime", "safe", "weak", "Discrete dots are present but read as falling snow rather than as optical mixing. Partial."),
 "brutalist": ("qwen", "replaces", "ready", "Massive raw concrete under flat grey light. As the card predicted, it is an architecture card and it rebuilds the location."),

 # ---- illustration traditions --------------------------------------------------------
 "ligne_claire": ("anime", "safe", "ready", "Uniform-weight outline, flat unmodulated colour, no cast shadow. Exactly the Moebius/Herge idiom and one of the cleanest cards in the library."),
 "american_comic": ("anime", "injects", "ready", "Heavy varied ink and saturated primaries - but it rewrote her pose into a dynamic action stance, as the card's note predicted. Same failure class as sakuga_impact."),
 "golden_age_illustration": ("anime", "safe", "ready", "Warm naturalistic painting with confident brushwork."),
 "woodcut": ("anime", "safe", "ready", "Cream ground, gouged parallel line, tone only through hatch density. Clean."),
 "linocut": ("anime", "safe", "ready", "Bolder and flatter than woodcut with spot colour. The two did NOT collapse together - keep both."),
 "scratchboard": ("anime", "safe", "weak", "Dark ground with some white line, but it never fully inverted. Partial."),
 "illuminated_manuscript": ("anime", "replaces", "ready", "Gold leaf and vermilion - drawn as an ornamental ring enclosing the figure. The card predicted the art_nouveau frame behaviour and got it."),
 "propaganda_poster": ("anime", "safe", "weak", "Red and black with a hard diagonal, but mostly ordinary anime underneath. The text negative did at least prevent the garbled lettering that killed screenprint_poster."),
 "pulp_cover": ("anime", "injects", "weak", "Gave her a paperback book to hold. The card deliberately named no genre furniture in order to test whether that was what broke retro_scifi_paperback - it was not. The noun in the NAME is enough."),
 "airbrush_70s": ("anime", "injects", "weak", "Put an actual airbrush tool in her hand. Textbook object-in-hands failure."),
 "tattoo_flash": ("anime", "injects", "unavailable", "Drew tattoo motifs ON her - symbols across the coat on the illustration engine, full face tattoos on qwen. The card predicted exactly this."),
 "graffiti": ("anime", "injects", "unavailable", "Put a spray can in her hand. The card rated this the highest noun risk in the batch and it was right."),

 # ---- anime studio idioms -------------------------------------------------------------
 "ufotable_glow": ("anime", "safe", "ready", "Layered bloom and particle light over a painted background. Separates from modern_anime on compositing, as intended."),
 "kyoani_soft": ("anime", "safe", "ready", "Delicate line with genuine drawn bokeh and warm ambient light. Holds apart from slice_of_life_anime."),
 "trigger_kinetic": ("anime", "replaces", "ready", "Thick tapering line, extreme perspective, red motion ribbons - and it broke up the background. Same behaviour as shonen_action."),
 "monogatari_geometric": ("anime", "replaces", "ready", "Replaced the background with flat geometric colour fields. That is the card working as designed, not failing."),
 "iyashikei": ("anime", "safe", "ready", "Quiet wide composition, soft muted greens, nothing tense. Marked weak before rendering on the grounds that 'peaceful' is a quality - the palette clause carried it further than expected. Prediction corrected."),
 "retro_shoujo_70s": ("anime", "safe", "ready", "Enormous starred eyes, fine feathered line, sepia-rose, elongated figure. Strong, and unlike shojo_soft it did NOT replace the setting."),
 "josei_muted": ("anime", "safe", "ready", "Restrained proportion, muted palette, understated. Close to seinen_grounded but darker and cooler; both survive."),

 # ---- 3D / CG --------------------------------------------------------------------------
 "pixar_3d": ("qwen", "safe", "ready", "Subsurface skin, soft global illumination, appealing stylised proportion. Clean modern-CG read."),
 "unreal_render": ("qwen", "inert", "weak", "An ordinary photograph on qwen and ordinary clean anime on the illustration engine. The 'unreal engine' token acted as a generic quality booster rather than a style, which is precisely the risk the card flagged."),
 "voxel": ("anime", "safe", "ready", "A full cube-built construction on the illustration engine. Guessed onto qwen, where it produced only a small pixelated patch on one cheek - re-routed on the evidence."),
 "ps1_lowpoly": ("anime", "safe", "weak", "Faceted the hair into polygons and left everything else smooth. The affine texture warping never appeared. low_poly_3d does this better."),

 # ---- photographic ---------------------------------------------------------------------
 "infrared_photo": ("qwen", "safe", "ready", "Waxy luminous skin, near-black sky, bleached foliage. Distinctive."),
 "cross_processed": ("qwen", "safe", "ready", "Clear cyan-green shift with crushed contrast. NOTE: this is a channel curve and would be more precise as a deterministic ffmpeg grade in looks/ than as a prompt."),
 "cyanotype": ("qwen", "safe", "ready", "Prussian-blue monochrome with a visible paper edge. Strong, and it validates the mechanism blueprint uses."),
 "daguerreotype": ("qwen", "safe", "weak", "Barely separable from the control - no mirror-silver surface, no edge solarisation. tintype already covers this ground and does it properly."),
 "kodachrome": ("qwen", "safe", "ready", "Warm midtones and deep controlled reds. Distinct enough from film_35mm to keep."),
 "cinestill_night": ("qwen", "safe", "ready", "Genuine red halation blooming around every light source. One of the strongest photographic cards in the library - pair it with a night place."),
 "street_bw": ("qwen", "safe", "ready", "Available-light monochrome with deep blacks and grain."),
 "tilt_shift": ("qwen", "inert", "weak", "Produced blur bands top and bottom but also broke the framing, squeezing the subject into a letterboxed strip. The viewpoint never moved - the same failure as drone_aerial, because viewpoint is a shot property."),
 "double_exposure": ("qwen", "safe", "weak", "A faint ghosted overlap rather than a silhouette filled with a second scene. Partial."),
 "thermal_imaging": ("qwen", "injects", "unavailable", "Recoloured her coat and scarf into a rainbow gradient and left the street a normal photograph. It painted the ramp onto an object instead of remapping the image."),

 # ---- cultural traditions ---------------------------------------------------------------
 "gongbi": ("anime", "safe", "weak", "Dark and atmospheric rather than meticulous - none of the fine even outline or flat silk ground that defines gongbi. ink_wash remains the working card in this family."),
 "persian_miniature": ("anime", "injects", "weak", "Put a golden tray in her hands. The flat jewel-toned space and gold did partly arrive, but the object-in-hands failure dominates."),
 "byzantine_icon": ("anime", "replaces", "ready", "Flat gold ground, halo, hieratic frontality. The gold ground deletes the setting by design, so compose=replaces is correct behaviour here rather than a fault."),
 "mexican_muralism": ("anime", "safe", "weak", "Some flat mural-like panelling in the background, but the monumental figure scale never arrived."),
 "ukiyo_e_shin_hanga": ("anime", "safe", "weak", "Warm atmospheric light over what is otherwise ordinary anime - the woodblock surface never appeared. ukiyo_e already covers this and does it properly."),
}


def main():
    changed = rerouted = 0
    counts, comps = {}, {}
    for sid, (eng, comp, st, seen) in sorted(V.items()):
        p = os.path.join(STYLES, sid + ".json")
        if not os.path.exists(p):
            print("  ! missing card %s" % sid)
            continue
        d = json.load(open(p, encoding="utf-8"))
        if d.get("engine") != eng:
            rerouted += 1
            print("  reroute %-24s %-6s -> %-6s" % (sid, d.get("engine"), eng))
        d["engine"] = eng
        d["compose"] = comp
        d["status"] = st
        d["verdict"] = seen
        d["verified_by"] = ("Looked at, against the no-style control at the same seed with "
                            "the same subject, on both engines. "
                            "studio/_tools/style_examples.py --all-engines")
        counts[st] = counts.get(st, 0) + 1
        comps[comp] = comps.get(comp, 0) + 1
        json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        open(p, "a").write("\n")
        changed += 1
    print("\n  %d wave-2 cards written, %d re-routed" % (changed, rerouted))
    print("  status :", counts)
    print("  compose:", comps)


if __name__ == "__main__":
    main()
