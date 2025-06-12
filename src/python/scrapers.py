import os
import sys
import yaml
import time
import requests
import pickle

with open('../../config.local.yaml', 'r') as f:
    local_config = yaml.safe_load(f)

LOCAL_PATH = local_config['LOCAL_PATH']
URL_RESPONSE_STORE = os.path.join(LOCAL_PATH, 'response_store/url_response_store.pkl')

sys.path.append(os.path.join(LOCAL_PATH, "src/python"))

from utils import get_hash, canonicalize_casenum

def request_url_text(url, overwrite=False, verbose=True, wait=0):
    if os.path.exists(URL_RESPONSE_STORE):
        with open(URL_RESPONSE_STORE, 'rb') as f:
            url_response_store = pickle.load(f)
    else:
        url_response_store = {}

    if (not overwrite) and (url in url_response_store):
        response = url_response_store.get(url)
        return response

    if verbose:
        print(f"Requesting {url}...")
    
    r = requests.get(url)
    if r.status_code!=200:
        if verbose:
            print(f"Error: Invalid response from {url}")
            print(r.text)
        raise
    time.sleep(wait)
        
    url_response_store[url] = r.text
    with open(URL_RESPONSE_STORE, 'wb') as f:
        pickle.dump(url_response_store, f)

    return r.text

def save_url_file(url, saveas, overwrite=False, verbose=True, wait=0):
    if (not overwrite) and os.path.exists(saveas):
        if verbose:
            print(f"File exists at {saveas}")
        return

    if verbose:
        print(f"Requesting {url}...")

    r = requests.get(url)
    if r.status_code!=200:
        if verbose:
            print(f"Error: Invalid response from {url}")
            print(r.text)
        raise
    time.sleep(wait)

    os.makedirs(os.path.dirname(saveas), exist_ok=True)
    with open(saveas, 'wb') as f:
        f.write(r.content)
    if verbose:
        print(f"Saved to {saveas}")
    return



