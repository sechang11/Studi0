#!/usr/bin/env python3
"""Second wave of style cards - the families the first 64 missed.

WHAT THIS WAVE IS FOR. The first pass covered anime idioms, photographic treatments and
art media (watercolour, oil, ink). It had almost no GENRE-WORLD aesthetics - the thing
cyberpunk_neon is an instance of - and almost no ART MOVEMENTS. Those are the two families
that carry the most weight in real prompt libraries, because they set palette, architecture
and light all at once.

WRITTEN AGAINST A MEASURED FAILURE MODE. The first wave taught us that a style whose NAME
CONTAINS AN OBJECT NOUN gets the object drawn into the frame instead of the idiom applied:
chalkboard drew a chalkboard, food_photography drew a plate of food, wildlife_photo added a
fox, retro_scifi_paperback added a starship. That is the project's governing rule - the
model renders nouns, not adjectives - showing up in the style layer.

So every card here is written as a RENDERING IDIOM: line, palette, surface, light, edge.
Where a tradition is inseparable from an object (stained glass is a window, tarot is a
card, mosaic is tiles) the card is still authored, because guessing is not measuring - but
its note records the prediction that it will inject rather than style, so the render either
confirms or refutes it.

ENGINE. Set as a starting guess only. style_examples.py --all-engines renders every card on
both, and style_verdicts.py rewrites this field from the pixels. The first wave had 27 of 64
re-routed that way, so treat the value here as a hypothesis.
"""
import json, os, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "studio/styles"

Q = "masterpiece, best quality, very aesthetic, absurdres"

# (id, name, family, engine_guess, means, tags, prose, negative_add, suits_looks, strength, works_for, note)
CARDS = [
 # ---------------- genre-world aesthetics: what cyberpunk_neon is an instance of -----
 ("steampunk", "Steampunk", "world", "anime",
  "Victorian industry as a whole visual world: brass and oxidised copper, riveted plate, leather and oiled canvas, warm gaslight against soot.",
  "steampunk, brass, gears, victorian, goggles, industrial, warm lighting",
  "a brass-and-copper Victorian industrial world, riveted metal plate and oiled leather, warm gaslight, soot-darkened air",
  "modern, plastic, neon, digital displays",
  ["golden", "sepia", "firelight", "warm"], "strong",
  "video - palette and material hold well; fine gear detail will crawl between frames",
  "The palette and materials carry this, not the word steampunk. 'goggles' is deliberately in the tag list because it is one of the few object nouns that reads as costume rather than as a prop dropped into the frame - it lands ON the figure. Compare food_photography, which put a plate on a table."),

 ("dieselpunk", "Dieselpunk", "world", "anime",
  "Interwar heavy industry: riveted steel, olive drab and oxide red, smoke and searchlights, weight over elegance.",
  "dieselpunk, 1940s, industrial, riveted metal, smoke, searchlight, olive drab",
  "an interwar heavy-industrial world of riveted steel and olive drab, smoke haze, hard searchlight beams",
  "clean, futuristic, pastel, neon",
  ["cold", "noir", "sodium", "overcast"], "moderate",
  "video - large forms hold; smoke is the usual i2v boiling risk",
  "Sits between steampunk and retro-futurism. If it collapses toward steampunk on render, the separator to push is the palette - olive/oxide against steampunk's brass - rather than the era word."),

 ("solarpunk", "Solarpunk", "world", "anime",
  "Optimistic ecological futurism: white structure overrun with green, glass and water, high clean daylight, plants integrated into architecture rather than decorating it.",
  "solarpunk, lush greenery, white architecture, sunlight, plants, glass, utopian",
  "a bright ecological future of white architecture overgrown with greenery, glass and water, clean high daylight",
  "dystopian, ruins, smog, dark, industrial decay",
  ["golden", "neutral", "warm"], "strong",
  "video - foliage is dense fine detail and is a known i2v boiling case",
  "The strongest signal is the LIGHT - high, clean, unclouded - not the word solarpunk. Predicted to compose safely because it changes palette and architecture without demanding a specific prop."),

 ("atompunk", "Atompunk / Raygun Gothic", "world", "anime",
  "1950s space-age optimism: chrome fins, atomic starbursts, turquoise and coral, googie curves, everything streamlined whether or not it moves.",
  "retro futurism, 1950s, chrome, atomic age, googie, turquoise, starburst",
  "a 1950s space-age world of chrome fins and atomic starburst motifs, turquoise and coral, streamlined googie curves",
  "gritty, realistic, muted, modern",
  ["faded_film", "warm", "golden"], "moderate",
  "video - flat chrome and flat colour hold well",
  "Raygun gothic is the more precise term but atompunk has more corpus mass. Watch for the noun trap: if 'raygun' or 'rocket' creeps into the prose the model will draw one."),

 ("cassette_futurism", "Cassette futurism", "world", "qwen",
  "The future as imagined in 1979: beige and grey plastic, CRT phosphor glow, chunky physical switches, monochrome text displays, visible screws.",
  "retro technology, crt monitor, beige plastic, 1980s computer, phosphor glow",
  "a lived-in analogue future of beige plastic and CRT phosphor glow, chunky switches and monochrome displays, visible wear",
  "sleek, glass, holographic, modern minimalism",
  ["cold", "sodium", "faded_film"], "moderate",
  "video - CRT scanline flicker is a per-frame texture and will crawl",
  "PREDICTED NOUN RISK: 'CRT monitor' is an object and may be drawn as a prop rather than as an environment treatment. The measured comparison is chalkboard, which did exactly that. If it injects, the fix is to strip the device nouns and keep only 'beige plastic, phosphor green glow'."),

 ("y2k_chrome", "Y2K chrome", "world", "anime",
  "Turn-of-millennium digital optimism: liquid chrome, iridescent gradients, lens flare, translucent plastic, blue-white highlights.",
  "y2k aesthetic, chrome, iridescent, holographic, lens flare, translucent, gradient",
  "a year-2000 digital aesthetic of liquid chrome and iridescent gradients, translucent plastic, blue-white lens flare",
  "matte, rustic, muted, natural",
  ["cold", "neon"], "moderate",
  "video - specular chrome shifts unpredictably between frames",
  "Reflective surfaces are the least temporally stable thing in the library. Expect this to look better as a still than as a clip."),

 ("dark_academia", "Dark academia", "world", "anime",
  "Old-university melancholy: oak and leather, dust in low window light, tweed and wool, brown-green palette, autumn perpetually.",
  "dark academia, library, old books, warm lamplight, tweed, autumn, dust motes",
  "an old-university world of oak and leather in low dusty window light, brown and forest-green palette, wool and tweed",
  "bright, modern, saturated, plastic",
  ["sepia", "golden", "memory", "firelight"], "moderate",
  "video - static and warm, one of the safer sets for i2v",
  "PREDICTED NOUN RISK: 'library' and 'old books' may be drawn as a location, overriding the place layer the way ghibli_pastoral did. If it replaces rather than styles, mark compose=replaces rather than deleting it."),

 ("cottagecore", "Cottagecore", "world", "anime",
  "Rural domestic softness: linen and dried flowers, warm diffuse daylight, hand-made texture, muted earth and cream.",
  "cottagecore, pastoral, linen, dried flowers, soft sunlight, rustic, warm",
  "a soft rural domestic world of linen and dried flowers in warm diffuse daylight, muted earth tones and cream",
  "urban, neon, industrial, high contrast",
  ["golden", "warm", "memory"], "moderate",
  "video - soft diffuse light is stable through i2v",
  "Overlaps ghibli_pastoral, which measured as compose=replaces. Watch whether this one also swaps the setting for a meadow."),

 ("grimdark", "Grimdark", "world", "anime",
  "Fantasy stripped of romance: mud, rust and dried blood, overcast flat light, heavy worn material, no clean surfaces anywhere.",
  "grimdark, dark fantasy, mud, rust, worn armor, overcast, desaturated, grim",
  "a brutal low-fantasy world of mud and rust under flat overcast light, worn heavy material, nothing clean",
  "bright, colorful, clean, heroic, polished",
  ["bleach", "cold", "overcast", "noir"], "strong",
  "video - flat overcast light is among the most stable choices",
  "Distinct from dark_fantasy_anime, which is about VALUE (near-black, single accent). This one is about MATERIAL - mud and rust. If they collapse on render, keep dark_fantasy_anime and repoint this at texture."),

 ("wasteland", "Post-apocalyptic wasteland", "world", "anime",
  "Ruin as a palette: dust ochre and bleached concrete, scoured surfaces, hard sun through particulate, vegetation reclaiming structure.",
  "post-apocalyptic, ruins, dust, overgrown, bleached, harsh sunlight, decay",
  "a ruined world of dust ochre and bleached concrete, scoured surfaces under hard particulate sunlight, vegetation reclaiming structure",
  "pristine, clean, new, vibrant",
  ["bleach", "sodium", "golden"], "strong",
  "video - dust haze holds; fine rubble detail will crawl",
  "The dust in the air is what sells this and it is also what makes it a good i2v candidate: atmospheric haze suppresses the fine detail that normally boils."),

 ("eldritch", "Cosmic horror", "world", "anime",
  "Wrongness without a monster: sickly green-violet cast, non-Euclidean geometry, too much negative space, light coming from the wrong direction.",
  "cosmic horror, eldritch, sickly green, unnatural geometry, oppressive, wrong perspective",
  "an unsettling world with a sickly green-violet cast, geometry that does not resolve, light falling from the wrong direction",
  "cheerful, warm, safe, cute, bright",
  ["noir", "cold", "bleach"], "moderate",
  "video - the wrongness is compositional and i2v tends to normalise it back toward sense",
  "DELIBERATELY NAMES NO CREATURE. The obvious failure is that 'eldritch' or 'Lovecraftian' summons a tentacled thing - a subject, not a style. Every noun here is about light and geometry instead."),

 ("wuxia", "Wuxia", "world", "anime",
  "Chinese martial-fantasy: flowing silk in motion, ink-wash mountains and mist, jade and vermilion, weightless verticality.",
  "wuxia, chinese clothes, flowing silk, misty mountains, jade, vermilion, ethereal",
  "a Chinese martial-fantasy world of flowing silk and ink-wash mountains in mist, jade green and vermilion",
  "western, modern, gritty, urban",
  ["memory", "warm", "overcast"], "strong",
  "video - flowing fabric is a strong motion subject and i2v handles cloth better than faces",
  "Related to ink_wash, which measured as the second-strongest card in the library. If this one underperforms, the fix is to borrow ink_wash's background treatment rather than to strengthen the wuxia tag."),

 ("arcane_magitech", "Arcane magitech", "world", "anime",
  "Magic rendered as engineering: glowing rune-etched metal, suspended crystal, teal and gold energy in physical housings.",
  "magitech, glowing runes, arcane technology, crystal, teal glow, ornate metal",
  "a world where magic is engineered - rune-etched metal glowing teal and gold, suspended crystal in ornate housings",
  "mundane, plain, modern, realistic",
  ["neon", "firelight", "cold"], "moderate",
  "video - emissive glow holds; the rune detail itself will crawl",
  "Named for the Arcane series look, which is where most of the corpus mass sits, but the card describes the idiom so it does not depend on the model knowing the show."),

 ("space_opera", "Space opera", "world", "qwen",
  "Big optimistic science fiction: white and chrome hulls, deep field starlight, hard rim light with a cool fill, vast scale.",
  "space opera, starship, chrome, deep space, rim lighting, epic scale, stars",
  "a grand science-fiction scene, white and chrome surfaces rim-lit hard against deep starfield, cool fill, vast scale",
  "gritty, rusty, small scale, domestic",
  ["cold", "neon"], "moderate",
  "video - starfields are fine high-contrast points and are a known i2v boiling case",
  "PREDICTED NOUN RISK: 'starship' may be drawn as an object beside the subject, exactly as retro_scifi_paperback drew a starship and a gas giant. Kept in because the rim-light clause may carry it alone."),

 ("western_frontier", "Western frontier", "world", "qwen",
  "American frontier: dust and sun-bleached wood, ochre and dry sage, low hard sun, long shadows, heat haze.",
  "western, frontier, dusty, sun-bleached, ochre, harsh sunlight, long shadows",
  "an American frontier scene, dust and sun-bleached timber, ochre and dry sage, low hard sun casting long shadows",
  "lush, green, cold, urban, modern",
  ["golden", "sepia", "sodium"], "strong",
  "video - hard directional sun is stable",
  "The low sun and long shadow do most of the work. This is a LIGHT card wearing a genre name."),

 ("neo_noir", "Neo-noir", "world", "qwen",
  "Noir in colour: wet asphalt reflecting saturated signage, deep blacks with coloured fill, venetian shadow, night always.",
  "neo-noir, wet street, night, saturated reflections, deep shadow, colored light",
  "a neo-noir night scene, wet asphalt reflecting saturated signage, deep blacks lit by coloured fill",
  "daylight, flat lighting, pastel, cheerful",
  ["noir", "neon", "sodium", "cold"], "strong",
  "video - reflective wet ground holds better than most specular surfaces because it is diffuse",
  "Close neighbour of cyberpunk_neon, which measured ready on qwen. The separator is that neo-noir is not futuristic - no holograms, no implants. If they collapse, keep cyberpunk_neon."),

 ("giallo", "Giallo", "world", "qwen",
  "Italian thriller colour: unmotivated saturated gels, red and cold blue in the same frame, hard black shadow, theatrical.",
  "giallo, saturated red lighting, blue shadow, high contrast, theatrical, 1970s thriller",
  "an Italian-thriller look with unmotivated saturated gels, red and cold blue in one frame, hard black shadow",
  "natural lighting, muted, documentary",
  ["noir", "neon", "firelight"], "moderate",
  "video - flat gel colour holds well",
  "The defining move is that the coloured light has NO source in frame. If the model insists on inventing a lamp to justify it, that is the failure to record."),

 # ---------------- art movements ----------------------------------------------------
 ("art_deco", "Art deco", "movement", "anime",
  "Machine-age geometry: symmetry, stepped forms, gold on deep lacquer, sunburst and chevron, sleek stylised figures.",
  "art deco, geometric, symmetrical, gold, black lacquer, sunburst, stylized, 1920s",
  "an art deco composition, symmetrical stepped geometry, gold line on deep lacquer, sunburst and chevron motifs",
  "organic, asymmetrical, rustic, naturalistic",
  ["golden", "sepia", "noir"], "strong",
  "video - flat geometry holds; the ornament will crawl",
  "Neighbour of art_nouveau, which measured compose=replaces because it built an ornamental arch around the figure. Deco's symmetry may do the same. Expect replaces rather than safe."),

 ("bauhaus", "Bauhaus", "movement", "anime",
  "Function as form: primary red-blue-yellow on white, hard geometry, no ornament, flat planes, sans-serif clarity.",
  "bauhaus, primary colors, geometric abstraction, flat design, minimalist, hard edges",
  "a Bauhaus composition of primary red, blue and yellow on white, hard flat geometry, no ornament",
  "ornate, detailed, textured, painterly, realistic",
  ["neutral", "cold"], "moderate",
  "video - completely flat, one of the most stable idioms available",
  "Predicted to fight the subject: a Bauhaus treatment wants to abstract a face into planes and both models resist abstracting faces. flat_vector measured ready and is the safer neighbour."),

 ("constructivist", "Constructivist", "movement", "anime",
  "Soviet agitprop graphics: red-black-cream, hard diagonal composition, photomontage angles, heroic low viewpoint.",
  "constructivism, soviet poster, red and black, diagonal composition, propaganda art, bold",
  "a constructivist composition in red, black and cream, hard diagonals, heroic low viewpoint",
  "soft, pastel, symmetrical, delicate",
  ["bleach", "sepia"], "moderate",
  "video - flat colour holds",
  "PREDICTED TEXT RISK: agitprop implies lettering and both models hallucinate garbled text - screenprint_poster failed exactly this way, producing nonsense letterforms. Text is pushed to the negative here."),

 ("surrealism", "Surrealism", "movement", "anime",
  "Dream logic rendered precisely: impossible juxtaposition painted with academic realism, deep empty perspective, hard shadow.",
  "surrealism, dreamlike, impossible, empty landscape, hard shadow, precise rendering",
  "a surrealist image - impossible juxtaposition rendered with precise academic realism, deep empty perspective and hard shadow",
  "mundane, literal, cluttered, casual",
  ["memory", "golden", "bleach"], "weak",
  "video - the impossible element is exactly what i2v normalises away",
  "Honest expectation: WEAK. Surrealism is a semantic property, not a rendering one, and the effect tiers in this project put semantics at the bottom. Included to be measured, not because it is likely to land."),

 ("cubism", "Cubism", "movement", "anime",
  "Simultaneous viewpoints: the subject fractured into planes and reassembled, muted ochre and grey, shallow space.",
  "cubism, fractured planes, multiple perspectives, geometric abstraction, muted ochre",
  "a cubist treatment - the subject fractured into simultaneous planes and reassembled, muted ochre and grey, shallow space",
  "realistic, single perspective, smooth, photographic",
  ["sepia", "bleach"], "weak",
  "video - not viable, the fracture pattern will reshuffle every frame",
  "Both models resist abstracting faces. Predicted to produce a lightly angular portrait rather than genuine cubism. low_poly_3d measured ready and is the working neighbour if this fails."),

 ("expressionism", "German expressionism", "movement", "anime",
  "Distortion for feeling: skewed perspective, exaggerated hard shadow, harsh angular line, sickly or blown-out value.",
  "german expressionism, distorted perspective, harsh shadows, angular, high contrast, unsettling",
  "a German expressionist treatment - skewed perspective, exaggerated hard shadow, harsh angular line",
  "naturalistic, soft, balanced, gentle",
  ["noir", "bleach", "cold"], "moderate",
  "video - strong value structure holds",
  "Close to gothic_illustration, which measured ready. The separator is the SKEWED PERSPECTIVE. If perspective stays upright the card is doing nothing new."),

 ("pop_art", "Pop art", "movement", "anime",
  "Commercial print language as fine art: flat primary colour, heavy black outline, benday dots, repeated panel logic.",
  "pop art, flat bold colors, thick black outline, halftone dots, high saturation, graphic",
  "a pop art treatment - flat primary colour, heavy black outline, benday dot shading, poster-flat space",
  "subtle, muted, realistic, soft shading",
  ["neon", "neutral"], "moderate",
  "video - flat colour holds well",
  "comic_halftone measured INERT - the dot screen never appeared on either engine. This card leans on flat colour and black outline instead, and the dots are a bonus rather than the mechanism."),

 ("psychedelic_60s", "Psychedelic poster", "movement", "anime",
  "1960s concert poster: writhing organic line, vibrating complementary colour, no negative space, flat.",
  "psychedelic, 1960s poster, swirling patterns, vibrant complementary colors, organic line, flat",
  "a 1960s psychedelic poster treatment - writhing organic linework, vibrating complementary colour, no empty space",
  "muted, realistic, minimal, sparse",
  ["neon"], "moderate",
  "video - dense pattern is a boiling risk but the flatness helps",
  "The vibrating colour pairs are the mechanism. If the model produces merely 'colourful' rather than optically vibrating, that is a partial and should be recorded as weak."),

 ("pre_raphaelite", "Pre-Raphaelite", "movement", "anime",
  "Jewel-toned romantic realism: intense local colour, botanical precision, flowing hair and drapery, even unshadowed light.",
  "pre-raphaelite, jewel tones, detailed botanicals, flowing hair, romantic, even lighting",
  "a Pre-Raphaelite painting - intense jewel-toned local colour, botanical precision, flowing hair and drapery, even light",
  "flat, minimal, modern, harsh lighting",
  ["golden", "memory", "warm"], "strong",
  "video - static and evenly lit, a safe i2v candidate",
  "The even, near-shadowless light is the strongest single signal and it is what separates this from baroque_painting, which measured ready on chiaroscuro."),

 ("pointillism", "Pointillism", "movement", "anime",
  "Colour mixed in the eye: the whole image built from discrete dots of pure hue, no blending, luminous.",
  "pointillism, dots of pure color, optical mixing, luminous, no blending",
  "a pointillist painting built entirely from discrete dots of pure colour, mixing optically, luminous",
  "smooth, blended, photographic, flat",
  ["golden", "warm"], "moderate",
  "video - not viable, a dot field is the worst case for temporal stability",
  "manga_screentone proved this engine CAN produce a dot field, which is the reason to expect pointillism to work where comic_halftone did not."),

 ("brutalist", "Brutalist", "movement", "qwen",
  "Raw concrete as aesthetic: massive unadorned forms, board-marked surfaces, grey monochrome, hard overhead light, oppressive scale.",
  "brutalist architecture, raw concrete, massive forms, monochrome grey, harsh light",
  "a brutalist treatment - raw board-marked concrete in massive unadorned forms, grey monochrome, hard overhead light",
  "ornate, warm, wooden, decorative, soft",
  ["cold", "overcast", "bleach"], "strong",
  "video - large static forms are the most stable case there is",
  "PREDICTED RISK: this is really an ARCHITECTURE card and may override the place layer entirely, like ghibli_pastoral. Expect compose=replaces."),

 # ---------------- illustration traditions ------------------------------------------
 ("ligne_claire", "Ligne claire", "illustration", "anime",
  "Uniform-weight ink line, flat unmodulated colour, no hatching and no cast shadow, every object equally in focus.",
  "ligne claire, clean uniform lineart, flat colors, no shading, european comic, clear",
  "a ligne claire treatment - uniform-weight ink outline, flat unmodulated colour, no hatching or cast shadow",
  "sketchy, painterly, heavy shading, gradient, textured",
  ["neutral", "warm"], "strong",
  "video - the flattest idioms hold best; this should be among the top performers",
  "The Moebius/Herge tradition. Distinct from flat_vector (which measured ready) because ligne claire keeps a drawn outline where vector has none."),

 ("american_comic", "American comic", "illustration", "anime",
  "Superhero-era print: heavy varied ink weight, muscular exaggerated anatomy, saturated primaries, dramatic low angle.",
  "american comic book, bold inking, dynamic pose, saturated primary colors, dramatic angle",
  "an American comic-book treatment - heavy varied ink weight, saturated primaries, dramatic low camera angle",
  "soft, pastel, delicate, realistic, muted",
  ["neon", "warm"], "moderate",
  "video - flat colour holds, ink weight may flicker",
  "PREDICTED POSE RISK: 'dynamic pose' may rewrite blocking the way sakuga_impact did, which measured compose=injects for changing the figure's pose. Watch for it."),

 ("golden_age_illustration", "Golden-age illustration", "illustration", "anime",
  "Early-20th-century magazine painting: warm naturalistic palette, confident brush, staged domestic composition, sentimental light.",
  "golden age illustration, painted, warm palette, naturalistic, rockwell style, nostalgic",
  "an early-twentieth-century magazine illustration - warm naturalistic painting, confident brushwork, sentimental light",
  "harsh, modern, digital, cold, edgy",
  ["sepia", "golden", "memory"], "moderate",
  "video - warm static painting is stable",
  "Overlaps storybook_illustration, which measured ready. The separator is adult subject matter and a heavier paint quality."),

 ("woodcut", "Woodcut", "illustration", "anime",
  "Carved relief print: stark black on cream, gouged parallel line, no grey except through hatch density, visible tool marks.",
  "woodcut, relief print, black and white, carved lines, hatching, high contrast, cream paper",
  "a woodcut relief print - stark black ink on cream paper, gouged parallel linework, tone only through hatch density",
  "smooth, grayscale gradient, painterly, color",
  ["bleach", "sepia", "noir"], "strong",
  "video - two-tone flat, very stable",
  "Neighbour of ukiyo_e (measured ready) but Western and monochrome. The mechanism is the same one that made ukiyo_e work: a carved line the corpus knows well."),

 ("linocut", "Linocut", "illustration", "anime",
  "Softer relief print: bolder simplified shapes than woodcut, slightly ragged edge, often one or two spot colours on cream.",
  "linocut, block print, bold simplified shapes, spot color, ragged edge, cream paper",
  "a linocut block print - bold simplified shapes with slightly ragged edges, one or two spot colours on cream",
  "detailed, photographic, smooth gradient",
  ["bleach", "sepia"], "moderate",
  "video - flat, stable",
  "Likely to collapse into woodcut. If it does, keep woodcut - it has more corpus mass - and drop this."),

 ("scratchboard", "Scratchboard", "illustration", "anime",
  "White line scratched out of solid black: the inverse of pen and ink, luminous highlights emerging from darkness.",
  "scratchboard, white lines on black, engraved, high contrast, inverted linework",
  "a scratchboard illustration - fine white lines scratched from a solid black ground, luminous highlight emerging from darkness",
  "white background, soft, painterly, color",
  ["noir", "bleach"], "moderate",
  "video - high-contrast fine line is a boiling risk",
  "The inversion is what makes this interesting and also what makes it fragile: if the model reverts to black-on-white it has produced pencil_sketch, which already exists and measured ready."),

 ("illuminated_manuscript", "Illuminated manuscript", "illustration", "anime",
  "Medieval devotional page: gold leaf, flat symbolic space with no perspective, vermilion and ultramarine, dense marginal ornament.",
  "illuminated manuscript, gold leaf, medieval art, flat perspective, vermilion, ultramarine, ornate border",
  "an illuminated manuscript page - gold leaf on vellum, flat symbolic space without perspective, vermilion and ultramarine, dense ornament",
  "realistic perspective, photographic, modern, muted",
  ["golden", "sepia"], "moderate",
  "video - ornament will crawl badly",
  "PREDICTED NOUN RISK: 'border' and 'page' are objects and art_nouveau already measured compose=replaces for building an ornamental frame. Expect the same and record it honestly."),

 ("propaganda_poster", "Propaganda poster", "illustration", "anime",
  "Mid-century state graphics: limited flat palette, heroic upward-looking figure, hard diagonal, simplified monumental forms.",
  "propaganda poster, limited palette, heroic figure, low angle, bold flat shapes, monumental",
  "a mid-century propaganda poster - limited flat palette, heroic upward-looking figure, hard diagonal composition",
  "delicate, realistic, subtle, detailed",
  ["bleach", "sepia"], "moderate",
  "video - flat colour holds",
  "TEXT IS IN THE NEGATIVE for the reason screenprint_poster failed: both models hallucinate garbled lettering when a card implies typography."),

 ("pulp_cover", "Pulp cover", "illustration", "anime",
  "Mid-century paperback painting: lurid saturated colour, dramatic single light source, painted realism, high-contrast melodrama.",
  "pulp art, lurid colors, dramatic lighting, painted realism, vintage paperback, melodramatic",
  "a mid-century pulp cover painting - lurid saturated colour under one dramatic light source, painted realism",
  "subtle, muted, minimal, flat",
  ["firelight", "noir", "sepia"], "moderate",
  "video - painted surfaces hold moderately",
  "retro_scifi_paperback measured compose=injects - it drew a starship and a planet rather than styling. This card deliberately names NO genre furniture, only the painting quality, to test whether that was the cause."),

 ("airbrush_70s", "70s airbrush", "illustration", "anime",
  "Van-art and record-sleeve airbrush: smooth impossible gradients, glowing chrome, sunset spectrum, soft-edged everything.",
  "airbrush, 1970s, smooth gradient, chrome, sunset colors, soft edges, glossy",
  "a 1970s airbrush illustration - smooth impossible gradients, glowing chrome, sunset spectrum, every edge soft",
  "hard edges, sketchy, matte, textured",
  ["golden", "neon", "warm"], "moderate",
  "video - smooth gradients are stable; chrome is not",
  "Shares the chrome problem with y2k_chrome. Where they differ is edge quality - airbrush has none, y2k has hard speculars."),

 ("tattoo_flash", "Tattoo flash", "illustration", "anime",
  "Traditional tattoo sheet: heavy black outline, limited red-green-yellow palette, bold simplified iconography, flat cream ground.",
  "traditional tattoo flash, heavy black outline, limited palette, bold simple shapes, flat",
  "a traditional tattoo flash treatment - heavy black outline, limited red green and yellow palette, bold simplified forms on cream",
  "detailed, realistic, gradient, photographic",
  ["neutral", "sepia"], "moderate",
  "video - flat and bold, stable",
  "PREDICTED NOUN RISK: may draw tattoos ON the subject rather than rendering the image AS flash. That is the chalkboard failure pattern and this card is a good test of it."),

 ("graffiti", "Graffiti", "illustration", "anime",
  "Aerosol on concrete: overspray haze, hard stencil edge against soft spray, saturated fill with black outline, layered over texture.",
  "graffiti, spray paint, aerosol texture, bold outline, saturated fill, concrete texture, street art",
  "an aerosol street-art treatment - overspray haze and hard stencil edges, saturated fill with black outline over concrete texture",
  "clean, smooth, delicate, painterly",
  ["neon", "sodium"], "moderate",
  "video - texture-heavy, expect crawl",
  "PREDICTED NOUN RISK: high. 'graffiti' will likely be drawn as graffiti on a wall BEHIND the subject rather than as the rendering idiom - the exact chalkboard failure. Authored anyway because the measurement is the point."),

 # ---------------- anime studio idioms ----------------------------------------------
 ("ufotable_glow", "Ufotable glow", "anime", "anime",
  "Compositing-heavy modern anime: layered bloom, particle light, deep gradient skies, digital effects over painted backgrounds.",
  "ufotable style, glowing effects, particle effects, bloom, gradient sky, digital compositing",
  "a modern anime look with heavy compositing - layered bloom and particle light over painted backgrounds, deep gradient sky",
  "flat, retro, matte, muted",
  ["neon", "firelight", "cold"], "moderate",
  "video - bloom holds; particles will not",
  "Separates from modern_anime (measured ready) by the COMPOSITING, not the drawing. If both land the same, this one is redundant."),

 ("kyoani_soft", "KyoAni soft", "anime", "anime",
  "Naturalistic slice-of-life anime: delicate line, soft ambient occlusion, real lens bokeh in a drawn image, gentle warm palette.",
  "kyoto animation style, soft shading, delicate lineart, bokeh, warm natural light, detailed background",
  "a naturalistic slice-of-life anime look - delicate line, soft shading, drawn bokeh, gentle warm daylight",
  "harsh, flat, high contrast, retro",
  ["warm", "golden", "memory"], "moderate",
  "video - soft light is stable",
  "Very close to slice_of_life_anime (measured ready). Kept separate because the drawn-bokeh background treatment is genuinely distinct; drop it if the renders match."),

 ("trigger_kinetic", "Trigger kinetic", "anime", "anime",
  "Exaggerated motion anime: extreme perspective, thick tapering line, limited high-saturation palette, deliberate rough energy.",
  "studio trigger style, exaggerated perspective, thick tapering lines, limited saturated palette, kinetic",
  "an exaggerated kinetic anime look - extreme perspective, thick tapering line, a small very saturated palette",
  "realistic, subtle, soft, detailed",
  ["neon", "warm"], "moderate",
  "video - bold line holds well",
  "Neighbour of shonen_action, which measured compose=replaces for shattering the background. Watch whether this does the same."),

 ("monogatari_geometric", "Geometric minimal anime", "anime", "anime",
  "Shaft-style graphic abstraction: flat colour fields replacing backgrounds, stark geometry, extreme negative space, red-white-black.",
  "geometric abstraction, flat color background, minimal, stark composition, negative space, red and white",
  "a graphically abstract anime look - flat colour fields instead of a background, stark geometry, extreme negative space",
  "detailed background, realistic, cluttered",
  ["neutral", "noir"], "moderate",
  "video - completely flat backgrounds are maximally stable",
  "This card DELETES the setting by design - it replaces backgrounds with colour fields. Expect compose=replaces and mark it so; that is a correct behaviour here, not a fault."),

 ("iyashikei", "Iyashikei", "anime", "anime",
  "Healing-genre calm: no conflict in the frame, wide quiet composition, soft natural light, muted green and cream, gentle.",
  "iyashikei, calm, peaceful, soft natural light, muted green, wide quiet composition, gentle",
  "a calm healing-genre anime look - quiet wide composition, soft natural light, muted greens and cream, nothing tense",
  "dramatic, dark, high contrast, action",
  ["warm", "overcast", "memory"], "weak",
  "video - calm and static, very stable",
  "Honest expectation: WEAK. 'Peaceful' is a quality, not a thing, and this project has repeatedly measured that qualities do not render. The palette clause is the only part likely to land."),

 ("retro_shoujo_70s", "70s shoujo", "anime", "anime",
  "Classic girls-comic: enormous starred eyes, fine feathered line, screentone flowers, vertical elongation, sepia-rose palette.",
  "1970s shoujo, huge sparkling eyes, delicate lineart, screentone, elongated figure, rose and sepia",
  "a 1970s girls-comic look - very large starred eyes, fine feathered line, screentone, elongated figure, rose and sepia",
  "modern, realistic proportions, digital, harsh",
  ["sepia", "memory", "faded_film"], "strong",
  "video - flat with fine line; line will flicker",
  "Distinct from shojo_soft (measured compose=replaces, it built a flower field). This is a PERIOD card - the elongation and eye size are the mechanism, and it may avoid the setting-override."),

 ("josei_muted", "Josei muted", "anime", "anime",
  "Adult women's manga: restrained realistic proportion, muted desaturated palette, fine line, understated expression.",
  "josei, realistic proportions, muted palette, fine lineart, understated, adult",
  "an adult women's-manga look - realistic restrained proportion, muted desaturated palette, fine line, understated expression",
  "exaggerated, saturated, cute, chibi",
  ["neutral", "overcast", "memory"], "moderate",
  "video - stable",
  "Close to seinen_grounded (measured ready, though subtle at 20.6 from control). If these two match, keep one."),

 # ---------------- 3D / CG ----------------------------------------------------------
 ("pixar_3d", "3D animated feature", "3d", "qwen",
  "Modern CG animation: subsurface-scattered skin, soft global illumination, appealing stylised proportion, everything slightly rounded.",
  "3d animated movie, subsurface scattering, soft global illumination, stylized proportions, rounded forms",
  "a modern 3D-animated feature look - subsurface skin, soft global illumination, appealing stylised proportion, rounded forms",
  "flat, 2d, lineart, photorealistic, harsh",
  ["warm", "golden", "neutral"], "strong",
  "video - smooth GI surfaces are among the more stable i2v subjects",
  "claymation measured ready on qwen, which is the evidence that this engine can do rendered-CG surfaces. Named by medium rather than by studio to avoid depending on a brand token."),

 ("unreal_render", "Real-time engine render", "3d", "qwen",
  "Game-engine realism: physically-based materials, ray-traced reflection, volumetric light shafts, slightly too-clean surfaces.",
  "unreal engine render, physically based rendering, ray tracing, volumetric lighting, hyperreal, clean",
  "a real-time engine render - physically based materials, ray-traced reflection, volumetric light shafts, surfaces slightly too clean",
  "hand drawn, painterly, sketchy, flat",
  ["cold", "neon", "firelight"], "moderate",
  "video - volumetrics hold, reflections do not",
  "'Unreal engine' is one of the highest-mass quality tokens in the whole SD corpus, which is why it is in the tags. Its risk is that it acts as a generic quality booster rather than a style."),

 ("voxel", "Voxel", "3d", "qwen",
  "Everything built from uniform cubes: blocky volumetric forms, hard cube faces, simple flat shading, visible grid.",
  "voxel art, cubes, blocky, isometric, flat shading, minecraft style, grid",
  "a voxel construction - the whole scene built from uniform cubes with hard faces and simple flat shading",
  "smooth, curved, organic, detailed, realistic",
  ["neutral", "cold"], "moderate",
  "video - hard-edged blocks are stable",
  "eight_bit measured ready on qwen and pixel_art measured ready on the illustration engine, so quantised forms clearly work on this box. Voxel is the 3D case of the same thing."),

 ("ps1_lowpoly", "PS1-era 3D", "3d", "qwen",
  "Fifth-generation console 3D: very low polygon counts, warped affine texture mapping, dithered low-colour textures, no filtering.",
  "ps1 graphics, low poly, affine texture warping, dithered textures, retro 3d, jagged",
  "a fifth-generation console 3D look - very low polygon count, warped affine texturing, dithered low-colour textures, unfiltered and jagged",
  "smooth, high detail, modern, antialiased",
  ["faded_film", "cold"], "moderate",
  "video - the artifacts are per-frame and will not be temporally coherent",
  "low_poly_3d measured ready on the illustration engine. This is the harsher, more specific case: the texture warping is the separator, not the polygon count."),

 # ---------------- photographic sub-styles -------------------------------------------
 ("infrared_photo", "Infrared", "photo", "qwen",
  "False-colour infrared: foliage rendered white or magenta, skies near-black, skin waxy and luminous, high strange contrast.",
  "", "an infrared photograph - foliage rendered white, sky nearly black, skin waxy and luminous, false colour",
  "normal colors, natural, muted",
  ["bleach", "cold"], "strong",
  "video - false colour is a global mapping and holds",
  "Genuinely distinctive and hard to confuse with anything else in the library. The foliage inversion is the single strongest cue."),

 ("cross_processed", "Cross-processed", "photo", "qwen",
  "Wrong-chemistry film: crushed contrast, cyan shadows and yellow-green highlights, blown channels, unpredictable colour shift.",
  "", "a cross-processed photograph - crushed contrast with cyan shadows and yellow-green highlights, shifted unnatural colour",
  "natural color, balanced, neutral",
  ["cold", "bleach", "faded_film"], "moderate",
  "video - a global colour shift, very stable",
  "NOTE this may be better as a deterministic ffmpeg grade in looks/ than as a prompt style - the project already has a colour-grade layer and a channel curve is exactly what that layer is for."),

 ("cyanotype", "Cyanotype", "photo", "qwen",
  "Sun-printed blue: monochrome Prussian blue on textured paper, soft edges, contact-print flatness.",
  "", "a cyanotype print - monochrome Prussian blue on textured paper, soft edges, flat contact-print tonality",
  "color, sharp, digital, high contrast",
  ["cold", "faded_film"], "strong",
  "video - single-hue monochrome is maximally stable",
  "blueprint measured ready on qwen and shares the blue-monochrome mechanism, which is the evidence this will land. The separator is that cyanotype is photographic and blueprint is drafted."),

 ("daguerreotype", "Daguerreotype", "photo", "qwen",
  "Earliest photography: mirror-silver surface, extremely shallow depth, slight solarisation at the edges, rigid formal stillness.",
  "", "a daguerreotype - mirrored silver plate with extremely shallow depth of field, edge solarisation, rigid formal stillness",
  "modern, color, casual, sharp",
  ["sepia", "bleach", "memory"], "moderate",
  "video - the stillness is the point and motion destroys it",
  "Neighbour of tintype (measured ready). The separator is the mirror-silver surface and the solarised edge; if they collapse, keep tintype."),

 ("kodachrome", "Kodachrome", "photo", "qwen",
  "Mid-century colour reversal film: deep saturated reds, controlled contrast, fine grain, warm midtones that never go garish.",
  "", "a Kodachrome photograph - deep saturated reds with controlled contrast, fine grain, warm midtones",
  "washed out, flat, digital, oversaturated",
  ["golden", "warm", "memory"], "moderate",
  "video - a stable global look",
  "Overlaps film_35mm (measured ready but subtle). The separator is the specific red response. If they match, this is redundant."),

 ("cinestill_night", "CineStill night", "photo", "qwen",
  "Remjet-removed tungsten film: halated red bloom around every light source, cyan-shifted shadows, grainy night.",
  "", "a CineStill 800T night photograph - red halation blooming around every light source, cyan-shifted shadow, visible grain",
  "clean, daylight, sharp, digital",
  ["neon", "sodium", "noir"], "strong",
  "video - halation is a per-light bloom and should hold",
  "The red halo around point lights is unmistakable and very likely to land - it is a strong visual token with real corpus mass. Best paired with a night place."),

 ("street_bw", "Black-and-white street", "photo", "qwen",
  "Documentary monochrome: available light, deep blacks, grain, decisive-moment framing, high contrast without gloss.",
  "", "a black-and-white street photograph - available light, deep blacks, visible grain, unposed decisive framing",
  "color, studio lighting, posed, clean",
  ["noir", "bleach"], "strong",
  "video - monochrome is stable",
  "Distinct from noir_comic (measured ready on qwen but drawn, not photographic) and from war_photography (which carries conflict connotations this does not)."),

 ("tilt_shift", "Tilt-shift", "photo", "qwen",
  "Miniature-faking optics: a narrow band of focus with strong blur above and below, exaggerated saturation, high viewpoint.",
  "", "a tilt-shift photograph - a narrow band of sharp focus with heavy blur above and below, saturated colour, high viewpoint",
  "everything in focus, flat lighting, low angle",
  ["neutral", "golden"], "moderate",
  "video - the blur gradient is fixed and holds well",
  "PREDICTED RISK: drone_aerial measured compose=injects because it failed to move the camera - viewpoint is a shot property, not a style. Tilt-shift also implies a high viewpoint and may fail the same way, landing only the blur."),

 ("double_exposure", "Double exposure", "photo", "qwen",
  "Two frames on one negative: a silhouette filled with a second scene, blended luminance, ghosted overlap.",
  "", "a double exposure - a portrait silhouette filled with a second overlapping scene, blended by luminance, ghosted",
  "single image, opaque, flat",
  ["bleach", "noir", "memory"], "moderate",
  "video - not viable, the two layers will drift independently",
  "One of the few compositional styles in the library. If it merely produces a faint overlay rather than a genuine silhouette fill, record that as weak."),

 ("thermal_imaging", "Thermal", "photo", "qwen",
  "Heat as image: black-body colour ramp from blue to white, no texture at all, glowing bodies against a cold ground.",
  "", "a thermal image - a blue-to-white heat colour ramp, no surface texture, warm bodies glowing against a cold ground",
  "natural color, texture, detail, daylight",
  ["cold", "neon"], "strong",
  "video - a global false-colour mapping, very stable",
  "Extremely distinctive and unlikely to be confused with anything. The risk is the opposite of the usual one - it may be SO strong that it erases the character and the setting together."),

 # ---------------- cultural traditions ------------------------------------------------
 ("gongbi", "Gongbi", "tradition", "anime",
  "Chinese court painting: fine even outline, layered translucent mineral colour, flat gold-silk ground, meticulous stillness.",
  "gongbi, chinese painting, fine outline, mineral pigments, silk ground, meticulous, flat",
  "a gongbi painting - fine even outline with layered translucent mineral colour on a flat silk ground, meticulous",
  "loose, expressive, impasto, western",
  ["golden", "warm", "memory"], "moderate",
  "video - flat and still",
  "The counterpart to ink_wash (which measured among the strongest cards): gongbi is the meticulous coloured tradition where ink_wash is the spontaneous monochrome one."),

 ("persian_miniature", "Persian miniature", "tradition", "anime",
  "Flat jewel-toned space with no perspective, gold ground, intricate pattern everywhere, figures in stacked registers.",
  "persian miniature, flat perspective, jewel tones, gold ground, intricate patterns, ornate",
  "a Persian miniature - flat jewel-toned space without perspective, gold ground, intricate pattern across every surface",
  "realistic perspective, photographic, muted, sparse",
  ["golden", "warm"], "moderate",
  "video - dense pattern will crawl",
  "Shares the no-perspective flatness with illuminated_manuscript. Both are predicted to risk becoming an ornamental frame the way art_nouveau did."),

 ("byzantine_icon", "Byzantine icon", "tradition", "anime",
  "Gold-ground devotional panel: flat gold behind the figure, elongated stylised features, no cast shadow, hieratic frontality.",
  "byzantine icon, gold background, flat, elongated features, religious art, hieratic, no shadow",
  "a Byzantine icon - flat gold ground behind an elongated stylised figure, no cast shadow, rigid frontal pose",
  "realistic, perspective, casual pose, shadow",
  ["golden", "sepia"], "strong",
  "video - completely flat and static",
  "The flat gold ground DELETES the setting by design, so expect compose=replaces. Like monogatari_geometric, that is correct behaviour rather than a fault."),

 ("mexican_muralism", "Mexican muralism", "tradition", "anime",
  "Public mural painting: monumental simplified figures, earth reds and ochres, strong outline, compressed heroic space.",
  "mural painting, monumental figures, earth tones, bold outline, rivera style, heroic",
  "a mural painting - monumental simplified figures in earth reds and ochres, strong outline, compressed heroic space",
  "delicate, pastel, small scale, photographic",
  ["warm", "sepia", "golden"], "moderate",
  "video - flat mural surfaces are stable",
  "The monumental figure scale is the mechanism. Related to propaganda_poster but painted rather than printed, and warmer."),

 ("ukiyo_e_shin_hanga", "Shin-hanga", "tradition", "anime",
  "Early-20th-century woodblock revival: ukiyo-e technique with Western light and atmosphere, soft gradient skies, quiet realism.",
  "shin hanga, woodblock print, atmospheric, soft gradient sky, japanese print, realistic light",
  "a shin-hanga woodblock print - traditional Japanese printing with Western atmospheric light, soft gradient sky, quiet realism",
  "flat, graphic, harsh, modern",
  ["memory", "overcast", "warm"], "moderate",
  "video - flat print surfaces hold",
  "The atmospheric gradient sky is what separates this from ukiyo_e (measured ready). If they collapse, keep ukiyo_e."),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    written = skipped = 0
    for (sid, name, family, engine, means, tags, prose, neg, looks, strength,
         works, note) in CARDS:
        p = os.path.join(OUT, sid + ".json")
        if os.path.exists(p):
            print("  exists, skipped: %s" % sid)
            skipped += 1
            continue
        d = {
            "id": sid, "name": name, "family": family, "engine": engine,
            "means": means, "tags": tags, "prose": prose, "negative_add": neg,
            "suits_looks": looks, "strength": strength, "works_for": works,
            "status": "untested",
            "note": note + (" | Authored in the second wave, after the first 64 were "
                            "rendered and measured. status=untested because nothing here "
                            "has been rendered yet - the first wave shipped 46 cards "
                            "marked ready without a single render and 27 of 64 turned out "
                            "to be routed to the wrong engine."),
        }
        json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        open(p, "a").write("\n")
        written += 1
    print("\n  %d written, %d skipped" % (written, skipped))
    fams = {}
    for c in CARDS:
        fams[c[2]] = fams.get(c[2], 0) + 1
    print("  families:", fams)


if __name__ == "__main__":
    main()
