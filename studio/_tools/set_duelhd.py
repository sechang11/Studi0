#!/usr/bin/env python3
"""studio/_tools/set_duelhd.py - the duel's clearing with a skin (2026-10-01).

The same geometry as set_duel.py, its flat colours replaced by procedural materials Eevee renders at once:
bark in vertical grooves, leaves mottled, the forest floor a mix of soil, moss and leaf litter, the path
packed dirt with pebbles, stone and rock cracked and lichened. The question it answers: does a set with a
detailed skin give the dress (Qwen-Image-2.1) more to keep - more detailed, more consistent start frames -
or does the dress repaint it anyway? Run inside Blender; "set": "duelhd".
"""
import bpy

import set_duel as D
import set_forest as F

TONES = {   # material: (dark, light, bump strength, pattern)
    "bark": ("#2e241c", "#5e4a38", 0.7, "bark"), "bark_dark": ("#1f1813", "#3f3127", 0.7, "bark"),
    "deadwood": ("#4a453f", "#8a8277", 0.6, "bark"), "leaf_dark": ("#142a19", "#2f4d2c", 0.25, "leaf"),
    "leaf_mid": ("#21401f", "#4a6b33", 0.25, "leaf"), "leaf_light": ("#3a5a28", "#6f8f40", 0.25, "leaf"),
    "floor": ("#2a2619", "#5b5232", 0.4, "floor"), "dirt": ("#5e4a30", "#a08259", 0.35, "dirt"),
    "moss": ("#33501f", "#6f8c3a", 0.45, "floor"), "rock": ("#4f4f4a", "#9a978c", 0.8, "stone"),
    "stone": ("#5d5a50", "#aca693", 0.8, "stone"), "thorn": ("#3d1f1c", "#6e3a33", 0.4, "bark"),
    "vine": ("#1d3320", "#3f5f37", 0.3, "leaf"),
}


def _skin(name, dark, light, bump, pattern):
    m = F.P.MAT.get(name)
    if m is None or m.node_tree is None:
        return
    nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return
    co = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = {"bark": 6.0, "leaf": 3.0, "floor": 1.6, "dirt": 3.5, "stone": 4.0}[pattern]
    noise.inputs["Detail"].default_value = 12.0
    if "Roughness" in noise.inputs:
        noise.inputs["Roughness"].default_value = 0.62
    nt.links.new(co.outputs["Object"], noise.inputs["Vector"])
    fac = noise.outputs["Fac"]
    if pattern == "bark":                         # long vertical grooves
        wave = nt.nodes.new("ShaderNodeTexWave")
        wave.wave_type = "BANDS"
        wave.bands_direction = "X"
        wave.inputs["Scale"].default_value = 9.0
        wave.inputs["Distortion"].default_value = 9.0
        wave.inputs["Detail"].default_value = 6.0
        nt.links.new(co.outputs["Object"], wave.inputs["Vector"])
        mix = nt.nodes.new("ShaderNodeMath")
        mix.operation = "MULTIPLY"
        nt.links.new(wave.outputs["Fac"], mix.inputs[0])
        nt.links.new(noise.outputs["Fac"], mix.inputs[1])
        fac = mix.outputs[0]
    elif pattern in ("leaf", "stone", "floor"):   # cells: leaves in clumps, cracks, litter
        vor = nt.nodes.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = {"leaf": 22.0, "stone": 7.0, "floor": 14.0}[pattern]
        nt.links.new(co.outputs["Object"], vor.inputs["Vector"])
        mix = nt.nodes.new("ShaderNodeMath")
        mix.operation = "ADD"
        nt.links.new(vor.outputs["Distance"], mix.inputs[0])
        nt.links.new(noise.outputs["Fac"], mix.inputs[1])
        half = nt.nodes.new("ShaderNodeMath")
        half.operation = "MULTIPLY"
        half.inputs[1].default_value = 0.6
        nt.links.new(mix.outputs[0], half.inputs[0])
        fac = half.outputs[0]
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[0].color = (*F.P.lin(dark), 1.0)
    ramp.color_ramp.elements[1].color = (*F.P.lin(light), 1.0)
    nt.links.new(fac, ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = bump
    nt.links.new(fac, bmp.inputs["Height"])
    nt.links.new(bmp.outputs["Normal"], bsdf.inputs["Normal"])


def build(sc, seed=0):
    info = D.build(sc, seed)
    for name, (dark, light, bump, pattern) in TONES.items():
        _skin(name, dark, light, bump, pattern)
    info["set"] = "duelhd"
    return info


def act(name, sc, frames, info):
    return D.act(name, sc, frames, info)
