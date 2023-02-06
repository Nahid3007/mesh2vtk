import numpy as np
import zlib
from base64 import b64encode
# making a random int64 array here for the example
rng = np.random.default_rng(seed=0)  # random number generator
arr = rng.integers(low=0, high=3, size=4096*3+3712, dtype='int64')
# this array was chosen to have 16000 elements, equal to 3 chunks of
# 4096 elements plus one chunk of 3712. This can be plotted in a vti
# array of extent 32, 25 and 20

# number of chunks
m = arr.nbytes//2**15 + 1  # equal to 4 here
# compressed chunk 0
compr_chunk0 = zlib.compress(arr[0:4096])
# compressed chunk 1
compr_chunk1 = zlib.compress(arr[4096:2*4096])
# compressed chunk 2
compr_chunk2 = zlib.compress(arr[2*4096:3*4096])
# compressed chunk 3
size_last_chunk = arr[3*4096::].nbytes
compr_chunk3 = zlib.compress(arr[3*4096::])

# header array, assuming uint32 headers in the XML file
head_arr = np.array([m, 2**15, size_last_chunk,
                     len(compr_chunk0), len(compr_chunk1),
                     len(compr_chunk2), len(compr_chunk3)], dtype='int32')

# print(head_arr)

# base64 encoding of the header array
b64_head_arr = b64encode(head_arr.tobytes())
print(b64_head_arr)
# base64 encoding of the concatenation of the compressed chunks
b64_arr = b64encode(compr_chunk0 + compr_chunk1 + compr_chunk2 + compr_chunk3)

# print to XML file (or to sys.stdout, in this case)
print((b64_head_arr + b64_arr).decode('utf-8'))