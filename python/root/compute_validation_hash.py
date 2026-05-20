import hashlib
p='validation_hashes.json'
with open(p,'rb') as f:
    data=f.read()
print(hashlib.sha256(data).hexdigest())