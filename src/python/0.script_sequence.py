# run python script sequence

import subprocess
import os
import yaml

# set paths

with open("../../config.local.yaml", 'r') as f:
    local_config = yaml.safe_load(f)
LOCAL_PATH = local_config['LOCAL_PATH']
STATA_PATH = local_config['STATA_PATH']
script_path1 = os.path.join(LOCAL_PATH, 'src/python') # python scrips
script_path2 = os.path.join(LOCAL_PATH, 'src/stata') # stata scripts

# 0. Reset outputs

try:
    input_path = os.path.join(LOCAL_PATH, 'intermediate_data/cpc')
    output_path = os.path.join(LOCAL_PATH, 'tables')
    os.remove(f'{input_path}/working_file.csv')
    os.remove(f'{input_path}/ologit.main_effects.mahalanobis.csv')
    os.remove(f'{input_path}/ologit.marginal_effects.mahalanobis.csv')
    os.remove(f'{output_path}/ologit_main_effects.tex')
except: pass

# 1. Build sample from original export

subprocess.run(['python3', f'{script_path1}/1.build_key.py'])

# 2. Build cluster file from original export

subprocess.run(['python3', f'{script_path1}/2.build_clusters.py'])

# 3. Calculate distance metrics

subprocess.run(['python3', f'{script_path1}/3.1.distance_measures.py']) # euclid, cosine, manhattan
subprocess.run(['python3', f'{script_path1}/3.2.distance_measures.py']) # mahalonobis
#subprocess.run(['python3', f'{script_path1}/3.3.distance_measures.py']) # mahalonobis cluster stability
subprocess.run(['python3', f'{script_path1}/3.4.build_distances.py']) # consolidate
subprocess.run(['python3', f'{script_path1}/3.5.normalize_distances.py']) # normalize

# 4. Add suffixes

subprocess.run(['python3', f'{script_path1}/4.suffix_mapping.py']) 

# 5. Run stata

try: subprocess.run([STATA_PATH, "-q", "do", f'{script_path2}/mahalanobis2.do'], timeout=15, check=True)
except: pass # kill stata

# 6. Clean tables

subprocess.run(['python3', f'{script_path1}/5.1.table_clean.py']) # arrange main fx for Latex



