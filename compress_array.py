import numpy as np
import zlib
from base64 import b64encode
import struct

# rng = np.random.default_rng(seed=0)  # random number generator
# arr = rng.integers(low=0, high=3, size=4096*3+3712, dtype='int64')


arr = np.array([0, 0, 0, 1, 0, 0,
                1, 1, 0, 0, 1, 1], dtype='float32')
                
# number of chunks
m = arr.nbytes//2**15 + 1  # equal to 4 here

compr_chunk = []
for i in range(m): # 0 1 2 3
    if i < m-1:
        chunk = zlib.compress(arr[i*4096:(i+1)*4096])
        compr_chunk.append(chunk)
        # print(f'Chunk_{i}')
    else:
        size_last_chunk = arr[i*4096::].nbytes
        chunk = zlib.compress(arr[i*4096::])
        compr_chunk.append(chunk)
        # print(f'Chunk_{i}')


head_arr = np.concatenate( ( [m, 2**15, size_last_chunk], [len(compr_chunk[i]) for i in range(len(compr_chunk))] ),dtype='int32')

# base64 encoding of the header array
b64_head_arr = b64encode(head_arr.tobytes())
# print(b64_head_arr)

# base64 encoding of the concatenation of the compressed chunks
# b64_arr = b64encode(compr_chunk0 + compr_chunk1 + compr_chunk2 + compr_chunk3)

sum = compr_chunk[0]

for i in range(1,len(compr_chunk)):
    sum = sum + compr_chunk[i]

b64_arr = b64encode(sum)

# print to XML file (or to sys.stdout, in this case)
print((b64_head_arr + b64_arr).decode('utf-8'))
