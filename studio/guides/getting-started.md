# Getting started

The shortest route from opening the app to a finished thing. Buttons are named exactly
as they appear.

If you have not read [The mental model](/guide/mental-model), read it after this. You
can follow these steps without it, but you will not understand why the app asked you
what it asked you.

---

## Route A — one picture, about five minutes

Use this first. It is the fewest decisions between you and an image.

1. Open the app. You land on the hub, titled **studio**.
2. In the hero panel at the top there are two buttons. Ignore the blue one for now and
   click the grey **Make something else**. (Or type `/make` in the address bar.)
3. You are on **make**. A row of tiles appears: **Image**, **Voice**, **Music**,
   **Sound effect**, **3D asset**. Click **Image**.
4. A form appears on the left. Fill in the description field. Write one plain sentence.
   Leave everything else on its default.
5. Optional but recommended: click **Preview workflow** first. It shows you the exact
   graph that will be sent, without spending GPU time. Nothing is queued.
6. Click **Generate**.
7. The **Result** panel on the right fills in when the render lands.
8. Click **gallery** in the nav. Your image is at the end, carrying the recipe that
   made it.

That is the whole loop: pick a maker, fill a form, generate, look at it in the gallery.

---

## Route B — a scene, which is what the app is actually for

This is the wizard. It produces a `.movie` file and then renders it.

1. From the hub, click the blue **Direct a scene →** button.
2. You are on **Direct a scene**. Eight steps run across the top:
   **Start · Format · Layer stack · Look & pace · Place & time · Cast · Shots · Review**.
   Move with **Next →** and **← Back**, or click a step name to jump.
3. **Start** — pick a template, or start from scratch. If you start from a template,
   check whether it sets a style; 20 of the 82 templates do not, and those silently
   route you to the illustration engine.
4. **Format** — canvas and fps. The defaults (1920x1080, 24) are fine. Move on.
5. **Layer stack** — the important one. Bands are stacked in containment order.
   - Open the **Style** band and pick one. Do this before anything else. Style decides
     which model renders, and the page tells you which engine you just chose.
   - Open **Place** and pick a setting.
   - **Character** is optional. Leave it empty for a landscape.
   - **Wear**, **Lighting**, **Weather** are modifiers. Skip them on a first pass.
   - **Style LoRA** is indented under Style on purpose. Leave it empty; empty means
     "follow the style's recommendation", not "none".
6. **Look & pace** — pick a look, or leave it empty. Remember it is a grade applied
   after generation, so it can be changed later without re-rendering. Avoid `night`
   for now; see the mental model.
7. **Place & time** and **Cast** — confirm what you already picked. Cast lets you add a
   character from the cast library.
8. **Shots** — add at least one beat. A beat is one shot. If you want anything to move,
   name a motion card here; a beat that names no motion resolves to a hold.
9. **Review** — read the panel. It shows the resolved prompt, the engine, and any
   conflict between layers. Fix conflicts here, before spending GPU time.
10. On the right, under **Save & render**: the **Your .movie** box shows the file you
    have authored. Put a name in the text field (it defaults to `my-scene`).
11. Click **Save** to write the file only, or **Save & render →** to write it and start
    the render.
12. Watch the **Saved** line under the buttons. When it finishes, the clip appears
    under **video**.

---

## Where to go when it comes out wrong

| what happened | read |
|---|---|
| It is drawn and I wanted a photo, or vice versa | [Styles](/guide/styles) |
| The face is mush | [Cast](/guide/cast) |
| Nothing moved | [Motions](/guide/motions) |
| A thing I never asked for is in frame | [The mental model](/guide/mental-model), section 5 |
| The shot came back black | [The mental model](/guide/mental-model), section 4 |
| I cannot find the picture again | [Gallery](/guide/gallery) |

---

## The one habit worth forming

Every library in this app separates **what has been rendered and looked at** from
**what is still someone's opinion**. That is the coloured bar under each library card
on the hub — green is measured, amber is weak, red does not work and the card says why,
grey has never been rendered.

Prefer green cards until you know the library. A grey card is not a promise. It is an
untested claim.
