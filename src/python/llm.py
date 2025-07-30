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
EMBEDDING_STORE = os.path.join(LOCAL_PATH, 'response_store/embedding_store.pkl')
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

client = OpenAI(api_key=OPENAI_API_KEY)

"""
Get embeddings first by checking an embeddings store then by calling OpeNAI
Input is a list of texts
Output is a np array of dimension (len(texts), EMBEDDING_DIMENSION)
"""
def get_embeddings(texts, overwrite=False):
    if os.path.exists(EMBEDDING_STORE):
        with open(EMBEDDING_STORE, 'rb') as f:
            embedding_store = pickle.load(f)
    else:
        embedding_store = {}
    
    embeddings = []
    for text in texts:
        my_hash = get_hash(text)
        if (not overwrite) and (embedding_store.get(my_hash)):
            embeddings.append(embedding_store.get(my_hash))
        else:
            client_response = client.embeddings.create(input=text, model=EMBEDDING_MODEL)
            embedding = client_response.data[0].embedding
            embedding_store[my_hash] = embedding
            embeddings.append(embedding)
    with open(EMBEDDING_STORE, 'wb') as f:
        pickle.dump(embedding_store, f)
    return np.array(embeddings)

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
