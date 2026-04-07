import json
import os

files = ['cbers4asat-download-test.ipynb', 'cbers4asat-rgbn-composite-test.ipynb']

for p in files:
    with open(p, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            cell['source'] = [s.replace('C:/Users/xavie/cipc-data', 'C:/Users/xavie/cipc-data/raw') for s in cell['source']]
            cell['source'] = [s.replace('./STACK', 'C:/Users/xavie/cipc-data/stack') for s in cell['source']]
    
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

print("Notebooks updated perfectly!")
