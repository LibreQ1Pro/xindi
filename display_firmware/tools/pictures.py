#!/usr/bin/env python3
"""Helpers to add, rename and remove pictures of the screen project (a library for the scripts of this directory).

    from pictures import Pictures
    p = Pictures()
    p.add("fan_slider_track", "/path/track.png")      # copies the file to pictures/<key>.png, appends the key
    p.rename("hdr_back_press", "header_back_press")  # file, project.json, every reference, names.json, xindi pics.py
    p.remove(["unused_one"])                          # refuses while the picture is still referenced
    p.save()                                          # writes project.json and renumbers xindi/screen/pics.py

The id of a picture is its position in ``project.json``; the host (xindi/screen/pics.py) sends the ids of some of
them by name, so pics.py is written again from the names of the new positions. A reference is ``"$ref": "picture:KEY"``
in the pages and ``${picture:KEY}`` in their code.
"""
import glob
import json
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # display_firmware/
PICS_PY = os.path.join(os.path.dirname(ROOT), "xindi", "screen", "pics.py")


def reference(key):
    """Regex of the references to the picture ``key`` (the key may be a prefix of another one)."""
    return re.compile(r"picture:%s(?![A-Za-z0-9_])" % re.escape(key))


class Pictures(object):
    def __init__(self):
        with open(os.path.join(ROOT, "project.json"), encoding="utf-8") as f:
            self.project = json.load(f)
        self.raw = open(os.path.join(ROOT, "project.json"), encoding="utf-8").read()
        self.old_keys = self.keys()
        self.renamed = {}                       # old key -> new key (for pics.py)

    def keys(self):
        return [p["key"] for p in self.project["pictures"]]

    def pages(self):
        return sorted(glob.glob(os.path.join(ROOT, "pages", "*.json")))

    def users(self, key):
        """The page files that refer to the picture."""
        rx = reference(key)
        found = []
        for path in self.pages():
            with open(path, encoding="utf-8") as f:
                if rx.search(f.read()):
                    found.append(os.path.basename(path))
        return found

    def add(self, key, png, index=None):
        if key in self.keys():
            raise ValueError("picture %s exists" % key)
        dest = os.path.join(ROOT, "pictures", key + ".png")
        if os.path.abspath(png) != os.path.abspath(dest):
            shutil.copy(png, dest)
        entry = {"key": key, "source": {"png": "pictures/%s.png" % key}}
        if index is None:
            self.project["pictures"].append(entry)
        else:
            self.project["pictures"].insert(index, entry)

    def remove(self, keys):
        for key in keys:
            used = self.users(key)
            if used:
                raise ValueError("picture %s is still used by %s" % (key, ", ".join(used)))
        gone = set(keys)
        self.project["pictures"] = [p for p in self.project["pictures"] if p["key"] not in gone]
        for key in keys:
            path = os.path.join(ROOT, "pictures", key + ".png")
            if os.path.exists(path):
                os.remove(path)

    def rename(self, old, new):
        if new in self.keys():
            raise ValueError("picture %s exists" % new)
        for entry in self.project["pictures"]:
            if entry["key"] == old:
                entry["key"] = new
                entry["source"]["png"] = "pictures/%s.png" % new
        src, dest = (os.path.join(ROOT, "pictures", k + ".png") for k in (old, new))
        if os.path.exists(src):
            os.rename(src, dest)
        rx = reference(old)
        for path in self.pages():
            with open(path, encoding="utf-8") as f:
                text = f.read()
            if rx.search(text):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(rx.sub("picture:" + new, text))
        names = os.path.join(ROOT, "tools", "names.json")
        with open(names, encoding="utf-8") as f:
            data = json.load(f)
        for stock, readable in data["pictures"].items():
            if readable == old:
                data["pictures"][stock] = new
        with open(names, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.write("\n")
        for was, now in list(self.renamed.items()):
            if now == old:
                self.renamed[was] = new
                break
        else:
            self.renamed[old] = new

    def save(self):
        with open(os.path.join(ROOT, "project.json"), "w", encoding="utf-8") as f:
            json.dump(self.project, f, ensure_ascii=False, indent=2)
            f.write("\n")
        self.sync_host()

    def sync_host(self):
        """Writes xindi/screen/pics.py again: the same names, the ids of the new positions."""
        keys = self.keys()
        with open(PICS_PY, encoding="utf-8") as f:
            lines = f.read().split("\n")
        out = []
        for line in lines:
            m = re.match(r'^([A-Za-z0-9_]+) = "(\d+)"$', line)
            if m:
                name = m.group(1)
                old_key = self.old_keys[int(m.group(2))]
                key = self.renamed.get(old_key, old_key)
                if key not in keys:
                    raise ValueError("pics.py: the picture %s (%s) is gone" % (name, old_key))
                line = '%s = "%d"' % (name, keys.index(key))
            out.append(line)
        with open(PICS_PY, "w", encoding="utf-8") as f:
            f.write("\n".join(out))
