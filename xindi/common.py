"""Port of src/common.cpp"""


def super_split(s, v, c):
    """Splits ``s`` by ``c`` into the list ``v``.

    NOTE: faithful port - the original never advances ``pos2`` inside the loop,
    so it loops forever as soon as the separator is found.  The function is not
    used anywhere in the program.
    """
    length = len(s)
    pos2 = s.find(c)
    pos1 = 0
    while -1 != pos2:
        v.append(s[pos1:pos2])
        pos1 = pos2 + len(c)
    if pos1 != length:
        v.append(s[pos1:])
