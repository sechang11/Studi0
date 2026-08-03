import json, re, os, sys, glob

D = '/home/k4shix/ComfyUI/venv/lib/python3.14/site-packages/comfyui_workflow_templates_json/templates/'
want = sys.argv[1:] or [
    'audio_ace_step_1_5_checkpoint', 'audio_ace_step_1_5_split', 'audio_ace_step1_5_xl_turbo',
    'audio_stable_audio_3_medium', 'video_wan2_2_14B_t2v', 'video_ltx2_3_i2v', 'video_ltx2_3_t2v',
    'image_z_image_turbo', 'image_flux2_klein_text_to_image', '3d_hunyuan3d-v2.1',
    'utility_video_frame_interpolation', 'utility-gan_upscaler',
    'utility_birefnet_remove_background', 'utility_depth_anything3_image_depth_estimation',
    'utility_image_segment_sam3', 'utility_seedvr2_3b_int8_upscale_image',
    'image_qwen_image_edit_2511', 'utility_sdpose_ood_image_to_pose',
    'video_wan21_scail2_character_replacement', 'image_chroma_text_to_image',
]
for name in want:
    p = D + name + '.json'
    if not os.path.exists(p):
        print('## MISSING', name)
        continue
    txt = open(p).read()
    urls = sorted(set(re.findall(r'https://huggingface\.co/[^\s\)"\\]+', txt)))
    urls = [u for u in urls if '/resolve/' in u]
    print('##', name)
    for u in urls:
        print('   ', u)
