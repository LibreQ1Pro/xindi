#!/usr/bin/env python3
"""Builds mockup/index.html (one file, nothing to install: open it in a browser) from mockup/src/*, mockup/texts.json
(tools/extract_texts.py) and the Lucide icons of mockup/icons/."""
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))


def read(*p):
    with open(os.path.join(HERE, *p), encoding="utf-8") as f:
        return f.read()


def main():
    texts = json.loads(read("texts.json"))
    icons = {}
    for path in glob.glob(os.path.join(HERE, "icons", "*.svg")):
        svg = open(path, encoding="utf-8").read()
        svg = re.sub(r'\s+(width|height)="24"', "", svg)
        svg = re.sub(r"\s+", " ", svg).strip()
        icons[os.path.basename(path)[:-4]] = svg
    parts = ["screens%d.js" % i for i in range(1, 10) if os.path.exists(os.path.join(HERE, "src", "screens%d.js" % i))]
    js = "const TEXTS=%s;\nconst ICONS=%s;\n" % (json.dumps(texts, ensure_ascii=False), json.dumps(icons))
    js += read("src", "kit.js") + "\n" + "\n".join(read("src", p) for p in parts) + "\n" + read("src", "shell.js") + "\ninit();\n"
    html = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>QIDI Q1 Pro screen mockup</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>%s</style></head>
<body><div id="side"></div><div id="main"></div><div class="modal" id="modal"></div><script>%s</script></body></html>""" % (read("src", "style.css"), js)
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html", len(html) // 1024, "KB")


if __name__ == "__main__":
    main()
