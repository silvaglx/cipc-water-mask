import os
import glob
from cbers4asat.tools import rgbn_composite
import rasterio as rio
from rasterio.plot import show
import matplotlib.pyplot as plt

base_dir = 'C:/Users/xavie/cipc-data/raw'
out_dir = 'C:/Users/xavie/cipc-data/stack'
os.makedirs(out_dir, exist_ok=True)

band_mapping = {
    'AMAZONIA-1': {'red': 'BAND3', 'green': 'BAND2', 'blue': 'BAND1', 'nir': 'BAND4'},
    'CBERS-4A': {'red': 'BAND15', 'green': 'BAND14', 'blue': 'BAND13', 'nir': 'BAND16'},
    'CBERS-4': {'red': 'BAND15', 'green': 'BAND14', 'blue': 'BAND13', 'nir': 'BAND16'}
}

processed_files = []
scene_dirs = glob.glob(os.path.join(base_dir, '*'))

sats_found = []

for scene_dir in scene_dirs:
    if not os.path.isdir(scene_dir):
        continue
        
    if 'AMAZONIA1' in scene_dir:
        sat_name = 'AMAZONIA-1'
    elif 'CBERS4A' in scene_dir:
        sat_name = 'CBERS-4A'
    elif 'CBERS4_' in scene_dir:
        sat_name = 'CBERS-4'
    else:
        continue
        
    if sat_name in sats_found:
        continue  
        
    mapping = band_mapping[sat_name]
    tifs = glob.glob(os.path.join(scene_dir, '*.tif'))
    
    bands_paths = {}
    for color, band_suffix in mapping.items():
        for t in tifs:
            if t.endswith(f"{band_suffix}.tif"):
                bands_paths[color] = t
                break
                
    if len(bands_paths) == 4:
        out_filename = f"{sat_name}_TRUE_COLOR.tif"
        print(f"Gerando composição para {sat_name}...")
        
        bands_paths = {k: v.replace('\\', '/') for k, v in bands_paths.items()}
        
        rgbn_composite(red=bands_paths['red'],
                       green=bands_paths['green'],
                       blue=bands_paths['blue'],
                       nir=bands_paths['nir'],
                       filename=out_filename,
                       outdir=out_dir)
        
        processed_files.append((sat_name, os.path.join(out_dir, out_filename)))
        sats_found.append(sat_name)

print("Process finished successfully.")
