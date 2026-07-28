#!/usr/bin/env python3
"""Confirm the generated pages contain every text string scraped from the original.

data/site.json is a direct extraction from koreanfreedomfighters.com, so if each
of its strings survives into the rendered HTML, no content was lost or altered.
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAGS = re.compile(r"<[^>]+>")
WS = re.compile(r"\s+")


def flat(s):
    s = TAGS.sub("", s or "")
    s = html.unescape(s)
    s = s.replace("​", "")
    return WS.sub(" ", s).strip()


def main():
    with open(os.path.join(ROOT, "data", "site.json")) as fh:
        pages = json.load(fh)

    total = missing = 0
    imgs_total = imgs_missing = 0
    problems = []

    for out, page in pages.items():
        path = os.path.join(ROOT, out + ".html")
        if not os.path.exists(path):
            problems.append("%s: page not generated" % out)
            continue
        with open(path) as fh:
            doc = fh.read()
        rendered = flat(doc)

        for sec in page["sections"]:
            for n in sec:
                if n["type"] == "img":
                    imgs_total += 1
                    if n.get("local"):
                        if ('src="%s"' % n["local"]) not in doc:
                            imgs_missing += 1
                            problems.append("%s: image not placed %s" % (out, n["local"]))
                        elif not os.path.exists(os.path.join(ROOT, n["local"])):
                            imgs_missing += 1
                            problems.append("%s: image file absent %s" % (out, n["local"]))
                    continue
                if n["type"] not in ("h1", "h2", "h3", "h4", "p", "list-item", "button"):
                    continue
                # a <br> is a line break, so compare each line independently
                for frag in re.split(r"<br\s*/?>", n["html"]):
                    want = flat(frag)
                    if not want:
                        continue
                    total += 1
                    if want not in rendered:
                        missing += 1
                        problems.append("%s: MISSING TEXT %r" % (out, want[:90]))

    print("text strings : %d checked, %d missing" % (total, missing))
    print("images       : %d checked, %d missing" % (imgs_total, imgs_missing))
    if problems:
        print("\nproblems (%d):" % len(problems))
        for p in problems[:40]:
            print("  -", p)
        if len(problems) > 40:
            print("  … %d more" % (len(problems) - 40))
        return 1
    print("\nOK — every scraped string and image is present in the build.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
