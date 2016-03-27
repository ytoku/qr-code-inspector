# -*- coding: utf-8 -*-
# QR code inspector
# Prototype 2.0
# 
# Reference1: http://www.thonky.com/qr-code-tutorial/
# Reference2: http://datagenetics.com/blog/november12013/index.html
#   * including error: ver < 7 don't include version information
# Sample generator: http://www.morovia.com/free-online-barcode-generator/qrcode-maker.php
# 
# TODO (on Prototype 2.1):
#  * ハンドリングしやすいエラー処理
#   * 想定外のビット列が来た程度で落ちるべきではない
#   * エラー情報配列に追加していくべき？
# TODO (on Release version):
#  * 適切にオブジェクト化
#   * 特にaffectionの部分を必要ない場合に意識しないよう

import reedsolo

class Uncertain:
    def __init__(self, value, mask, bits = 8):
        self.value = value & mask
        self.mask = mask
        self.bits = bits

    def __repr__(self):
        s = "Uncertain(" + repr(self.value) + ", " + repr(self.mask)
        if self.bits != 8:
            s += ", bits=" + repr(self.bits)
        s += ")"
        return s

def merge_uncertain(a, b, l):
    if isinstance(a, Uncertain):
        av = a.value
        am = a.mask
    else:
        av = a
        am = (1 << l) - 1
    if isinstance(b, Uncertain):
        bv = b.value
        bm = b.mask
    else:
        bv = b
        bm = (1 << l) - 1

    mismatched = (av ^ bv) & (am & bm)
    m = (am | bm) ^ mismatched
    v = av | bv
    if m == (1 << l) - 1:
        return v
    else:
        return Uncertain(v, m)


def show(qr, markers = []):
    (w, h) = (len(qr[0]), len(qr))
    scale = 16
    import Image
    import ImageDraw
    img = Image.new('RGB', (scale*(w+2), scale*(h+2)))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, scale*(w+2), scale*(h+2)), "white")
    for y in xrange(h):
        for x in xrange(w):
            if (x, y) in markers:
                if qr[y][x]:
                    color = "darkgreen"
                elif qr[y][x] == 0:
                    color = "lightgreen"
                else:
                    color = "green"
            else:
                if qr[y][x] == 1:
                    color = "black"
                elif qr[y][x] == 0:
                    color = "white"
                else:
                    color = "gray"

            draw.rectangle((scale*(x+1), scale*(y+1),
                            scale*(x+2)-1, scale*(y+2)-1),
                           color)
    img.show()

def generate_codeword_marker_table(version):
    table = []
    k = 0
    markers = []
    for (x, y) in zigzag(version):
        if not in_payload_area(version, x, y):
            continue
        k += 1
        markers.append((x, y))
        if k == 8:
            table.append(markers)
            markers = []
            k = 0
    return table

def markerpos(chunks, version):
    coodinates = set()
    table = generate_codeword_marker_table(version)
    for c in chunks:
        coodinates.update(table[c])
    return coodinates


def load(filename):
    qr = []
    with open(filename) as f:
        size = int(f.readline())
        for i in range(size):
            l = f.readline()
            qr.append([])
            for j in range(size):
                if j < len(l) and l[j] != "\n":
                    c = l[j]
                else:
                    c = " "
                if c == "*":
                    qr[i].append(1)
                elif c == " ":
                    qr[i].append(0)
                else:
                    qr[i].append(None)
    return qr

def hamming_distance(a, b, l):
    if isinstance(a, Uncertain):
        am = a.mask
        av = a.value
    else:
        am = (1 << l) - 1
        av = a
    if isinstance(b, Uncertain):
        bm = b.mask
        bv = b.value
    else:
        bm = (1 << l) - 1
        bv = b
    x = av ^ bv
    m = am & bm
    d = 0
    for i in range(l):
        if x & 1 == 1 or m & 1 == 0:
            d += 1
        x >>= 1
        m >>= 1
    return d

ECL_L = 1
ECL_M = 0
ECL_Q = 3
ECL_H = 2

# (version, ecl): (EC Codewords / Block,
#                  [(#Blocks in Group i, #Data Codewords / Group i's Block)])
correction_table = {
    (1, ECL_L): (7, [(1, 19), (0, 0)]),
    (1, ECL_M): (10, [(1, 16), (0, 0)]),
    (1, ECL_Q): (13, [(1, 13), (0, 0)]),
    (1, ECL_H): (17, [(1, 9), (0, 0)]),
    (2, ECL_L): (10, [(1, 34), (0, 0)]),
    (2, ECL_M): (16, [(1, 28), (0, 0)]),
    (2, ECL_Q): (22, [(1, 22), (0, 0)]),
    (2, ECL_H): (28, [(1, 16), (0, 0)]),
    (3, ECL_L): (15, [(1, 55), (0, 0)]),
    (3, ECL_M): (26, [(1, 44), (0, 0)]),
    (3, ECL_Q): (18, [(2, 17), (0, 0)]),
    (3, ECL_H): (22, [(2, 13), (0, 0)]),
    (4, ECL_L): (20, [(1, 80), (0, 0)]),
    (4, ECL_M): (18, [(2, 32), (0, 0)]),
    (4, ECL_Q): (26, [(2, 24), (0, 0)]),
    (4, ECL_H): (16, [(4, 9), (0, 0)]),
    (5, ECL_L): (26, [(1, 108), (0, 0)]),
    (5, ECL_M): (24, [(2, 43), (0, 0)]),
    (5, ECL_Q): (18, [(2, 15), (2, 16)]),
    (5, ECL_H): (22, [(2, 11), (2, 12)]),
    (6, ECL_L): (18, [(2, 68), (0, 0)]),
    (6, ECL_M): (16, [(4, 27), (0, 0)]),
    (6, ECL_Q): (24, [(4, 19), (0, 0)]),
    (6, ECL_H): (28, [(4, 15), (0, 0)]),
    (7, ECL_L): (20, [(2, 78), (0, 0)]),
    (7, ECL_M): (18, [(4, 31), (0, 0)]),
    (7, ECL_Q): (18, [(2, 14), (4, 15)]),
    (7, ECL_H): (26, [(4, 13), (1, 14)]),
    (8, ECL_L): (24, [(2, 97), (0, 0)]),
    (8, ECL_M): (22, [(2, 38), (2, 39)]),
    (8, ECL_Q): (22, [(4, 18), (2, 19)]),
    (8, ECL_H): (26, [(4, 14), (2, 15)]),
    (9, ECL_L): (30, [(2, 116), (0, 0)]),
    (9, ECL_M): (22, [(3, 36), (2, 37)]),
    (9, ECL_Q): (20, [(4, 16), (4, 17)]),
    (9, ECL_H): (24, [(4, 12), (4, 13)]),
    (10, ECL_L): (18, [(2, 68), (2, 69)]),
    (10, ECL_M): (26, [(4, 43), (1, 44)]),
    (10, ECL_Q): (24, [(6, 19), (2, 20)]),
    (10, ECL_H): (28, [(6, 15), (2, 16)]),
    (11, ECL_L): (20, [(4, 81), (0, 0)]),
    (11, ECL_M): (30, [(1, 50), (4, 51)]),
    (11, ECL_Q): (28, [(4, 22), (4, 23)]),
    (11, ECL_H): (24, [(3, 12), (8, 13)]),
    (12, ECL_L): (24, [(2, 92), (2, 93)]),
    (12, ECL_M): (22, [(6, 36), (2, 37)]),
    (12, ECL_Q): (26, [(4, 20), (6, 21)]),
    (12, ECL_H): (28, [(7, 14), (4, 15)]),
    (13, ECL_L): (26, [(4, 107), (0, 0)]),
    (13, ECL_M): (22, [(8, 37), (1, 38)]),
    (13, ECL_Q): (24, [(8, 20), (4, 21)]),
    (13, ECL_H): (22, [(12, 11), (4, 12)]),
    (14, ECL_L): (30, [(3, 115), (1, 116)]),
    (14, ECL_M): (24, [(4, 40), (5, 41)]),
    (14, ECL_Q): (20, [(11, 16), (5, 17)]),
    (14, ECL_H): (24, [(11, 12), (5, 13)]),
    (15, ECL_L): (22, [(5, 87), (1, 88)]),
    (15, ECL_M): (24, [(5, 41), (5, 42)]),
    (15, ECL_Q): (30, [(5, 24), (7, 25)]),
    (15, ECL_H): (24, [(11, 12), (7, 13)]),
    (16, ECL_L): (24, [(5, 98), (1, 99)]),
    (16, ECL_M): (28, [(7, 45), (3, 46)]),
    (16, ECL_Q): (24, [(15, 19), (2, 20)]),
    (16, ECL_H): (30, [(3, 15), (13, 16)]),
    (17, ECL_L): (28, [(1, 107), (5, 108)]),
    (17, ECL_M): (28, [(10, 46), (1, 47)]),
    (17, ECL_Q): (28, [(1, 22), (15, 23)]),
    (17, ECL_H): (28, [(2, 14), (17, 15)]),
    (18, ECL_L): (30, [(5, 120), (1, 121)]),
    (18, ECL_M): (26, [(9, 43), (4, 44)]),
    (18, ECL_Q): (28, [(17, 22), (1, 23)]),
    (18, ECL_H): (28, [(2, 14), (19, 15)]),
    (19, ECL_L): (28, [(3, 113), (4, 114)]),
    (19, ECL_M): (26, [(3, 44), (11, 45)]),
    (19, ECL_Q): (26, [(17, 21), (4, 22)]),
    (19, ECL_H): (26, [(9, 13), (16, 14)]),
    (20, ECL_L): (28, [(3, 107), (5, 108)]),
    (20, ECL_M): (26, [(3, 41), (13, 42)]),
    (20, ECL_Q): (30, [(15, 24), (5, 25)]),
    (20, ECL_H): (28, [(15, 15), (10, 16)]),
    (21, ECL_L): (28, [(4, 116), (4, 117)]),
    (21, ECL_M): (26, [(17, 42), (0, 0)]),
    (21, ECL_Q): (28, [(17, 22), (6, 23)]),
    (21, ECL_H): (30, [(19, 16), (6, 17)]),
    (22, ECL_L): (28, [(2, 111), (7, 112)]),
    (22, ECL_M): (28, [(17, 46), (0, 0)]),
    (22, ECL_Q): (30, [(7, 24), (16, 25)]),
    (22, ECL_H): (24, [(34, 13), (0, 0)]),
    (23, ECL_L): (30, [(4, 121), (5, 122)]),
    (23, ECL_M): (28, [(4, 47), (14, 48)]),
    (23, ECL_Q): (30, [(11, 24), (14, 25)]),
    (23, ECL_H): (30, [(16, 15), (14, 16)]),
    (24, ECL_L): (30, [(6, 117), (4, 118)]),
    (24, ECL_M): (28, [(6, 45), (14, 46)]),
    (24, ECL_Q): (30, [(11, 24), (16, 25)]),
    (24, ECL_H): (30, [(30, 16), (2, 17)]),
    (25, ECL_L): (26, [(8, 106), (4, 107)]),
    (25, ECL_M): (28, [(8, 47), (13, 48)]),
    (25, ECL_Q): (30, [(7, 24), (22, 25)]),
    (25, ECL_H): (30, [(22, 15), (13, 16)]),
    (26, ECL_L): (28, [(10, 114), (2, 115)]),
    (26, ECL_M): (28, [(19, 46), (4, 47)]),
    (26, ECL_Q): (28, [(28, 22), (6, 23)]),
    (26, ECL_H): (30, [(33, 16), (4, 17)]),
    (27, ECL_L): (30, [(8, 122), (4, 123)]),
    (27, ECL_M): (28, [(22, 45), (3, 46)]),
    (27, ECL_Q): (30, [(8, 23), (26, 24)]),
    (27, ECL_H): (30, [(12, 15), (28, 16)]),
    (28, ECL_L): (30, [(3, 117), (10, 118)]),
    (28, ECL_M): (28, [(3, 45), (23, 46)]),
    (28, ECL_Q): (30, [(4, 24), (31, 25)]),
    (28, ECL_H): (30, [(11, 15), (31, 16)]),
    (29, ECL_L): (30, [(7, 116), (7, 117)]),
    (29, ECL_M): (28, [(21, 45), (7, 46)]),
    (29, ECL_Q): (30, [(1, 23), (37, 24)]),
    (29, ECL_H): (30, [(19, 15), (26, 16)]),
    (30, ECL_L): (30, [(5, 115), (10, 116)]),
    (30, ECL_M): (28, [(19, 47), (10, 48)]),
    (30, ECL_Q): (30, [(15, 24), (25, 25)]),
    (30, ECL_H): (30, [(23, 15), (25, 16)]),
    (31, ECL_L): (30, [(13, 115), (3, 116)]),
    (31, ECL_M): (28, [(2, 46), (29, 47)]),
    (31, ECL_Q): (30, [(42, 24), (1, 25)]),
    (31, ECL_H): (30, [(23, 15), (28, 16)]),
    (32, ECL_L): (30, [(17, 115), (0, 0)]),
    (32, ECL_M): (28, [(10, 46), (23, 47)]),
    (32, ECL_Q): (30, [(10, 24), (35, 25)]),
    (32, ECL_H): (30, [(19, 15), (35, 16)]),
    (33, ECL_L): (30, [(17, 115), (1, 116)]),
    (33, ECL_M): (28, [(14, 46), (21, 47)]),
    (33, ECL_Q): (30, [(29, 24), (19, 25)]),
    (33, ECL_H): (30, [(11, 15), (46, 16)]),
    (34, ECL_L): (30, [(13, 115), (6, 116)]),
    (34, ECL_M): (28, [(14, 46), (23, 47)]),
    (34, ECL_Q): (30, [(44, 24), (7, 25)]),
    (34, ECL_H): (30, [(59, 16), (1, 17)]),
    (35, ECL_L): (30, [(12, 121), (7, 122)]),
    (35, ECL_M): (28, [(12, 47), (26, 48)]),
    (35, ECL_Q): (30, [(39, 24), (14, 25)]),
    (35, ECL_H): (30, [(22, 15), (41, 16)]),
    (36, ECL_L): (30, [(6, 121), (14, 122)]),
    (36, ECL_M): (28, [(6, 47), (34, 48)]),
    (36, ECL_Q): (30, [(46, 24), (10, 25)]),
    (36, ECL_H): (30, [(2, 15), (64, 16)]),
    (37, ECL_L): (30, [(17, 122), (4, 123)]),
    (37, ECL_M): (28, [(29, 46), (14, 47)]),
    (37, ECL_Q): (30, [(49, 24), (10, 25)]),
    (37, ECL_H): (30, [(24, 15), (46, 16)]),
    (38, ECL_L): (30, [(4, 122), (18, 123)]),
    (38, ECL_M): (28, [(13, 46), (32, 47)]),
    (38, ECL_Q): (30, [(48, 24), (14, 25)]),
    (38, ECL_H): (30, [(42, 15), (32, 16)]),
    (39, ECL_L): (30, [(20, 117), (4, 118)]),
    (39, ECL_M): (28, [(40, 47), (7, 48)]),
    (39, ECL_Q): (30, [(43, 24), (22, 25)]),
    (39, ECL_H): (30, [(10, 15), (67, 16)]),
    (40, ECL_L): (30, [(19, 118), (6, 119)]),
    (40, ECL_M): (28, [(18, 47), (31, 48)]),
    (40, ECL_Q): (30, [(34, 24), (34, 25)]),
    (40, ECL_H): (30, [(20, 15), (61, 16)]),
}

def get_version(qr):
    size = len(qr)
    return (size - 17) / 4



### Format String ###
def gen_rs_format(f):
    assert 0 <= f and f < 32
    ecc = f << 10
    for i in range(4, -1, -1):
        if ((0b10000000000 << i) & ecc) != 0:
            ecc ^= 0b10100110111 << i
    return (f << 10) | ecc

def gen_format(ecl, maskp):
    f = (ecl << 3) | maskp
    f = gen_rs_format(f)
    return f ^ 0b101010000010010

def extract_format(qr):
    # msb-to-lsb
    fl1 = []
    fl1 += qr[8][:6] + qr[8][7:9]
    fl1.append(qr[7][8])
    for i in range(6):
        fl1.append(qr[5 - i][8])

    fl2 = []
    for i in range(7):
        fl2.append(qr[len(qr) - 1 - i][8])
    fl2 += qr[8][-8:]

    f1 = 0
    fm1 = 0
    for x in fl1:
        f1 *= 2
        fm1 *= 2
        if x == 1: f1 += 1
        if x is not None: fm1 += 1
    if fm1 != (1 << 15) - 1:
        f1 = Uncertain(f1, fm1, bits=15)

    f2 = 0
    fm2 = 0
    for x in fl2:
        f2 *= 2
        fm2 *= 2
        if x == 1: f2 += 1
        if x is not None: fm2 += 1
    if fm2 != (1 << 15) - 1:
        f2 = Uncertain(f2, fm2, bits=15)

    return (f1, f2)

def match_format(ftuple):
    mergedf = merge_uncertain(ftuple[0], ftuple[1], 15)
    formats = []
    for e in range(4):
        for m in range(8):
            f = gen_format(e, m)
            d = hamming_distance(mergedf, f, 15)
            d0 = hamming_distance(ftuple[0], f, 15)
            d1 = hamming_distance(ftuple[1], f, 15)
            formats.append((d, d0, d1, (e, m)))
    formats.sort()
    return formats


### Version Information ###
## version が 7以上の時にのみ含まれる
def gen_golay_version(v):
    assert 0 <= v and v < 64
    ecc = v << 12
    for i in range(5, -1, -1):
        if ((0b1000000000000 << i) & ecc) != 0:
            ecc ^= 0b1111100100101 << i
    return (v << 12) + ecc

def gen_version(v):
    return gen_golay_version(v)

def extract_version(qr):
    # msb-to-lsb
    vl1 = []
    for x in range(6):
        for y in range(3):
            vl1.append(qr[-11+y][x])
    vl1.reverse()

    vl2 = []
    for y in range(6):
        for x in range(3):
            vl2.append(qr[y][-11+x])
    vl2.reverse()

    v1 = 0
    for x in vl1:
        v1 *= 2
        if x == 1: v1 += 1

    v2 = 0
    for x in vl2:
        v2 *= 2
        if x == 1: v2 += 1

    return (v1, v2)

def match_version(vtuple):
    mergedv = merge_uncertain(vtuple[0], vtuple[1], 18)
    versions = []
    for version in range(7, 41):
        v = gen_version(version)
        d = hamming_distance(mergedv, v, 18)
        d0 = hamming_distance(vtuple[0], v, 18)
        d1 = hamming_distance(vtuple[1], v, 18)
        versions.append((d, d0, d1, version))
    versions.sort()
    return versions

### Payload ###
alignment_pattern_locations_table = [
    None, 
    [],
    [6, 18],
    [6, 22],
    [6, 26],
    [6, 30],
    [6, 34],
    [6, 22, 38],
    [6, 24, 42],
    [6, 26, 46],
    [6, 28, 50],
    [6, 30, 54],
    [6, 32, 58],
    [6, 34, 62],
    [6, 26, 46, 66],
    [6, 26, 48, 70],
    [6, 26, 50, 74],
    [6, 30, 54, 78],
    [6, 30, 56, 82],
    [6, 30, 58, 86],
    [6, 34, 62, 90],
    [6, 28, 50, 72, 94],
    [6, 26, 50, 74, 98],
    [6, 30, 54, 78, 102],
    [6, 28, 54, 80, 106],
    [6, 32, 58, 84, 110],
    [6, 30, 58, 86, 114],
    [6, 34, 62, 90, 118],
    [6, 26, 50, 74, 98, 122],
    [6, 30, 54, 78, 102, 126],
    [6, 26, 52, 78, 104, 130],
    [6, 30, 56, 82, 108, 134],
    [6, 34, 60, 86, 112, 138],
    [6, 30, 58, 86, 114, 142],
    [6, 34, 62, 90, 118, 146],
    [6, 30, 54, 78, 102, 126, 150],
    [6, 24, 50, 76, 102, 128, 154],
    [6, 28, 54, 80, 106, 132, 158],
    [6, 32, 58, 84, 110, 136, 162],
    [6, 26, 54, 82, 110, 138, 166],
    [6, 30, 58, 86, 114, 142, 170],
]
alignment_pattern_modules = {}

def in_payload_area(version, x, y):
    if version in alignment_pattern_modules:
        excludes = alignment_pattern_modules[version]
    else:
        apl = alignment_pattern_locations_table[version]
        excludes = set()
        for ay in apl:
            for ax in apl:
                if ax == apl[0] and ay == apl[0]:
                    continue
                if ax == apl[0] and ay == apl[-1]:
                    continue
                if ax == apl[-1] and ay == apl[0]:
                    continue
                for by in [-2, -1, 0, 1, 2]:
                    for bx in [-2, -1, 0, 1, 2]:
                        excludes.add((ax + bx, ay + by))
        alignment_pattern_modules[version] = excludes

    size = version * 4 + 17
    # Timing
    if x == 6 or y == 6:
        return False
    # 左上Position + Format
    if x <= 8 and y <= 8:
        return False
    # 左下Position + Format
    if x <= 8 and size - 8 <= y:
        return False
    # 右上Position + Format
    if y <= 8 and size - 8 <= x:
        return False
    # Alignment
    if (x, y) in excludes:
        return False
    # Version Information
    if version >= 7:
        if size - 11 <= x and y <= 5:
            return False
        if size - 11 <= y and x <= 5:
            return False
    return True

def zigzag(version):
    size = version * 4 + 17
    x = y = size - 1

    while x >= 0:
        # up
        for i in range(size):
            yield (x, y)
            x -= 1
            yield (x, y)
            y -= 1; x += 1
        y = 0
        x -= 2
        # skip a timing line
        if x == 6:
            x -= 1
        # down
        for i in range(size):
            yield (x, y)
            x -= 1
            yield (x, y)
            y += 1; x += 1
        y = size - 1
        x -= 2

def mask_at(m, x, y):
    if m == 0:
        flip = (y + x) % 2 == 0
    elif m == 1:
        flip = (y) % 2 == 0
    elif m == 2:
        flip = (x) % 3 == 0
    elif m == 3:
        flip = (y + x) % 3 == 0
    elif m == 4:
        flip = (y/2 + x/3) % 2 == 0
    elif m == 5:
        flip = (y*x) % 2 + (y*x) % 3 == 0
    elif m == 6:
        flip = ( (y*x) % 2 + (y*x) % 3 ) % 2 == 0
    elif m == 7:
        flip = ( (y+x) % 2 + (y*x) % 3 ) % 2 == 0
    if flip:
        return 1
    else:
        return 0

def extract_codewords(qr, m):
    ver = get_version(qr)
    codewords = []
    k = 0
    w = 0
    wm = 0
    for (x, y) in zigzag(ver):
        if not in_payload_area(ver, x, y):
            continue
        # print (len(codewords), k, x, y)
        if qr[y][x] is None:
            w = w * 2
            wm = wm * 2
        else:
            w = w * 2 + (qr[y][x] ^ mask_at(m, x, y))
            wm = wm * 2 + 1
        k += 1
        if k == 8:
            if wm != 255:
                codewords.append(Uncertain(w, wm))
            else:
                codewords.append(w)
            w = 0
            wm = 0
            k = 0
    return codewords

def uninterleave(codewords, version, ecl):
    (necc, gs) = correction_table[(version, ecl)]
    
    p = 0

    affected = []
    data_groups = []
    for g in gs:
        blocks = []
        for i in range(g[0]):
            blocks.append([])
        data_groups.append(blocks)
        
        blocks = []
        for i in range(g[0]):
            blocks.append([])
        affected.append(blocks)

    ncol = max(map(lambda g: g[1], gs))

    for c in range(ncol):
        for j in range(len(gs)):
            if c >= gs[j][1]:
                continue
            for i in range(gs[j][0]):
                data_groups[j][i].append(codewords[p])
                affected[j][i].append(set([p]))
                p += 1
    
    ecc_groups = []
    for g in gs:
        blocks = []
        for i in range(g[0]):
            blocks.append([])
        ecc_groups.append(blocks)
    
    for c in range(necc):
        for j in range(len(gs)):
            for i in range(gs[j][0]):
                ecc_groups[j][i].append(codewords[p])
                for c in range(gs[j][1]):
                    affected[j][i][c].add(p)
                p += 1

    return (data_groups, ecc_groups, affected)

def groups_to_bitstring(groups):
    s = ""
    for g in groups:
        for b in g:
            for c in b:
                if isinstance(c, Uncertain):
                    t = ""
                    for i in range(8):
                        m = 1 << i
                        if c.mask & m:
                            if c.value & m:
                                t += "1"
                            else:
                                t += "0"
                        else:
                            t += "0" # "?"
                    s += t[::-1]
                else:
                    s += "{:08b}".format(c)
    return s

def flatten_affected(nested_affected):
    affected = []
    for g in nested_affected:
        for b in g:
            for c in b:
                affected.append(c)
    return affected


def bits_affected(affected, p, q):
    pb = p / 8
    qb = (q + 7) / 8
    result = set()
    for s in affected[pb:qb]:
        result.update(s)
    return result

### Error Correction ###
def recover_error_block(data_block, ecc_block):
    rs = reedsolo.RSCodec(len(ecc_block))
    d = map(lambda x: -1 if isinstance(x, Uncertain) else x, data_block)
    e = map(lambda x: -1 if isinstance(x, Uncertain) else x, ecc_block)
    decoded = rs.decode(d + e)
    return decoded

## TODO: Support reedsolo.ReedSolomonError
def recover_error(data_groups, ecc_groups):
    groups = []
    for (dg, eg) in zip(data_groups, ecc_groups):
        blocks = []
        for (db, eb) in zip(dg, eg):
            blocks.append(recover_error_block(db, eb))
        groups.append(blocks)
    return groups

### Decoding data ###

def decode_numeric(bits):
    assert len(bits) in [4, 7, 10]
    l = {4: 1, 7: 2, 10: 3}[len(bits)]
    x = int(bits, 2)
    # TODO: when out of range raise error
    return ("000" + str(x))[-l:]
    
alphanumeric_table = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", " ", "$", "%", "*", "+", "-", ".", "/", ":"]
def decode_alphanumeric(bits):
    assert len(bits) == 6 or len(bits) == 11
    x = int(bits, 2)
    if len(bits) == 6:
        # TODO: when x >= 45 raise error
        return alphanumeric_table[x]
    elif len(bits) == 11:
        # TODO: when x / 45 >= 45 raise error
        return alphanumeric_table[x / 45] + alphanumeric_table[x % 45]

def decode_byte(bits):
    assert len(bits) == 8
    return chr(int(bits, 2))

def decode_kanji(bits):
    assert len(bits) == 13
    x = int(bits, 2)
    if x < 0x1F00:
        # between 0x8140 and 0x9FFC
        x += 0x8140
    else:
        # between 0xE040 and 0xEBBF
        x += 0xC140
    # TODO: when out of range raise error

    import codecs
    decode_sjis = codecs.getdecoder("shiftjis")
    return decode_sjis(chr(x >> 8) + chr(x & 255))[0]

    
MODE_NUM   = 0b0001
MODE_ALNUM = 0b0010
MODE_BYTE  = 0b0100
MODE_KANJI = 0b1000
MODE_ECI   = 0b0111

def ccilen(version, mode):
    if version <= 9:
        if mode == MODE_NUM:
            return 10
        elif mode == MODE_ALNUM:
            return 9
        elif mode == MODE_BYTE or mode == MODE_KANJI:
            return 8
    elif version <= 26:
        if mode == MODE_NUM:
            return 12
        elif mode == MODE_ALNUM:
            return 11
        elif mode == MODE_BYTE:
            return 16
        elif mode == MODE_KANJI:
            return 10
    elif version <= 40:
        if mode == MODE_NUM:
            return 14
        elif mode == MODE_ALNUM:
            return 13
        elif mode == MODE_BYTE:
            return 16
        elif mode == MODE_KANJI:
            return 12
    # Not reached normally
    assert 1 <= version <= 40
    assert mode in [MODE_NUM, MODE_ALNUM, MODE_BYTE, MODE_KANJI]
    assert False
    

def decode_segment(bits, first, version, affected=None,
                   force_mode=None, force_cci=None):
    p = first
    q = p + 4
    if q > len(bits):
        return ("", [], len(bits) - first, True)
    if force_mode is None:
        mode = int(bits[p:q], 2)
    else:
        mode = force_mode
    p = q
    if mode == 0:
        return ("", [], q - first, True)

    q = p + ccilen(version, mode)
    if force_cci is None:
        cci = int(bits[p:q], 2)
    else:
        cci = force_cci
    # print cci
    p = q

    affection = []

    s = ""
    # FIXME: 途中で終わっても無限ループ・クラッシュしないように
    while len(s) < cci:
        # print bits[p:]
        # print s
        if mode == MODE_NUM:
            if cci - len(s) > 2:
                q = p + 10
            elif cci - len(s) == 2:
                q = p + 7
            else:
                q = p + 4
            r = decode_numeric(bits[p:q])
        elif mode == MODE_ALNUM:
            if cci - len(s) > 1:
                q = p + 11
            else:
                q = p + 6
            r = decode_alphanumeric(bits[p:q])
        elif mode == MODE_BYTE:
            q = p + 8
            r = decode_byte(bits[p:q])
        elif mode == MODE_KANJI:
            q = p + 13
            r = decode_kanji(bits[p:q])
        s += r
        if affected is not None:
            affection.append((r, bits_affected(affected, p, q)))
        p = q
    return (s, affection, q - first, False)

def decode(bits, version, affected=None):
    p = 0
    result = ""
    affection = []
    while True:
        (s, a, read, stop) = decode_segment(bits, p, version, affected)
        if stop:
            break
        p += read
        result += s
        affection += a
    return (result, affection)

### Test codes ###
if __name__ == '__main__':
    # ファイルからQRコードを読み込んで
    qr = load("test/sample.qr")
    # 寸法からバージョンを決定して
    version = get_version(qr)
    #show(qr)

    from pprint import pprint
    # AUX: Format Informationの候補一覧を表示
    # 書式: (min(距離), 領域1との距離, 領域2との距離, 候補)
    pprint(match_format(extract_format(qr)))
    # AUX: Version Informationの候補一覧を表示
    # 書式: (min(距離), 領域1との距離, 領域2との距離, 候補)
    if version >= 7:
        pprint(match_version(extract_version(qr)))

    # Format Informationを抽出して最も確からしい物を取り出して
    (ecl, mask) = match_format(extract_format(qr))[0][3]
    print (version, ecl, mask)

    # ペイロードの符号語を取り出して(この時点ではinterleaveされている)
    codewords = extract_codewords(qr, mask)
    print(codewords)
    # 符号語をData, ECCやGroup, Blockごとに分割して
    # 構造: groups[i]: group = blocks
    #       groups[i][j]: block = codewords
    #       groups[i][j][k]: codeword = 8 bits integer
    #       affected[i][j][k]: そのデータ符号語に関連する符号語番号の集合
    (data_groups, ecc_groups, affected) = uninterleave(codewords, version, ecl)
    # エラー訂正を試みて
    try:
        data_groups = recover_error(data_groups, ecc_groups)
    except reedsolo.ReedSolomonError:
        print "Can't recover errors"

    # 全てのデータを直列に並べてビット文字列("0","1"の文字列)にして
    bitstring = groups_to_bitstring(data_groups)
    print(bitstring)
    # QRコード用文字エンコーディングからUnicode文字列に復号して
    # (先頭が欠けているときはmodeやcciを指定してdecode_segmentを呼び出す)
    # 構造: affection[i]: ('シンボルからデコードされた文字列',
    #                      関連する符号語番号の集合)
    (s, affection) = decode(bitstring, version,
                            affected=flatten_affected(affected))
    # AUX: 復号された文字部分列と関係する符号語の場所の一覧を表示
    for i in range(len(affection)):
        print "{}: {}".format(i, affection[i])
    # 文字列を表示
    print s

    # 2番目の文字部分列に関係する場所を強調表示
    show(qr, markerpos(affection[2][1], version))
