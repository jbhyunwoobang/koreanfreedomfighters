#!/usr/bin/env python3
"""Extract page content + assets from koreanfreedomfighters.com into data/*.json.

Stdlib only. The site is Squarespace and server-renders its section markup, so a
plain fetch is enough. We keep the author's text byte-for-byte and only record
structure (headings / paragraphs / lists / images) so the generator can re-emit
it in clean semantic HTML.
"""
import html
import json
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
ASSETS = os.path.join(ROOT, "assets")
BASE = "https://www.koreanfreedomfighters.com"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"

# slug on the original site -> output filename
PAGES = [
    ("/", "index"),
    ("/schedule", "about"),
    ("/1st-class", "korean-1st-class"),
    ("/2nd-class", "korean-2nd-class"),
    ("/3rd-class", "korean-3rd-class"),
    ("/4th-class", "korean-4th-class"),
    ("/5th-class", "korean-5th-class"),
    ("/national-award-1", "korean-national-award"),
    ("/classes-2-1", "foreign-1st-class"),
    ("/classes-2", "foreign-2nd-class"),
    ("/classes-2-1-2", "foreign-3rd-class"),
    ("/classes-2-1-2-1", "foreign-4th-class"),
    ("/classes-2-1-2-2", "foreign-5th-class"),
    ("/national-award", "foreign-national-award"),
]

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def fetch(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
        raw = r.read()
    return raw if binary else raw.decode("utf-8", "replace")


BLOCK = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li"}
INLINE_KEEP = {"strong", "b", "em", "i", "u", "br", "sup", "sub"}
CACHE = os.path.join(DATA, "assets.json")


class SectionParser(HTMLParser):
    """Walk the document once, emitting an ordered list of section -> nodes."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections = []
        self.depth_stack = []      # open tags, for tracking section nesting
        self.in_section = 0
        self.section_open_depth = None
        self.cur = None            # current node list
        self.block = None          # {"tag":..., "parts":[...]}
        self.list_stack = []
        self.skip = 0              # inside script/style/svg/noscript

    # --- helpers ---------------------------------------------------------
    def _attr(self, attrs, name):
        for k, v in attrs:
            if k == name:
                return v or ""
        return ""

    def _push_block(self, tag):
        self.block = {"tag": tag, "parts": []}

    def _flush_block(self):
        if not self.block:
            return
        text = "".join(self.block["parts"])
        # collapse whitespace but keep intentional <br>
        text = re.sub(r"[ \t ]+", " ", text)
        text = re.sub(r"\s*\n\s*", " ", text)
        text = text.strip()
        if text and re.search(r"[^\s​]", re.sub(r"<[^>]+>", "", text)):
            tag = self.block["tag"]
            if tag == "button":
                node = {"type": "button", "html": text, "href": self.block.get("href", "")}
            else:
                node = {"type": "list-item" if tag == "li" else tag, "html": text}
            self.cur.append(node)
        self.block = None

    # --- parser hooks ----------------------------------------------------
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "svg", "noscript"):
            self.skip += 1
            return
        if self.skip:
            return
        self.depth_stack.append(tag)

        if tag == "section":
            self._flush_block()
            self.in_section += 1
            if self.in_section == 1:
                self.section_open_depth = len(self.depth_stack)
                self.cur = []
                self.sections.append(self.cur)
            return

        if self.cur is None:
            return

        cls = self._attr(attrs, "class")
        # Squarespace navigation / accessibility chrome we never want as content
        if "sqs-block-horizontalrule" in cls or "hrule" in cls:
            self.cur.append({"type": "rule"})
            return

        if tag == "img":
            src = (self._attr(attrs, "data-src") or self._attr(attrs, "src") or "")
            if src.startswith("data:"):
                src = self._attr(attrs, "data-src")
            if src and not src.startswith("data:"):
                self.cur.append({
                    "type": "img",
                    "src": src,
                    "alt": self._attr(attrs, "alt"),
                    "w": self._attr(attrs, "data-image-dimensions"),
                })
            return

        if tag in BLOCK:
            self._flush_block()
            self._push_block(tag)
            return

        if tag in ("ul", "ol"):
            self._flush_block()
            self.list_stack.append(tag)
            self.cur.append({"type": "list-start", "ordered": tag == "ol"})
            return

        if tag == "a":
            href = self._attr(attrs, "href")
            if "sqs-block-button-element" in cls:
                self._flush_block()
                self._push_block("button")
                self.block["href"] = href
                return
            if self.block is not None and href:
                self.block["parts"].append('<a href="%s">' % html.escape(href, quote=True))
                self.block["open_a"] = True
                return

        if self.block is not None and tag in INLINE_KEEP:
            self.block["parts"].append("<br>" if tag == "br" else "<%s>" % tag)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "svg", "noscript"):
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return

        if tag == "section" and self.in_section:
            self._flush_block()
            if self.in_section == 1:
                self.cur = None
                self.section_open_depth = None
            self.in_section -= 1
        elif self.cur is not None:
            if tag in BLOCK:
                self._flush_block()
            elif tag in ("ul", "ol"):
                self._flush_block()
                if self.list_stack:
                    self.list_stack.pop()
                self.cur.append({"type": "list-end"})
            elif tag == "a" and self.block is not None:
                if self.block["tag"] == "button":
                    self._flush_block()
                elif self.block.pop("open_a", None):
                    self.block["parts"].append("</a>")
            elif self.block is not None and tag in INLINE_KEEP and tag != "br":
                self.block["parts"].append("</%s>" % tag)

        if self.depth_stack:
            # pop the matching open tag if present
            for i in range(len(self.depth_stack) - 1, -1, -1):
                if self.depth_stack[i] == tag:
                    del self.depth_stack[i:]
                    break

    def handle_data(self, data):
        if self.skip or self.block is None:
            return
        self.block["parts"].append(html.escape(data, quote=False))


NAV_NOISE = re.compile(
    r"^(skip to content|open menu|close menu|home|about|koreanactivists|foreignactivists|"
    r"1st class|2nd class|3rd class|4th class|5th class|national award|folder|back)$",
    re.I,
)


def clean(nodes):
    """Drop nav chrome and empty scaffolding from a section's node list."""
    out = []
    for n in nodes:
        if n["type"] in ("h1", "h2", "h3", "h4", "h5", "h6", "p", "list-item"):
            plain = re.sub(r"<[^>]+>", "", n["html"]).strip()
            if not plain or NAV_NOISE.match(plain):
                continue
        out.append(n)
    # collapse list-start immediately followed by list-end
    res = []
    for n in out:
        if n["type"] == "list-end" and res and res[-1]["type"] == "list-start":
            res.pop()
            continue
        res.append(n)
    while res and res[0]["type"] in ("rule", "list-end"):
        res.pop(0)
    while res and res[-1]["type"] in ("rule", "list-start"):
        res.pop()
    return res


def local_name(url):
    path = urllib.parse.urlsplit(url).path
    stem = urllib.parse.unquote(os.path.basename(path))
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-._") or "image"
    root, ext = os.path.splitext(stem)
    root = root[:60]
    return root, ext.lower()


def download_asset(url, seen):
    if url in seen:
        return seen[url]
    cached = seen.get("__disk__", {}).get(url)
    if cached and os.path.exists(os.path.join(ROOT, cached)):
        seen[url] = cached
        return cached
    full = url if url.startswith("http") else urllib.parse.urljoin(BASE, url)
    # ask Squarespace for a reasonable width instead of the 2500w original
    if "images.squarespace-cdn.com" in full:
        full = re.sub(r"([?&])format=\d+w", r"\1format=1500w", full)
        if "format=" not in full:
            full += ("&" if "?" in full else "?") + "format=1500w"
    root, ext = local_name(full)
    try:
        blob = fetch(full, binary=True)
    except Exception as exc:                      # noqa: BLE001
        print("  ! asset failed %s (%s)" % (full[:80], exc))
        seen[url] = None
        return None
    if blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        ext = ".webp"
    elif blob[:3] == b"\xff\xd8\xff":
        ext = ".jpg"
    elif blob[:8] == b"\x89PNG\r\n\x1a\n":
        ext = ".png"
    elif blob[:6] in (b"GIF87a", b"GIF89a"):
        ext = ".gif"
    name = root + ext
    i = 2
    while os.path.exists(os.path.join(ASSETS, name)) and seen.get("__by_name__", {}).get(name) != url:
        seen.setdefault("__by_name__", {})
        if seen["__by_name__"].get(name) == url:
            break
        name = "%s-%d%s" % (root, i, ext)
        i += 1
    seen.setdefault("__by_name__", {})[name] = url
    with open(os.path.join(ASSETS, name), "wb") as fh:
        fh.write(blob)
    rel = "assets/" + name
    seen[url] = rel
    print("  + %-58s %6.0f KB" % (name[:58], len(blob) / 1024))
    return rel


def main():
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(ASSETS, exist_ok=True)
    seen = {}
    if os.path.exists(CACHE):
        with open(CACHE) as fh:
            seen["__disk__"] = json.load(fh)
    manifest = {}
    for slug, out in PAGES:
        url = BASE + slug
        print("== %s -> %s.json" % (url, out))
        try:
            doc = fetch(url)
        except Exception as exc:                  # noqa: BLE001
            print("  ! page failed: %s" % exc)
            continue
        title = ""
        m = re.search(r"<title>(.*?)</title>", doc, re.S | re.I)
        if m:
            title = html.unescape(m.group(1)).strip()
        p = SectionParser()
        p.feed(doc)
        sections = []
        for nodes in p.sections:
            nodes = clean(nodes)
            if not nodes:
                continue
            for n in nodes:
                if n["type"] == "img":
                    rel = download_asset(n["src"], seen)
                    n["local"] = rel
            sections.append(nodes)
        # the last section on every page is the shared GET IN TOUCH footer
        manifest[out] = {"slug": slug, "title": title, "sections": sections}
        print("  sections: %d" % len(sections))
    with open(os.path.join(DATA, "site.json"), "w") as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=False)
    disk = dict(seen.get("__disk__", {}))
    disk.update({k: v for k, v in seen.items()
                 if v and not k.startswith("__") and isinstance(v, str)})
    with open(CACHE, "w") as fh:
        json.dump(disk, fh, indent=1)
    print("\nwrote data/site.json  (%d pages, %d assets)" % (len(manifest), len(disk)))


if __name__ == "__main__":
    sys.exit(main())
