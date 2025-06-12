import hashlib
import re

# Get the hash of a string
def get_hash(text):
    return hashlib.md5(text.encode()).hexdigest()

# Check if a string is a valid planning department case number
def is_casenum(s):
    pattern = r'^[A-Za-z]{2,3}-\d+-[A-Za-z0-9-]+$'
    return bool(re.match(pattern, s))


