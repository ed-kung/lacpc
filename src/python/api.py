import os
import numpy as np
import pandas as pd
import yaml
import time

from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI

with open('../../config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    
PINECONE_API_KEY = config['PINECONE_API_KEY']
OPENAI_API_KEY = config['OPENAI_API_KEY']

EMBEDDING_MODEL = config['EMBEDDING_MODEL']
EMBEDDING_DIMENSION = config['EMBEDDING_DIMENSION']
BATCH_SIZE = config['BATCH_SIZE']

PINECONE_INDEX_NAME = config['PINECONE_INDEX_NAME']
PINECONE_CLOUD = config['PINECONE_CLOUD']
PINECONE_REGION = config['PINECONE_REGION']

pc = Pinecone(api_key=PINECONE_API_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)


"""
Get embeddings using OpenAI Embeddings API
Input is a list of texts
Output is a list of lists of floats
"""
def get_embeddings(texts):
    client_response = client.embeddings.create(input=texts, model=EMBEDDING_MODEL)
    embeddings = [r.embedding for r in client_response.data]
    return embeddings
    

"""
Get embeddings and upsert vectors into Pinecone
Input is a dataframe
Dataframe must have columns ['id','text','item_type']
"""
def embed_and_upsert(dataframe, namespace, verbose=True):
    
    assert 'id' in dataframe.columns, "dataframe must contain column 'id'"
    assert 'text' in dataframe.columns, "dataframe must contain column 'text'"
    
    # Create index if not exist
    if not pc.has_index(PINECONE_INDEX_NAME):
        pc.create_index(
            name = PINECONE_INDEX_NAME, 
            dimension = EMBEDDING_DIMENSION, 
            metric='cosine',
            spec=ServerlessSpec(
                cloud = PINECONE_CLOUD,
                region = PINECONE_REGION
            )
        )
        
    # Wait for the index to be ready
    while not pc.describe_index(PINECONE_INDEX_NAME).status['ready']:
        time.sleep(1)
    
    # Create embeddings and upsert vectors
    pc_index = pc.Index(PINECONE_INDEX_NAME)

    embeddings = []
    for i in range(0, len(dataframe), BATCH_SIZE):
        if verbose:
            print(f"{i}... ", end='')
        
        subdf = dataframe[i:i+BATCH_SIZE].reset_index(drop=True)
        texts = list(subdf['text'])
        embeddings = get_embeddings(texts)

        vectors_to_upsert = []
        for idx, row in subdf.iterrows():
            vectors_to_upsert.append({
                'id': row['id'], 
                'values': embeddings[idx],
                'metadata': dict(row)
            })

        pc_index.upsert(vectors=vectors_to_upsert, namespace=namespace)
    
    # Wait for the index to be ready
    while not pc.describe_index(PINECONE_INDEX_NAME).status['ready']:
        time.sleep(1)
    
    if verbose:
        print(pc_index.describe_index_stats())


"""
Return relevant passages
"""
def get_relevant_items(query, namespace, item_type, top_k=5):
    pc_index = pc.Index(PINECONE_INDEX_NAME)
        
    embedding = get_embeddings([query])[0]
    
    results = pc_index.query(
        namespace = namespace,
        vector = embedding,
        top_k = top_k, 
        filter = {'item_type': item_type},
        include_values = False,
        include_metadata = True
    )
    return results


