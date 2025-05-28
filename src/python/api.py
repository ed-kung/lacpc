import os
import numpy as np
import pandas as pd
import yaml
import time
import requests
import json
import hashlib
import pickle

rng = np.random.default_rng(1234)

from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI

with open('../../secrets.yaml', 'r') as f:
    secrets = yaml.safe_load(f)

PINECONE_API_KEY = secrets['PINECONE_API_KEY']
OPENAI_API_KEY = secrets['OPENAI_API_KEY']

with open('../../config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    
CHAT_MODEL = config['CHAT_MODEL']
EMBEDDING_MODEL = config['EMBEDDING_MODEL']
EMBEDDING_DIMENSION = config['EMBEDDING_DIMENSION']
BATCH_SIZE = config['BATCH_SIZE']

PINECONE_CLOUD = config['PINECONE_CLOUD']
PINECONE_REGION = config['PINECONE_REGION']

GEOCODE_URL = config['GEOCODE_URL']
GEOCODE_BENCHMARK = config['GEOCODE_BENCHMARK']
GEOCODE_VINTAGE = config['GEOCODE_VINTAGE']

pc = Pinecone(api_key=PINECONE_API_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

RESPONSE_STORE = "../../response_store/response_store.pkl"
URL_RESPONSE_STORE = "../../response_store/url_response_store.pkl"

"""
Hash of a string
"""
def get_hash(text):
    return hashlib.md5(text.encode()).hexdigest()


"""
Get embeddings
(First check pinecone, then OpenAI)
Input is list of texts
Output is list of floats
"""
def get_embeddings(texts, namespace, verbose=True):
    pc_index = pc.Index(EMBEDDING_MODEL)
    embeddings = []
    n_pinecone = 0
    n_openai = 0
    read_units = 0
    for i in range(0, len(texts), BATCH_SIZE):
        my_texts = texts[i:i+BATCH_SIZE]
        my_text_hashes = []
        for text in my_texts:
            my_text_hashes.append(get_hash(text))
        pc_results = pc_index.fetch(my_text_hashes, namespace=namespace)
        read_units += pc_results.usage.read_units
        for j in range(len(my_texts)):
            my_text = my_texts[j]
            my_text_hash = my_text_hashes[j]
            if pc_results.vectors.get(my_text_hash) is not None:
                embeddings.append(pc_results.vectors.get(my_text_hash).values)
                n_pinecone+=1
            else:
                client_response = client.embeddings.create(input=[my_text], model=EMBEDDING_MODEL)
                client_embeddings = [r.embedding for r in client_response.data]
                embeddings.append(client_embeddings[0])
                n_openai+=1
    if verbose:
        print(f"Records retrieved from Pinecone: {n_pinecone}")
        print(f"Records processed by OpenAI: {n_openai}")
        print(f"Pinecone Read Units: {read_units}")

    return embeddings


"""
Get embeddings using OpenAI Embeddings API
Input is a list of texts
Output is a list of lists of floats
"""
def get_embeddings_openai(texts):
    client_response = client.embeddings.create(input=texts, model=EMBEDDING_MODEL)
    embeddings = [r.embedding for r in client_response.data]
    return embeddings

"""
Get embeddings from OpenAI and upsert vectors into Pinecone
Input is a dataframe
Dataframe must have columns [text','item_type']
"""
def embed_and_upsert(dataframe, namespace, verbose=True):
    
    assert 'text' in dataframe.columns, "dataframe must contain column 'text'"
    
    # Create index if not exist
    if not pc.has_index(EMBEDDING_MODEL):
        pc.create_index(
            name = EMBEDDING_MODEL, 
            dimension = EMBEDDING_DIMENSION, 
            metric='cosine',
            spec=ServerlessSpec(
                cloud = PINECONE_CLOUD,
                region = PINECONE_REGION
            )
        )
        
    # Wait for the index to be ready
    while not pc.describe_index(EMBEDDING_MODEL).status['ready']:
        time.sleep(1)
    
    # Create embeddings and upsert vectors
    pc_index = pc.Index(EMBEDDING_MODEL)

    embeddings = []
    for i in range(0, len(dataframe), BATCH_SIZE):
        if verbose:
            print(f"{i}... ", end='')
        
        subdf = dataframe[i:i+BATCH_SIZE].reset_index(drop=True)
        texts = list(subdf['text'])
        embeddings = get_embeddings_openai(texts)

        vectors_to_upsert = []
        for idx, row in subdf.iterrows():
            vectors_to_upsert.append({
                'id': get_hash(row['text']), 
                'values': embeddings[idx],
                'metadata': dict(row)
            })

        pc_index.upsert(vectors=vectors_to_upsert, namespace=namespace)
    
    # Wait for the index to be ready
    while not pc.describe_index(EMBEDDING_MODEL).status['ready']:
        time.sleep(1)
    
    if verbose:
        print(pc_index.describe_index_stats())


"""
Return relevant passages
"""
def get_relevant_items(query, namespace, item_type, top_k=5):
    pc_index = pc.Index(EMBEDDING_MODEL)
        
    embedding = get_embeddings([query], namespace=namespace)[0]
    
    results = pc_index.query(
        namespace = namespace,
        vector = embedding,
        top_k = top_k, 
        filter = {'item_type': item_type},
        include_values = False,
        include_metadata = True
    )
    return results

"""
Get a Chat-GPT completion
"""
def get_gpt_completion(prompt):
    completion = client.chat.completions.create(
        model = CHAT_MODEL, 
        messages = [
            {'role':'user', 'content':prompt}
        ],
        temperature = 0,
        logprobs = True
    )
    message = completion.choices[0].message.content
    score = completion.choices[0].logprobs.content[0].logprob
    return message, score

"""
Get a Chat-GPT response, first checking whether an answer for the 
prompt already exists.
"""
def get_response(prompt, overwrite=False):
    if os.path.exists(RESPONSE_STORE):
        with open(RESPONSE_STORE, 'rb') as f:
            response_store = pickle.load(f)
    else:
        response_store = {}
        
    my_hash = get_hash(prompt)

    if (not overwrite) and (response_store.get(my_hash)):
        message, score = response_store.get(my_hash)
        return message, score

    message, score = get_gpt_completion(prompt)
    response_store[my_hash] = message, score

    with open(RESPONSE_STORE, 'wb') as f:
        pickle.dump(response_store, f)

    return message, score
        

"""
Geocoding
"""
def geocode_address(street, zip , state):
    request_params = {
        'street': street,
        'zip': zip, 
        'state': state,
        'benchmark': GEOCODE_BENCHMARK,
        'vintage': GEOCODE_VINTAGE,
        'format': 'json'
    }
    r = requests.get(GEOCODE_URL, params=request_params)
    request_url = r.url
    response_status_code = r.status_code
    if response_status_code==200:
        response_content = json.loads(r.content)
    else:
        response_content = r.content
    return {
        'request_params': request_params,
        'request_url': request_url,
        'response_status_code': response_status_code,
        'response_content': response_content
    }

"""
Scraping
"""
def request_url(url, overwrite=False, verbose=True, wait_time=60):
    if os.path.exists(URL_RESPONSE_STORE):
        with open(URL_RESPONSE_STORE, 'rb') as f:
            url_response_store = pickle.load(f)
    else:
        url_response_store = {}

    if (not overwrite) and (url_response_store.get(url)):
        response = url_response_store.get(url)
        return response

    if verbose:
        print(f"Requesting {url}...")
    r = requests.get(url)
    time.sleep(rng.uniform(wait_time, wait_time+5))
    if r.status_code!=200:
        if verbose:
            print('')
            print("****")
            print(f"Error: Invalid response from {url}")
            print(r.text)
            print("****")
            print('')
        raise

    url_response_store[url] = r.text
    with open(URL_RESPONSE_STORE, 'wb') as f:
        pickle.dump(url_response_store, f)

    return r.text


def get_id_from_caseno(caseno, overwrite=False, verbose=True):
    # get PDIS internal caseid from planning dept case number
    url = f"https://planning.lacity.org/pdiscaseinfo/api/Service/SearchCaseNumber?caseNo={caseno}"
    response = request_url(url, overwrite, verbose)
    
    if response is None:
        return None

    ok = True
    j = json.loads(response)
    if len(j)==0:
        ok = False
    elif j[0]['encodedCaseId']=='MA0':
        ok = False
    if ok:
        caseid = j[0]['encodedCaseId']
        return caseid

    short_caseno = '-'.join(caseno.split('-')[0:3])
    if verbose:
        print(f"retrying as {short_caseno}... ")
    url = f"https://planning.lacity.org/pdiscaseinfo/api/Service/SearchCaseNumber?caseNo={short_caseno}"
    response = request_url(url, overwrite, verbose)

    if response is None:
        return None

    ok = True
    if len(j)==0:
        ok = False
    elif j[0]['encodedCaseId']=='MA0':
        ok = False
    if ok:
        caseid = j[0]['encodedCaseId']
        return caseid

    if verbose:
        print(f"Warning: failed to retrieve data for {caseno}")
    return None

def get_case_info_from_caseid(caseid, overwrite=False, verbose=True):
    # get case info from caseid
    url = f"https://planning.lacity.org/pdiscaseinfo/api/Service/GetCaseInfoDataEncoded?encodedCaseId={caseid}"
    response = request_url(url, overwrite, verbose)

    if response is None:
        return None

    j = json.loads(response)
    if j is None:
        if verbose:
            print(f"Warning: no data found for caseid {caseid}... ")
        return None
    if len(j)==0:
        if verbose:
            print(f"Warning: no data found for caseid {caseid}... ")
        return None
    if j['caseNbr']==None:
        if verbose:
            print(f"Warning: no data found for caseid {caseid}... ")
        return None

    return j

def get_case_info(caseno, overwrite=False, verbose=True):
    j = get_case_info_from_caseid(get_id_from_caseno(caseno, overwrite, verbose), overwrite, verbose)
    return j
    
