# MODE: SCRIPT\n\nimport os

def check(path):
    return os.path.exists(path)

p1 = r'C:\Users\ambas\.ollama\blobs\sha256-bbd75c7dc4292c6106265222c6eeddaaeaec9ea5a54babb6a81bce4799fcaffd-partial'
p2 = r'C:\Users\ambas\.ollama\blobs\sha256-f5074b1221da0f5a2910d33b642efa5b9eb58cfdddca1c79e16d7ad28aa2b31f-partial'

print('mistral7b-instruct:', check(p1), p1)
print('mistral7b-normal:', check(p2), p2)

# If present, print file size and mod time
for label, p in [('mistral7b-instruct', p1), ('mistral7b-normal', p2)]:
    if check(p):
        st = os.stat(p)
        print(f"{label} -> size={st.st_size} bytes, mtime={st.st_mtime}")
