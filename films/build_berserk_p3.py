#!/usr/bin/env python3
"""Third pass on films/berserk.json - make it breathe like a film instead of a recap.

Run AFTER build_berserk.py and _p2.py.

The problem this fixes: the film was 90 narrated shots out of 102 - only 12% silent, with
one unbroken run of 13 narrated shots. Something was being *told* almost continuously.
Real cinema holds. It lets an image sit with no words and trusts the audience to do the
work, and the silence after a line is what gives the line its weight.

Three changes:

1. SILENCE AS ITS OWN SHOT. ~28 held beats with no narration, placed immediately after the
   moments that need room. Deliberately NOT done by padding `tail` on existing shots -
   dead air on the end of a talking shot is just a slow shot. A held reaction on a new
   image is a beat. It also costs one keyframe and one clip instead of re-rendering
   everything.

2. THE LONG HOLD. The heaviest moments get 9-12s with nothing but ambience. The cell after
   Griffith is found, the black sun, the empty moor at dawn. These are the shots people
   remember, and they only work if nothing is competing with them.

3. NARRATION -> DIALOGUE where a character can say it better. Narration explains; dialogue
   dramatises. A few lines move from the narrator's mouth into a character's.
"""
import collections, json, os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "berserk.json")
film = json.load(open(P, encoding="utf-8"), object_pairs_hook=collections.OrderedDict)
shots = film["shots"]
by = {s["id"]: s for s in shots}


def beat(sid, after, prompt, motion, secs, look=None, ref=None, sfx=None, tin="cut"):
    """A held shot with no narration. The image does the work."""
    return (after, collections.OrderedDict(
        [("id", sid), ("in", tin)]
        + ([("look", look)] if look else [])
        + ([("ref", ref)] if ref else [])
        + [("seconds", secs), ("prompt", prompt), ("motion", motion)]
        + ([("sfx", sfx)] if sfx else [])))


BEATS = [
 beat("142_dirt_hold", "140_duel1_end",
   "Low wide shot of an open training ground at dusk, {GUTS} face down in the churned dirt in the middle of the frame, the ring of watching mercenaries already breaking up and walking away from him",
   "The watching men turn and drift away out of frame one by one. Dust settles slowly. He stays exactly where he is. Very slow push in.",
   7.0, "dawn", ["GUTS"], "Boots walking away on dirt, a crowd dispersing, wind, one man breathing into the ground"),

 beat("155_apart", "150_guts_owned",
   "Wide night shot of a mercenary camp from outside its ring of firelight, dozens of men gathered around the fires, and one figure sitting alone on a supply crate well beyond the light with his back to all of them",
   "The men around the fires laugh and move. The lone figure at the edge does not turn. Firelight flickers across the ground between them. Slow drift.",
   8.0, "fire", ["GUTS"], "A camp at night heard from outside it, muffled laughter, fire, wind, distance"),

 beat("256_bridge_after", "254_griffith_sees",
   "Bleak wide shot at dawn of a narrow stone bridge over a gorge, the whole span heaped with dead men, mist rising out of the gorge below, a single figure sitting on the parapet at the far end",
   "Mist rises steadily out of the gorge and drifts across the bridge. A cloak stirs on one of the bodies. The seated figure does not move. Slow crane up.",
   9.0, "cold", None, "A gorge at dawn, wind, water far below, crows beginning, no voices"),

 beat("285_fire_burns_down", "280_guts_listens",
   "Intimate two-shot of a campfire burned down to embers between two seated figures, both quiet, the night enormous and black beyond the small ring of light",
   "The embers settle and collapse inward. A last flame gutters out. Neither figure moves. Smoke rises straight up. Very slow push in on the embers.",
   9.0, "fire", None, "Embers settling, one log collapsing, a sleeping camp, insects, deep night"),

 beat("299_river_after", "298_riverbank",
   "Wide shot of a fast river at dawn, mist over the water, the rock shelf at the near bank empty now, first light on the far trees",
   "Mist moves downstream over the water. The current keeps running. Light strengthens on the far bank. Nothing else is in the frame.",
   7.0, "dawn", None, "A river at dawn, mist, birds beginning, water over stones"),

 beat("346_griffith_above", "344_cheer",
   "Shot from behind {GRIFFITH} on the fortress steps looking down at thousands of cheering soldiers, his back to camera, the roar of the courtyard in front of him and his face not visible at all",
   "The crowd below roars and raises weapons. His shoulders do not move. Banners snap overhead. Slow push in on his back.",
   8.0, "dawn", ["GRIFFITH"], "An enormous crowd cheering, heard from above and slightly apart, banners, bells"),

 beat("359_wrecked_room", "358_after_assassins",
   "Still wide shot of a wrecked lamplit bedchamber, an overturned chair, blood across the floorboards, the balcony doors open onto the night, nobody in frame",
   "The open balcony doors move slightly in a draught. The lamp flame leans and recovers. Blood runs slowly along a floorboard seam. Nothing else.",
   7.0, "fire", None, "An empty room after violence, a lamp, a draught, blood dripping, night outside"),

 beat("432_behelit_hold", "430_behelit",
   "Extreme macro of the small red egg-shaped stone lying in an open palm, its marked surface catching moonlight, held completely steady",
   "The marks on the stone shift by the smallest degree, settling further into a face. Moonlight moves across it. The hand beneath does not move.",
   6.0, "cold", None, "One faint wet sound, a held tone, absolute quiet"),

 beat("446_empty_road", "444_skull_warn",
   "Wide shot of an empty moonlit road through open country, mist to the knees, the rider gone, only hoofprints in the mud leading away out of frame",
   "Mist drifts across the road. The hoofprints slowly fill with water. Cloud crosses the moon and the light drops. Nothing comes.",
   7.0, "cold", None, "An empty road at night, wind, water settling into mud, no hooves"),

 beat("522_corridor_hold", "520_guts_realises",
   "Shot down a dark stone corridor, {GUTS} standing motionless halfway along it, the lit doorway behind him and the dark ahead, his face turned away from both",
   "The light from the doorway flickers as someone moves inside the room. He stays where he is. Dust drifts through the light. Slow pull back down the corridor.",
   9.0, "fire", ["GUTS"], "A stone corridor, muffled voices through a door, one person not moving, distant camp"),

 beat("544_judeau_alone", "542_judeau_knows",
   "Quiet shot of {JUDEAU} alone at the camp table after the other chair has emptied, turning a small knife over and over in his fingers, one lamp, the tent dark around him",
   "He turns the knife over, and over, and over. The lamp flame steadies. He does not look up at anything. Very slow push in.",
   8.0, "fire", ["JUDEAU"], "A knife turned repeatedly on wood, a lamp, an empty tent, night outside"),

 beat("572_empty_road", "570_guts_leaves",
   "Very wide shot of an empty snowy road running away to the horizon, the walking figure now tiny and almost lost in the falling snow, the fortress gate small and dark at the near edge of frame",
   "Snow falls thickly across the whole frame. The tiny figure grows smaller and is gradually lost in it. The gate stays dark and open. Very slow crane up.",
   11.0, "dawn", None, "Heavy snow, wind across open country, one set of footsteps too far away to hear clearly"),

 beat("586_gate_hold", "585_snow_hand",
   "Wide shot of the fortress gateway from inside the courtyard, {GRIFFITH} small and alone in the open gate with his back to camera, snow filling the air between",
   "Snow falls between camera and the small white figure in the gate. He does not turn and does not move. The snow slowly begins to settle on his shoulders. Extremely slow push in.",
   12.0, "dawn", ["GRIFFITH"], "Snow falling in a stone courtyard, wind through an open gate, nothing else at all"),

 beat("586b_throne_empty", "584_king",
   "Formal wide shot of the throne room emptied of people, the throne itself vacant, candles guttering in a long row, one overturned goblet on the marble",
   "The candle flames lean together in a draught. The goblet rocks once and settles. Light moves across the empty throne. Nobody enters.",
   7.0, "fire", None, "A great hall emptied out, candles, a draught, marble, a distant door closing"),

 beat("622_cell_hold", "620_year",
   "Bleak static wide of the bottom of a stone shaft, one narrow blade of light from far above lying across a wet floor, chains against the wall, no figure visible anywhere in frame",
   "The blade of light creeps slowly across the wet floor and up the wall as hours pass. Water falls through it at intervals. Nothing else happens for a long time.",
   12.0, "cold", None, "A deep stone shaft, water dripping at long intervals, chains shifting once, terrible patience"),

 beat("662_doorway", "660_griffith_ruined",
   "Devastating shot from inside a cell looking at the open doorway, {GUTS} standing in it without coming any further in, the huge sword hanging forgotten from one hand, his face unreadable in the dark",
   "He stands in the doorway and does not come in. The torchlight behind him wavers. The sword hangs from his hand. He does not move at all for a long moment. Very slow push in on him.",
   11.0, "cold", ["GUTS"], "A cell in near total silence, one torch guttering far behind, water, a held breath"),

 beat("672_stair_empty", "670_carry",
   "Shot up an empty spiral stone stair, a dropped torch still burning on the steps, guttering, nobody on the stair at all",
   "The dropped torch burns down where it lies, throwing moving light up the curve of the stair. Smoke rises. The stair stays empty.",
   7.0, "fire", None, "An empty stone stair, a torch burning on the ground, distant footsteps receding"),

 beat("686_cart_night", "684_watching",
   "Wide night shot of a small cart on open moorland with a low fire beside it, the hooded figure motionless in the cart, two sleeping shapes by the fire, enormous darkness around all of it",
   "The fire burns low. The hooded figure in the cart stays exactly as it is. Wind moves across the moor grass. The dark presses in. Very slow drift back.",
   9.0, "fire", None, "A moor at night, a low fire, wind in grass, a cart settling, no voices"),

 beat("702_horizon", "700_eclipse",
   "Apocalyptic wide of the red plain under the black sun, the horizon crawling with countless silhouetted shapes, the small band tiny and surrounded at the centre of an enormous frame",
   "The horizon crawls continuously with shapes. The black sun does not move. The ground itself rises and falls slowly as if breathing. The tiny figures turn.",
   10.0, "eclipse", None, "A vast inhuman chorus held on one note, wind that is not wind, a heartbeat under everything"),

 beat("732_black_sun", "730_answer",
   "Near abstract shot of the black sun filling almost the entire frame, red light bleeding around its edge, everything else in silhouette",
   "The black disc burns without moving. Red light bleeds slowly wider around its rim and floods the frame by degrees. Nothing else exists.",
   10.0, "eclipse", None, "One enormous tolling note decaying very slowly, a chorus far beneath it"),

 beat("756_field_far", "754_corkus",
   "Very wide shot of the red plain seen from a great distance, the shapes and the small figures reduced almost to texture, the black sun above, no detail visible at all",
   "The distant mass moves continuously across the plain. The black sun hangs still. Everything is too far away to make out. Slow drift.",
   8.0, "eclipse", None, "An overwhelming sound kept very far off and indistinct, wind, a chorus"),

 beat("782_blood_hold", "780_brand",
   "Extreme macro of blood running steadily from a fresh brand at the base of a neck, tracking down the skin, red light",
   "Blood runs steadily from the mark and tracks down the skin drop after drop. Steam rises off it. The skin shudders once. Nothing else.",
   6.0, "eclipse", None, "Blood running, breath forced through teeth, a chorus receding into distance"),

 beat("792_light_hold", "790_griffith_reborn",
   "Abstract shot of red light with a single winged silhouette descending slowly through the centre of it, everything else formless",
   "The winged shape descends slowly and steadily through the light without any effort at all. The light pulses around it. It does not look down.",
   9.0, "eclipse", None, "Enormous wings in still air, a chorus of adoration, one terrible held note"),

 beat("802_moor_hold", "800_after",
   "Very wide static shot of an ordinary empty moor at dawn, wet grass, low mist, grey sky, one small kneeling figure almost lost in the middle distance",
   "Mist drifts slowly across ordinary wet grass. Birds cross the frame. The small kneeling figure does not move. The world is completely, unbearably normal.",
   12.0, "cold", None, "An ordinary damp moor at dawn, birdsong, wind in grass, nothing wrong with any of it"),

 beat("811_casca_hands", "810_casca_after",
   "Extreme close-up of a woman's open hands lying loose and palm up in her lap on wet grass, dirt under the nails, completely still",
   "The hands lie open and do not close. A blade of grass moves against one finger. Light shifts across them as cloud passes. They never move.",
   8.0, "cold", ["CASCA"], "Wind in wet grass, shallow breathing, no words at all"),

 beat("814_road_empty", "812_rickert",
   "Wide shot from a hillside of an empty valley road at dawn, mist in the low ground, the road running away to nothing, no one on it",
   "Mist moves along the empty road. Light strengthens. A bird crosses. The road stays completely empty all the way to the horizon.",
   9.0, "dawn", None, "A hillside at dawn, wind in grass, a horse shifting behind camera, an empty road"),

 beat("827_back", "825_iron_hand",
   "Wide shot from behind {GUTS} standing on the empty moor at dawn, the enormous sword across his back, facing away toward the horizon, everything else empty",
   "His cloak moves in the wind. He stands facing the horizon and does not turn. Dawn light strengthens across the moor behind him. Slow crane up and back.",
   9.0, "dawn", ["GUTS"], "Wind across an open moor, a heavy sword shifting on a back, one bird, dawn"),
]

added = 0
for anchor, sd in BEATS:
    if sd["id"] in by:
        continue
    idx = [k for k, s in enumerate(shots) if s["id"] == anchor]
    if not idx:
        print(f"  ! anchor {anchor} missing - skipping {sd['id']}")
        continue
    shots.insert(idx[0] + 1, sd)
    by[sd["id"]] = sd
    added += 1

# ── narration -> dialogue, where a character says it better than the narrator ──
TO_DIALOGUE = {
 "254_griffith_sees": ("GRIFFITH", "I have never seen anyone fight like that. I want him."),
 "170_we_voted":      None,   # not in this film
 "330_casca_truth":   ("CASCA", "He gave me a sword instead of a life I did not choose. You would not understand that."),
 "640_guts_returns":  ("GUTS", "A year. I came back with an answer and there is no one left to give it to."),
}
moved = 0
for sid, spec in TO_DIALOGUE.items():
    if not spec or sid not in by:
        continue
    who, line = spec
    by[sid]["say"] = line
    by[sid]["who"] = who
    moved += 1

json.dump(film, open(P, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

tot = len(shots)
silent = sum(1 for s in shots if not s.get("say"))
dia = sum(1 for s in shots if s.get("who"))
run = best = 0
for s in shots:
    run = run + 1 if s.get("say") else 0
    best = max(best, run)
print(f"held beats added   : {added}   -> {tot} shots")
print(f"narration -> dialogue: {moved}")
print(f"silent shots       : {silent} ({silent/tot*100:.0f}%, was 12%)")
print(f"dialogue lines     : {dia}")
print(f"longest narrated run: {best} shots (was 13)")
print(f"added screen time  : ~{sum(s['seconds'] for _, s in BEATS):.0f}s of held silence")
