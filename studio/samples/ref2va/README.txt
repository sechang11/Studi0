The ref_*.{mp4,json,png,jpg} files at THIS level were rendered 2026-09-07 with workflow 63's
nested ref_images dict. ComfyUI's Autogrow input reads only flat dotted 0-indexed ids
("ref_images.ref_image_0"), so NO reference picture reached the model in any of them: their
identity scores measure the prompt alone. Fixed 2026-09-17 (LTX_PLAYBOOK §97). Correctly wired
renders: wired/. Unwired renders from the day of the fix: _unwired_nested_dict/.
