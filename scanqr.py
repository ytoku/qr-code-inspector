import Image
import sys

def scan(img, top, left, msize, version):
    w = h = version * 4 + 17
    qr = []
    for y in range(h):
        line = []
        for x in range(w):
            c = img.getpixel((top + msize * x, left + msize * y))
            if c == (0, 0, 0):
                x = 1
            elif c == (255, 255, 255):
                x = 0
            else:
                x = -1
            line.append(x)
        qr.append(line)
    return qr

version = 7

img = Image.open("version7.png")
img = img.convert('RGB')
qr = scan(img, 0, 0, 2, version)

print version * 4 + 17
for line in qr:
    for m in line:
        if m == 1:
            c = "*"
        elif m == 0:
            c = " "
        else:
            c = "?"
        sys.stdout.write(c)
    sys.stdout.write("\n")
