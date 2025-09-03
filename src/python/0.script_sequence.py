# run python script sequence

import subprocess

script_path = '/Users/hal9004/Library/Mobile Documents/com~apple~CloudDocs/research/Code/scraping/cityplanning'

# 1. Build sample from original export

subprocess.run(['python3', f'{script_path}/1.build_key.py'])

# 2. Build cluster file from original export

subprocess.run(['python3', f'{script_path}/2.build_clusters.py'])

# 3. Calculate distance metrics

subprocess.run(['python3', f'{script_path}/3.1.distance_measures.py']) # euclid, cosine, manhattan
subprocess.run(['python3', f'{script_path}/3.2.distance_measures.py']) # mahalonobis
#subprocess.run(['python3', f'{script_path}/3.3.distance_measures.py']) # mahalonobis cluster stability
subprocess.run(['python3', f'{script_path}/3.4.build_distances.py']) # consolidate
subprocess.run(['python3', f'{script_path}/3.5.normalize_distances.py']) # normalize

# 4. Add suffixes

subprocess.run(['python3', f'{script_path}/4.suffix_mapping.py']) 




