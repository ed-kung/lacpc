import hashlib

"""
Hash of a string
"""
def get_hash(text):
    return hashlib.md5(text.encode()).hexdigest()
