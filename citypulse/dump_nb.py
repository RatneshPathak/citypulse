import json

with open('src/CityPulse_AQI_Cleaning_EDA.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

with open('notebook_dump.txt', 'w', encoding='utf-8') as out_f:
    for i, cell in enumerate(nb['cells']):
        out_f.write(f"\n{'='*35} CELL {i} ({cell['cell_type']}) {'='*35}\n")
        out_f.write("--- SOURCE ---\n")
        out_f.write(''.join(cell['source']) + "\n")
        out_f.write("--- OUTPUTS ---\n")
        for out in cell.get('outputs', []):
            if 'text' in out:
                out_f.write(''.join(out['text']) + "\n")
            elif 'data' in out:
                for mime, val in out['data'].items():
                    if mime == 'text/plain':
                        out_f.write(str(val) + "\n")
                    elif mime.startswith('image/'):
                        out_f.write(f"[{mime} image data]\n")
            elif 'ename' in out:
                out_f.write(f"ERROR: {out.get('ename')}: {out.get('evalue')}\n")

print("Dumped", len(nb['cells']), "cells to notebook_dump.txt")
