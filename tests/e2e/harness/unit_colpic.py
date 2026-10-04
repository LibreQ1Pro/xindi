#!/usr/bin/env python3
"""
Equivalence test of the thumbnail converter (runs inside the xindi-e2e image):
the original /home/mks/gene4.py with the original aarch64 /home/mks/libColPic.so
against xindi/gene4.py of the port on a set of generated pictures.
"""

import os
import random
import subprocess
import sys

sys.path.insert(0, "/opt/src_py")

from PIL import Image  # noqa: E402

from xindi import gene4  # noqa: E402

WORK = "/tmp/colpic"


def make_images(rng):
    images = []
    specs = [
        ("RGB", (1, 1)), ("RGB", (2, 3)), ("RGBA", (160, 160)), ("RGB", (112, 112)), ("RGB", (300, 200)),
        ("RGB", (64, 300)), ("L", (50, 50)), ("P", (90, 60)), ("RGBA", (176, 176)), ("RGB", (17, 255)),
    ]
    for i, (mode, size) in enumerate(specs):
        for kind in ("noise", "flat", "stripes", "blocks"):
            img = Image.new("RGB", size)
            px = img.load()
            w, h = size
            for y in range(h):
                for x in range(w):
                    if kind == "noise":
                        px[x, y] = (rng.randrange(256), rng.randrange(256), rng.randrange(256))
                    elif kind == "flat":
                        px[x, y] = (12, 200, 99)
                    elif kind == "stripes":
                        px[x, y] = ((x * 37) % 256, (y * 11) % 256, ((x + y) * 5) % 256)
                    else:
                        c = ((x // 7) * 50 + (y // 5) * 30) % 256
                        px[x, y] = (c, 255 - c, (c * 3) % 256)
            if mode != "RGB":
                img = img.convert(mode)
            path = os.path.join(WORK, "img_%02d_%s.png" % (i, kind))
            img.save(path)
            images.append(path)
    jpg = os.path.join(WORK, "photo.jpg")
    Image.open(images[2]).convert("RGB").save(jpg, quality=70)
    images.append(jpg)
    return images


def main():
    os.makedirs(WORK, exist_ok=True)
    rng = random.Random(1234)
    images = make_images(rng)
    sizes = [160, 112, 176, 200, 1, 33]
    failures = 0
    total = 0
    for img in images:
        for size in sizes:
            ref = os.path.join(WORK, "ref.txt")
            out = os.path.join(WORK, "py.txt")
            for p in (ref, out):
                if os.path.exists(p):
                    os.unlink(p)
            subprocess.run(["python3", "/home/mks/gene4.py", img, ref, str(size)], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            gene4.main([img, out, str(size)])
            a = open(ref, "rb").read() if os.path.exists(ref) else None
            b = open(out, "rb").read() if os.path.exists(out) else None
            total += 1
            if a != b:
                failures += 1
                print("MISMATCH %s size=%d ref=%s py=%s" % (os.path.basename(img), size,
                                                            None if a is None else len(a), None if b is None else len(b)))
    print("colpic: %d/%d conversions identical" % (total - failures, total))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
