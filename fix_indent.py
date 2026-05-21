with open('backend/modal_backend.py', 'r', encoding='utf-8') as f:
    lines = f.read().split('\n')

# The goal is to make sure everything from `def pil_to_cv2(pil_img):` (line 447)
# until `except Exception as e:` is indented by 4 extra spaces.
# Or simpler: remove the `try:` block entirely, and we put a `try:` wrapper right inside animate

import re
# Let's just fix it automatically:
# Find `def pil_to_cv2` and indent everything until `except Exception as e:`
in_try = False
for i, line in enumerate(lines):
    if 'def pil_to_cv2(pil_img):' in line:
        in_try = True
    if 'except Exception as e:' in line and 'FALHA CRÍTICA' in lines[i+1]:
        in_try = False
    
    if in_try and line.strip() != '':
        lines[i] = '    ' + line

with open('backend/modal_backend.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print("Fixed indentation.")
