"""Port of src/dictionary.cpp (N. Devillard's string dictionary used by iniparser).

Keys and values are byte strings (``bytes``) exactly like the C ``char *``.
The slot layout (insertion / deletion / growth) is reproduced so that the
order in which entries are dumped is identical.
"""

MAXVALSZ = 1024
DICTMINSZ = 128

DICT_INVALID_KEY = object()


class dictionary(object):
    def __init__(self):
        self.n = 0          # number of entries in dictionary
        self.size = 0       # storage size
        self.val = []       # list of string values
        self.key = []       # list of string keys
        self.hash = []      # list of hash values for keys


def dictionary_hash(key):
    """Hash function (from Dr Dobbs Journal); chars are unsigned on aarch64."""
    if key is None:
        return 0
    h = 0
    for c in key:
        h = (h + c) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= (h >> 6)
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= (h >> 11)
    h = (h + (h << 15)) & 0xFFFFFFFF
    return h


def _dictionary_grow(d):
    """Double the size of the dictionary"""
    d.val = d.val + [None] * d.size
    d.key = d.key + [None] * d.size
    d.hash = d.hash + [0] * d.size
    d.size *= 2
    return 0


def dictionary_new(size):
    """Create a new dictionary object"""
    if size < DICTMINSZ:
        size = DICTMINSZ
    d = dictionary()
    d.size = size
    d.val = [None] * size
    d.key = [None] * size
    d.hash = [0] * size
    return d


def dictionary_del(d):
    """Delete a dictionary object"""
    if d is None:
        return
    d.val = []
    d.key = []
    d.hash = []
    d.n = 0
    d.size = 0


def dictionary_get(d, key, default):
    """Get a value from a dictionary (``default`` if the key is missing)."""
    h = dictionary_hash(key)
    for i in range(d.size):
        if d.key[i] is None:
            continue
        if h == d.hash[i]:
            if key == d.key[i]:
                return d.val[i]
    return default


def dictionary_set(d, key, val):
    """Set a value in a dictionary (adds the key if needed); 0 on success."""
    if d is None or key is None:
        return -1

    h = dictionary_hash(key)
    # Find if value is already in dictionary
    if d.n > 0:
        for i in range(d.size):
            if d.key[i] is None:
                continue
            if h == d.hash[i]:
                if key == d.key[i]:
                    d.val[i] = val
                    return 0
    # Add a new value; grow if needed
    if d.n == d.size:
        if _dictionary_grow(d) != 0:
            return -1

    # Insert key in the first empty slot. Start at d->n and wrap at d->size.
    i = d.n
    while d.key[i] is not None:
        i += 1
        if i == d.size:
            i = 0
    d.key[i] = key
    d.val[i] = val
    d.hash[i] = h
    d.n += 1
    return 0


def dictionary_unset(d, key):
    """Delete a key in a dictionary"""
    if key is None or d is None:
        return

    h = dictionary_hash(key)
    i = 0
    while i < d.size:
        if d.key[i] is not None and h == d.hash[i] and key == d.key[i]:
            break
        i += 1
    if i >= d.size:
        return      # Key not found

    d.key[i] = None
    d.val[i] = None
    d.hash[i] = 0
    d.n -= 1


def dictionary_dump(d, out):
    """Dump a dictionary to a binary file object"""
    if d is None or out is None:
        return
    if d.n < 1:
        out.write(b"empty dictionary\n")
        return
    for i in range(d.size):
        if d.key[i] is not None:
            out.write(b"%20s\t[%s]\n" % (d.key[i], d.val[i] if d.val[i] is not None else b"UNDEF"))
