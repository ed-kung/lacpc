# This file contains functions for interacting with OpenAI and Anthropic APIs

import os
import sys
import yaml
import duckdb
import json
import numpy as np
import pandas as pd
from openai import OpenAI
import anthropic
from datetime import datetime
import hashlib
import tiktoken

with open("../../config.local.yaml", "r") as f:
    local_config = yaml.safe_load(f)
with open("../../config.yaml", "r") as f:
    config = yaml.safe_load(f)

LOCAL_PATH = local_config['LOCAL_PATH']
DATA_PATH = local_config['DATA_PATH']
OPENAI_API_KEY = local_config['OPENAI_API_KEY']
CLAUDE_API_KEY = local_config['CLAUDE_API_KEY']
EMBEDDING_DIMENSION = config['EMBEDDING_DIMENSION']

openai_client = OpenAI(api_key=OPENAI_API_KEY)
claude_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

def get_hash(text):
    digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
    return digest

def count_tokens(text, model):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    return len(tokens)

def chunk_text(text, model, max_tokens):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    if not tokens:
        return [text]
    chunks = []
    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i+max_tokens]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)
    return chunks

# --- Helper functions for interacting with batch jobs

def get_batch_jobs_db_conn(db_path):
    conn = duckdb.connect(db_path)
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            type TEXT,
            input_file TEXT,
            output_file TEXT,
            status TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        );
        """
    )
    return conn

def get_batch_jobs_df(db_conn):
    return db_conn.execute("SELECT * FROM jobs").df()

def get_batch_job(id, db_conn):
    result = db_conn.execute(
        "SELECT * FROM jobs WHERE id = ?",
        (id,)
    ).fetchone()
    return result if result else None

def delete_batch_job(id, db_conn):
    db_conn.execute(
        "DELETE FROM jobs WHERE id = ?",
        (id,)
    )
    db_conn.commit()

def store_batch_job(id, type, input_file, db_conn):
    timestamp = datetime.now()
    db_conn.execute(
        "INSERT INTO jobs (id, type, input_file, status, created_at, updated_at) VALUES (?, ?, ?, 'created', ?, ?)",
        (id, type, input_file, timestamp, timestamp)
    )
    db_conn.commit()

def update_batch_job(id, status, output_file=None, db_conn=None):
    timestamp = datetime.now()
    if output_file:
        db_conn.execute(
            "UPDATE jobs SET status = ?, output_file = ?, updated_at = ? WHERE id = ?",
            (status, output_file, timestamp, id)
        )
    else:
        db_conn.execute(
            "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?",
            (status, timestamp, id)
        )
    db_conn.commit()

def check_batch_status(id, rel_path, db_conn):
    if id.startswith("msgbatch"):
        provider = "claude"
    elif id.startswith("batch"):
        provider = "openai"
        
    if provider == "openai":
        batch = openai_client.batches.retrieve(id)
        db_batch_result = get_batch_job(id, db_conn)
        if not db_batch_result:
            print(f"Batch job with id {id} not found in database")
            return None
        if batch:
            if batch.status == "completed" or batch.status == "expired":
                output_filename = f"{id}_output.jsonl"
                output_filepath = os.path.join(DATA_PATH, rel_path, output_filename)
                output_file_id = batch.output_file_id
                if output_file_id:
                    output_file_content = openai_client.files.content(output_file_id)
                    with open(output_filepath, "w") as f:
                        f.write(output_file_content.text)
                update_batch_job(id, 'completed', output_file=output_filename, db_conn=db_conn)
                return batch
            else:
                update_batch_job(id, batch.status, db_conn=db_conn)
                return batch
        print(f"Batch job with id {id} not found in OpenAI API")
        return None
    elif provider == "claude":
        batch = claude_client.messages.batches.retrieve(id)
        db_batch_result = get_batch_job(id, db_conn)
        if not db_batch_result:
            print(f"Batch job with id {id} not found in database")
            return None
        if batch:
            if batch.processing_status == "ended":
                output_filename = f"{id}_output.jsonl"
                output_filepath = os.path.join(DATA_PATH, rel_path, output_filename)
                if batch.results_url:
                    results = claude_client.messages.batches.results(id)
                    with open(output_filepath, "w") as f:
                        for result in results:
                            f.write(json.dumps(result.model_dump()) + "\n")
                update_batch_job(id, 'completed', output_file=output_filename, db_conn=db_conn)
                batch.status = "completed"
                return batch
            else:
                # Map Claude statuses to a normalized form for the DB
                status_map = {
                    "in_progress": "in_progress",
                    "canceling": "canceling",
                }
                db_status = status_map.get(batch.processing_status, batch.processing_status)
                update_batch_job(id, db_status, db_conn=db_conn)
                batch.status = db_status
                return batch
        print(f"Batch job with id {id} not found in Claude API")
        return None


def write_batch_to_response_store(batch_id, rel_path, batch_db_conn, response_db_conn, overwrite=False):
    if batch_id.startswith("msgbatch"):
        provider = "claude"
    elif batch_id.startswith("batch"):
        provider = "openai"

    batch_result = get_batch_job(batch_id, batch_db_conn)
    if not batch_result:
        print(f"Batch job with id {batch_id} not found in database")
        return None
    if batch_result[1] != "chat":
        print(f"Batch job with id {batch_id} is not a chat batch job")
        return None
    if provider == "openai":
        return _write_openai_batch(batch_id, batch_result, rel_path, response_db_conn, overwrite)
    elif provider == "claude":
        return _write_claude_batch(batch_id, batch_result, response_db_conn, overwrite)

def _write_openai_batch(batch_id, batch_result, rel_path, response_db_conn, overwrite):
    output_file = batch_result[3]
    if not output_file:
        print(f"Batch job with id {batch_id} does not have an output file yet")
        return None
    output_filepath = os.path.join(DATA_PATH, rel_path, output_file)
    if not os.path.exists(output_filepath):
        print(f"Output file {output_filepath} not found for batch job with id {batch_id}")
        return None
    n_requests = 0
    n_written = 0
    n_error = 0
    n_existing = 0
    with open(output_filepath, "r", encoding="utf-8") as f:
        for line in f:
            n_requests += 1
            j = json.loads(line)
            if (not j['error']) and ('choices' in j['response']['body']):
                prompt_hash = j['custom_id']
                if not overwrite:
                    cached_response = check_response_cache(prompt_hash, response_db_conn)
                    if cached_response:
                        n_existing += 1
                        continue
                response = j['response']
                message = response['body']['choices'][0]['message']['content']
                total_logprob = sum([tok['logprob'] for tok in response['body']['choices'][0]['logprobs']['content']])
                n_tokens = len(response['body']['choices'][0]['logprobs']['content'])
                perplexity = np.exp(-total_logprob / n_tokens)
                store_response(
                    prompt_hash = prompt_hash,
                    response = message,
                    total_logprob = total_logprob,
                    perplexity = perplexity,
                    db_conn = response_db_conn
                )
                n_written += 1
            else:
                n_error += 1
    print(f"Chat batch job {batch_id} - Total requests: {n_requests}, Written: {n_written}, Existing: {n_existing}, Errors: {n_error}")
    return n_error

def _write_claude_batch(batch_id, batch_result, response_db_conn, overwrite):

    # Check batch status via the API
    message_batch = claude_client.messages.batches.retrieve(batch_id)
    if message_batch.processing_status != "ended":
        print(f"Claude batch {batch_id} is not finished yet (status: {message_batch.processing_status})")
        return None

    n_requests = 0
    n_written = 0
    n_error = 0
    n_existing = 0

    for entry in claude_client.messages.batches.results(batch_id):
        n_requests += 1

        if entry.result.type == "succeeded":
            prompt_hash = entry.custom_id
            if not overwrite:
                cached_response = check_response_cache(prompt_hash, response_db_conn)
                if cached_response:
                    n_existing += 1
                    continue

            # Extract the text content from the response
            message = entry.result.message.content[0].text

            # Claude does not return logprobs, so store as None
            store_response(
                prompt_hash = prompt_hash,
                response = message,
                total_logprob = 0.0,
                perplexity = 0.0,
                db_conn = response_db_conn
            )
            n_written += 1
        else:
            # Covers "errored", "canceled", and "expired"
            n_error += 1

    print(f"Chat batch job {batch_id} - Total requests: {n_requests}, Written: {n_written}, Existing: {n_existing}, Errors: {n_error}")
    return n_error


def write_batch_to_embedding_store(batch_id, rel_path, batch_db_conn, embedding_db_conn, overwrite=False):
    batch_result = get_batch_job(batch_id, batch_db_conn)
    if not batch_result:
        print(f"Batch job with id {batch_id} not found in database")
        return None
    if batch_result[1] != "embedding":
        print(f"Batch job with id {batch_id} is not an embedding job")
        return None
    output_file = batch_result[3]
    if not output_file:
        print(f"Batch job with id {batch_id} does not have an output file yet")
        return None
    output_filepath = os.path.join(DATA_PATH, rel_path, output_file)
    if not os.path.exists(output_filepath):
        print(f"Output file {output_filepath} not found for batch job with id {batch_id}")
        return None
    n_requests = 0
    n_written = 0
    n_error = 0
    n_existing = 0
    with open(output_filepath, "r", encoding="utf-8") as f:
        for line in f:
            n_requests += 1
            j = json.loads(line)
            if (not j['error']):
                prompt_hash = j['custom_id']
                if not overwrite:
                    cached_embedding = check_embedding_cache(prompt_hash, embedding_db_conn)
                    if cached_embedding:
                        n_existing += 1
                        continue
                embedding = j['response']['body']['data'][0]['embedding']
                store_embedding(
                    prompt_hash = prompt_hash,
                    embedding = embedding,
                    db_conn = embedding_db_conn
                )
                n_written += 1
            else:
                n_error += 1
    print(f"Embeddings batch job {batch_id} - Total requests: {n_requests}, Written: {n_written}, Existing: {n_existing}, Errors: {n_error}")
    return n_error

def create_chat_batch_job(prompts, rel_path, input_filename, model, batch_db_conn, response_db_conn, overwrite=False, provider='openai', max_output_tokens=4096):
    input_filepath = os.path.join(DATA_PATH, rel_path, input_filename)
    if os.path.exists(input_filepath):
        print(f"Batch input file {input_filepath} already exists.")
        return None
    
    prompt_hashes = []
    prompts_to_submit = []
    for prompt in prompts:
        prompt_hash = get_hash(prompt)
        if not overwrite:
            cached_response = check_response_cache(prompt_hash, response_db_conn)
            if cached_response:
                continue
        if prompt_hash in prompt_hashes:
            continue
        prompt_hashes.append(prompt_hash)
        prompts_to_submit.append(prompt)
    
    if not prompts_to_submit:
        print(f"No new prompts to process.")
        return None
    
    if provider=='openai':
        with open(input_filepath, 'w', encoding='utf-8') as f:
            for prompt_hash, prompt in zip(prompt_hashes, prompts_to_submit):
                task = {
                    'custom_id': prompt_hash,
                    'method': 'POST',
                    'url': '/v1/chat/completions',
                    'body': {
                        'model': model,
                        'temperature': 0.0,
                        'logprobs': True,
                        'messages': [{'role': 'user', 'content': prompt}]
                    }
                }
                f.write(json.dumps(task) + '\n')
        print(f"Batch input file created: {input_filepath} with {len(prompts_to_submit)} requests.")

        file_upload = openai_client.files.create(
            file = open(input_filepath, 'rb'),
            purpose = 'batch'
        )
        input_file_id = file_upload.id
        batch = openai_client.batches.create(
            input_file_id = input_file_id,
            endpoint = '/v1/chat/completions',
            completion_window = '24h'
        )
        batch_id = batch.id
        print(f"Batch job created with id {batch_id}")
        store_batch_job(batch_id, 'chat', input_filename, batch_db_conn)
    elif provider=='claude':
        requests = []
        for prompt_hash, prompt in zip(prompt_hashes, prompts_to_submit):
            requests.append({
                "custom_id": prompt_hash,
                "params": {
                    "model": model,
                    "max_tokens": max_output_tokens,
                    "temperature": 0.0,
                    "messages": [{"role": "user", "content": prompt}]
                }
            })
        batch = claude_client.messages.batches.create(requests=requests)
        batch_id = batch.id
        print(f"Batch job created with id {batch_id}")
        store_batch_job(batch_id, 'chat', "", batch_db_conn)

    return batch

def create_embedding_batch_job(prompts, rel_path, input_filename, model, batch_db_conn, embedding_db_conn, overwrite=False):
    input_filepath = os.path.join(DATA_PATH, rel_path, input_filename)
    if os.path.exists(input_filepath):
        print(f"Batch input file {input_filepath} already exists.")
        return None
    
    prompt_hashes = []
    prompts_to_submit = []
    for prompt in prompts:
        prompt_hash = get_hash(prompt)
        if not overwrite:
            cached_embedding = check_embedding_cache(prompt_hash, embedding_db_conn)
            if cached_embedding:
                continue
        if prompt_hash in prompt_hashes:
            continue
        prompt_hashes.append(prompt_hash)
        prompts_to_submit.append(prompt)
    
    if not prompts_to_submit:
        print(f"No new prompts to process.")
        return None
    
    with open(input_filepath, 'w', encoding='utf-8') as f:
        for prompt_hash, prompt in zip(prompt_hashes, prompts_to_submit):
            task = {
                'custom_id': prompt_hash,
                'method': 'POST',
                'url': '/v1/embeddings',
                'body': {
                    'model': model,
                    'input': prompt
                }
            }
            f.write(json.dumps(task) + '\n')
    print(f"Batch input file created: {input_filepath} with {len(prompts_to_submit)} requests.")

    file_upload = openai_client.files.create(
        file = open(input_filepath, 'rb'),
        purpose = 'batch'
    )
    input_file_id = file_upload.id
    batch = openai_client.batches.create(
        input_file_id = input_file_id,
        endpoint = '/v1/embeddings',
        completion_window = '24h'
    )
    batch_id = batch.id
    print(f"Batch job created with id {batch_id}")
    store_batch_job(batch_id, 'embedding', input_filename, batch_db_conn)
    return batch


# --- Helper functions for interacting with a response and embedding store dbs

def get_embedding_store_db_conn(db_path):
    conn = duckdb.connect(db_path)
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS embeddings (
            prompt_hash VARCHAR(64) PRIMARY KEY,
            embedding FLOAT[{EMBEDDING_DIMENSION}],
            last_updated_at TIMESTAMP
        );
        """
    )
    return conn

def get_response_store_db_conn(db_path):
    conn = duckdb.connect(db_path)
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS responses (
            prompt_hash VARCHAR(64) PRIMARY KEY,
            response TEXT,
            total_logprob FLOAT,
            perplexity FLOAT,
            last_updated_at TIMESTAMP
        );
        """
    )
    return conn

def check_response_cache(prompt_hash, db_conn):
    result = db_conn.execute(
        "SELECT response, total_logprob, perplexity FROM responses WHERE prompt_hash = ?",
        (prompt_hash,)
    ).fetchone()
    return result if result else None

def check_embedding_cache(prompt_hash, db_conn):
    result = db_conn.execute(
        "SELECT embedding FROM embeddings WHERE prompt_hash = ?",
        (prompt_hash,)
    ).fetchone()
    return result if result else None

def store_response(prompt_hash, response, total_logprob, perplexity, db_conn):
    timestamp = datetime.now()
    db_conn.execute(
        "INSERT OR REPLACE INTO responses (prompt_hash, response, total_logprob, perplexity, last_updated_at) VALUES (?, ?, ?, ?, ?)",
        (prompt_hash, response, total_logprob, perplexity, timestamp)
    )
    db_conn.commit()

def store_embedding(prompt_hash, embedding, db_conn):
    timestamp = datetime.now()
    db_conn.execute(
        "INSERT OR REPLACE INTO embeddings (prompt_hash, embedding, last_updated_at) VALUES (?, ?, ?)",
        (prompt_hash, embedding, timestamp)
    )
    db_conn.commit()

# --- Helper functions for interacting with chat completions

def get_chat_completion(prompt, model, provider="openai", max_output_tokens=4096):
    if provider=="openai":
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            logprobs=True
        )
        message = response.choices[0].message.content
        total_logprob = sum(tok.logprob for tok in response.choices[0].logprobs.content)
        n_tokens = len(response.choices[0].logprobs.content)
        perplexity = np.exp(-total_logprob / n_tokens)
    elif provider=="claude":
        response = claude_client.messages.create(
            model=model,
            max_tokens=max_output_tokens,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}]
        )
        message = response.content[0].text
        total_logprob = 0.0  # Claude does not provide logprobs
        perplexity = 0.0      # Claude does not provide perplexity

    return {
        "response": message,
        "total_logprob": total_logprob,
        "perplexity": perplexity
    }

def get_response(prompt, model, db_conn, overwrite=False, provider="openai", max_output_tokens=4096):
    prompt_hash = get_hash(prompt)
    if not overwrite:
        cached_response = check_response_cache(prompt_hash, db_conn)
        if cached_response:
            return {
                "response": cached_response[0],
                "total_logprob": cached_response[1],
                "perplexity": cached_response[2]
            }
    response = get_chat_completion(prompt, model, provider=provider, max_output_tokens=max_output_tokens)
    store_response(
        prompt_hash = prompt_hash,
        response = response["response"],
        total_logprob = response["total_logprob"],
        perplexity = response["perplexity"],
        db_conn = db_conn
    )
    return response

# --- Helper functions for interacting with embeddings

def get_embedding_(prompt, model):
    response = openai_client.embeddings.create(input=prompt, model=model)
    embedding = response.data[0].embedding
    return embedding

def get_embedding(prompt, model, db_conn, overwrite=False):
    prompt_hash = get_hash(prompt)
    if not overwrite:
        cached_response = check_embedding_cache(prompt_hash, db_conn)
        if cached_response:
            return list(cached_response[0]) # stored as tuple in duckdb
    embedding = get_embedding_(prompt, model)
    store_embedding(prompt_hash, embedding, db_conn)
    return embedding


