import os
import numpy as np
import pandas as pd
import yaml
from openai import OpenAI

with open('../../config.yaml', 'r') as f:
    config = yaml.safe_load(f)

client = OpenAI(api_key=config['OPENAI_API_KEY'])

def get_embedding(text, model="text-embedding-3-small"):
    text = text.replace("\n", " ")
    return np.array(client.embeddings.create(input = [text], model=model).data[0].embedding)

