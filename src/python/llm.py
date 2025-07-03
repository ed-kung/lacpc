import os
import sys
import yaml
import time
import requests
import json
import pickle
import numpy as np
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI

with open('../../config.local.yaml', 'r') as f:
    local_config = yaml.safe_load(f)

LOCAL_PATH = local_config['LOCAL_PATH']
RESPONSE_STORE = os.path.join(LOCAL_PATH, 'response_store/response_store.pkl')
PINECONE_API_KEY = local_config['PINECONE_API_KEY']
OPENAI_API_KEY = local_config['OPENAI_API_KEY']

sys.path.append(os.path.join(LOCAL_PATH, "src/python"))
from utils import get_hash

with open('../../config.yaml', 'r') as f:
    config = yaml.safe_load(f)

CHAT_MODEL = config['CHAT_MODEL']
EMBEDDING_MODEL = config['EMBEDDING_MODEL']
EMBEDDING_DIMENSION = config['EMBEDDING_DIMENSION']
BATCH_SIZE = config['BATCH_SIZE']
PINECONE_CLOUD = config['PINECONE_CLOUD']
PINECONE_REGION = config['PINECONE_REGION']

pc = Pinecone(api_key=PINECONE_API_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

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
    total_logprob = sum(tok.logprob for tok in completion.choices[0].logprobs.content)
    n_tokens = len(completion.choices[0].logprobs.content)
    perplexity = np.exp(-total_logprob/n_tokens)
    return {
        'message': message,
        'total_logprob': total_logprob,
        'n_tokens': n_tokens,
        'perplexity': perplexity
    }

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
        response = response_store.get(my_hash)
        return response

    response = get_gpt_completion(prompt)
    response_store[my_hash] = response

    with open(RESPONSE_STORE, 'wb') as f:
        pickle.dump(response_store, f)

    return response
