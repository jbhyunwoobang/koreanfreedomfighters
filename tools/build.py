#!/usr/bin/env python3
"""Render the static site from data/site.json.

The author's text is emitted exactly as scraped. This module only decides
*structure*: which section becomes a hero, a split, or an activist profile, and
what heading level each string gets so the document outline is valid.
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

SITE_NAME = "KoreanFreedomFighters"
EMAIL = "jbhyunwoobang@gmail.com"
INSTAGRAM = "https://www.instagram.com/heritage_of_koreans/"
INSTAGRAM_HANDLE = "@heritage_of_koreans"

KOREAN_PAGES = [
    ("1st Class", "korean-1st-class"),
    ("2nd Class", "korean-2nd-class"),
    ("3rd Class", "korean-3rd-class"),
    ("4th Class", "korean-4th-class"),
    ("5th Class", "korean-5th-class"),
    ("National Award", "korean-national-award"),
]
FOREIGN_PAGES = [
    ("1st Class", "foreign-1st-class"),
    ("2nd Class", "foreign-2nd-class"),
    ("3rd Class", "foreign-3rd-class"),
    ("4th Class", "foreign-4th-class"),
    ("5th Class", "foreign-5th-class"),
    ("National Award", "foreign-national-award"),
]

DATES_RE = re.compile(r"^\s*\[")
STRIP_TAGS = re.compile(r"<[^>]+>")

# page -> 건국훈장 class, for attaching the official roster
PAGE_CLASS = {
    "korean-1st-class": 1, "korean-2nd-class": 2, "korean-3rd-class": 3,
    "korean-4th-class": 4, "korean-5th-class": 5,
    "foreign-1st-class": 1, "foreign-2nd-class": 2, "foreign-3rd-class": 3,
    "foreign-4th-class": 4, "foreign-5th-class": 5,
}
# the foreign pages list the same grades, filtered to non-Korean recipients
FOREIGN_ONLY = {p for p in PAGE_CLASS if p.startswith("foreign-")}

I18N, GONG, MATCHES = {}, {}, {}
_untranslated = []


def load_side_data():
    global I18N, GONG, MATCHES
    for name, target in (("i18n.json", "I18N"), ("gonghun.json", "GONG"), ("matches.json", "MATCHES")):
        path = os.path.join(DATA, name)
        if os.path.exists(path):
            with open(path) as fh:
                globals()[target] = json.load(fh)


def txt(node_html):
    return html.unescape(STRIP_TAGS.sub("", node_html or "")).strip()


def ko_for(en_html):
    """Look up the Korean rendering for a source string, if we have one."""
    key = txt(en_html)
    hit = I18N.get("prose", {}).get(key)
    if hit is not None:
        return hit  # "" means: deliberately not shown in Korean
    if key and len(key) > 1:
        _untranslated.append(key)
    return None


LEAD = re.compile(r"^\s*<(strong|b)>(.*?)</\1>\s*<br\s*/?>\s*", re.S | re.I)


def restore_lead(en_html, ko):
    """Put back a bold lead-in the translation flattened.

    Several bullets open with a bold label, a line break, then the detail. The
    Korean came back as one plain run, which loses that structure. If we know
    the label's own Korean and the translation starts with it, re-split there.
    """
    m = LEAD.match(en_html or "")
    if not m:
        # a node that packs several "○" items behind <br> came back as one run;
        # the markers survived, so break the line before each of them again
        if "<br" in (en_html or "") and ko.count("○") > 1:
            parts = [q.strip() for q in ko.split("○") if q.strip()]
            return "<br>".join("○ " + html.escape(q) for q in parts)
        return html.escape(ko)
    ko_lab = I18N.get("prose", {}).get(txt(m.group(2)))
    if not ko_lab or not ko.startswith(ko_lab):
        return html.escape(ko)
    return "<strong>%s</strong><br>%s" % (
        html.escape(ko_lab), html.escape(ko[len(ko_lab):].lstrip()))


def bi(en_html, tag="span"):
    """Emit both languages; CSS reveals whichever matches the active language."""
    ko = ko_for(en_html)
    if ko is None:
        # no translation yet: show the English text in both modes
        return '<%s class="i18n" data-both>%s</%s>' % (tag, en_html, tag)
    if not ko.strip():
        # English-only line: the Korean above already carries the whole question,
        # so repeating it as a subtitle would read as a stutter.
        return '<%s class="i18n only-en" lang="en" data-en>%s</%s>' % (tag, en_html, tag)
    return ('<%s class="i18n" lang="en" data-en>%s</%s>'
            '<%s class="i18n" lang="ko" data-ko>%s</%s>'
            % (tag, en_html, tag, tag, restore_lead(en_html, ko), tag))


def ui(key):
    """A chrome string in both languages."""
    e = I18N.get("ui", {}).get(key)
    if not e:
        return key
    return ('<span class="i18n" lang="en" data-en>%s</span>'
            '<span class="i18n" lang="ko" data-ko>%s</span>'
            % (html.escape(e["en"]), html.escape(e["ko"])))


def ui_raw(key, lang="en"):
    e = I18N.get("ui", {}).get(key)
    return e[lang] if e else key


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", txt(s).lower()).strip("-")
    return s or "entry"


# ----------------------------------------------------------------- rendering --

def render_prose(nodes, base_level=3):
    """Render a run of text nodes. `p` inside a list run becomes an <li>."""
    out = []
    in_list = False
    for n in nodes:
        t = n["type"]
        if t == "list-start":
            out.append("<ul>")
            in_list = True
        elif t == "list-end":
            out.append("</ul>")
            in_list = False
        elif t == "rule":
            out.append('<hr class="rule">')
        elif t == "p":
            out.append("<li>%s</li>" % bi(n["html"]) if in_list else "<p>%s</p>" % bi(n["html"]))
        elif t == "list-item":
            out.append("<li>%s</li>" % bi(n["html"]))
        elif t in ("h1", "h2", "h3", "h4", "h5", "h6"):
            lvl = min(6, base_level + {"h1": 0, "h2": 0, "h3": 1, "h4": 1}.get(t, 1))
            out.append('<h%d class="h-label">%s</h%d>' % (lvl, bi(n["html"]), lvl))
        elif t == "button":
            href = n.get("href") or "#"
            out.append(
                '<p><a class="btn" href="%s">%s<span class="btn__arrow" aria-hidden="true">&rarr;</span></a></p>'
                % (html.escape(map_href(href), quote=True), bi(n["html"]))
            )
        elif t == "img":
            if n.get("local"):
                out.append('<img src="%s" alt="" loading="lazy" decoding="async">' % n["local"])
    if in_list:
        out.append("</ul>")
    return "\n        ".join(out)


HREF_MAP = {"/": "index.html", "/schedule": "about.html"}
for _label, _slug in KOREAN_PAGES:
    HREF_MAP.setdefault(_label, None)


def build_href_map(pages):
    m = dict(HREF_MAP)
    for out, page in pages.items():
        m[page["slug"]] = out + ".html"
    return m


HREFS = {}


def map_href(href):
    """Rewrite on-site links to the generated filenames; leave the rest alone."""
    if not href:
        return "#"
    clean = href.split("?")[0].rstrip("/") or "/"
    if clean in HREFS:
        return HREFS[clean]
    if href.startswith(("http://", "https://", "mailto:", "tel:", "#")):
        return href
    return HREFS.get(href, href)


def is_profile(section):
    """A profile section is a portrait + NAME + [dates] + body."""
    heads = [n for n in section if n["type"] in ("h1", "h2", "h3")]
    for i, n in enumerate(heads[:-1]):
        if DATES_RE.match(txt(heads[i + 1]["html"])):
            return True
    return False


def split_profile(section):
    img = next((n for n in section if n["type"] == "img"), None)
    heads = [n for n in section if n["type"] in ("h1", "h2", "h3")]
    name = heads[0] if heads else None
    dates = None
    for i, n in enumerate(heads[:-1]):
        if DATES_RE.match(txt(heads[i + 1]["html"])):
            name, dates = n, heads[i + 1]
            break
    rest = [n for n in section if n is not img and n is not name and n is not dates]
    return img, name, dates, rest


def render_hero(section, page_title):
    img = next((n for n in section if n["type"] == "img"), None)
    heads = [n for n in section if n["type"] in ("h1", "h2", "h3", "h4")]
    rest = [n for n in section if n["type"] not in ("img",) and n not in heads]
    lines = []
    if heads:
        lines.append('<h1 class="h-hero">%s</h1>' % bi(heads[0]["html"]))
        for h in heads[1:]:
            lines.append('<p class="h-hero-sub" role="doc-subtitle">%s</p>' % bi(h["html"]))
    else:
        lines.append('<h1 class="h-hero">%s</h1>' % html.escape(page_title))
    media = ""
    if img and img.get("local"):
        media = (
            '  <div class="hero__media">\n'
            '    <img src="%s" alt="" fetchpriority="high" decoding="async">\n'
            "  </div>\n" % img["local"]
        )
    extra = render_prose(rest, 2) if rest else ""
    return (
        '<section class="section hero">\n'
        "%s"
        '  <div class="hero__slab reveal">\n'
        '    <div class="hero__rule" aria-hidden="true"><i></i><i></i><i></i></div>\n'
        "    %s\n"
        "%s"
        "  </div>\n"
        "</section>"
        % (media, "\n    ".join(lines), ('    <div class="prose">%s</div>\n' % extra) if extra else "")
    )


def render_split(section, flip):
    img = next((n for n in section if n["type"] == "img"), None)
    body = [n for n in section if n is not img]
    heads = [n for n in body if n["type"] in ("h1", "h2")]
    lead = heads[0] if heads else None
    rest = [n for n in body if n is not lead]
    parts = []
    if lead:
        parts.append('<h2 class="h-section">%s</h2>' % bi(lead["html"]))
    prose = render_prose(rest, 3)
    if not img or not img.get("local"):
        return (
            '<section class="section reveal">\n  <div class="shell statement">\n    %s\n'
            '    <div class="prose">%s</div>\n  </div>\n</section>'
            % ("\n    ".join(parts), prose)
        )
    return (
        '<section class="section reveal">\n'
        '  <div class="shell split%s">\n'
        '    <div class="split__body">\n      %s\n      <div class="prose">%s</div>\n    </div>\n'
        '    <figure class="split__media">\n      <img src="%s" alt="" loading="lazy" decoding="async">\n    </figure>\n'
        "  </div>\n"
        "</section>"
        % (" split--flip" if flip else "", "\n      ".join(parts), prose, img["local"])
    )


def render_banner(section):
    img = next((n for n in section if n["type"] == "img"), None)
    if not img or not img.get("local"):
        return ""
    return (
        '<section class="section banner" aria-hidden="true">\n'
        '  <div class="banner__media">\n    <img src="%s" alt="" loading="lazy" decoding="async">\n  </div>\n'
        "</section>" % img["local"]
    )


def render_profile(section, anchor, match=None):
    img, name, dates, rest = split_profile(section)
    portrait = ""
    if img and img.get("local"):
        portrait = (
            '    <figure class="profile__aside">\n'
            '      <img class="profile__portrait" src="%s" alt="Portrait of %s" loading="lazy" decoding="async">\n'
            "    </figure>\n" % (img["local"], html.escape(txt(name["html"]).rstrip(" :"), quote=True))
        )
    head = ""
    if name:
        label = name["html"]
        if match and match.get("name_ko"):
            # in Korean mode show the name as the official record spells it
            ko = match["name_ko"]
            if match.get("name_hanja") and re.search(r"[一-鿿]", match["name_hanja"]):
                ko += " %s" % match["name_hanja"]
            label = ('<span class="i18n" lang="en" data-en>%s</span>'
                     '<span class="i18n" lang="ko" data-ko>%s</span>'
                     % (label, html.escape(ko)))
        head += '<h2 class="h-name profile__name">%s</h2>\n      ' % label
    if dates:
        head += '<p class="profile__dates">%s</p>\n      ' % dates["html"]
    if match:
        head += ('<p class="profile__official">'
                 '<span lang="ko">건국훈장 %s</span> · %s</p>\n      '
                 % (html.escape(match.get("grade_ko") or ""),
                    html.escape(match.get("award_year") or "")))
    return (
        '<article class="profile reveal" id="%s">\n'
        '  <div class="shell profile__grid">\n'
        "%s"
        '    <div class="profile__body">\n      %s<div class="prose">%s</div>\n    </div>\n'
        "  </div>\n"
        "</article>" % (anchor, portrait, head, render_prose(rest, 3))
    )


def roster_records(cls, foreign):
    """The official recipients for one grade, split Korean / foreign by 본적."""
    for v in GONG.values():
        if v.get("class") != cls:
            continue
        rows = []
        for r in v["records"]:
            is_foreign = str(r.get("origin_ko") or "").startswith("외국")
            if is_foreign == foreign:
                rows.append(r)
        rows.sort(key=lambda r: (r.get("name_ko") or ""))
        return v, rows
    return None, []


def render_roster(page, cls, profile_anchors):
    grade = I18N.get("grades", {}).get(str(cls), {})
    meta, rows = roster_records(cls, page in FOREIGN_ONLY)
    if not rows:
        return ""
    moves = I18N.get("movements", {})
    # name -> anchor of a featured profile on this page, so rows can link across
    linked = {}
    for label, m in (MATCHES.get(page) or {}).items():
        if m.get("name_ko"):
            linked[m["name_ko"]] = slugify(label)

    trs = []
    for r in rows:
        ko = r.get("name_ko") or "—"
        anchor = linked.get(ko)
        name_cell = html.escape(ko)
        if anchor:
            name_cell = '<a class="roster__jump" href="#%s">%s</a>' % (anchor, name_cell)
        mv = r.get("movement_ko") or ""
        mv_en = moves.get(mv, mv)
        prior = ""
        if r.get("prior_awards"):
            bits = ", ".join("%s %s" % (p["grade_ko"], p.get("award_year") or "")
                             for p in r["prior_awards"])
            prior = ' <span class="roster__prior">(%s %s)</span>' % (
                ui_raw("prior_award", "ko"), html.escape(bits.strip()))
        trs.append(
            "<tr>"
            '<th scope="row" lang="ko">%s</th>'
            '<td lang="ko" class="roster__hanja">%s</td>'
            "<td>%s</td>"
            '<td class="roster__move"><span class="i18n" lang="en" data-en>%s</span>'
            '<span class="i18n" lang="ko" data-ko>%s</span></td>'
            "<td>%s%s</td>"
            '<td lang="ko" class="roster__origin">%s</td>'
            "</tr>"
            % (name_cell,
               html.escape(r.get("name_hanja") or "—"),
               html.escape(r.get("years") or "—"),
               html.escape(mv_en), html.escape(mv),
               html.escape(r.get("award_year") or "—"), prior,
               html.escape(r.get("origin_ko") or "—"))
        )

    crit = ""
    if grade:
        crit = (
            '  <div class="roster__criteria">\n'
            '    <h3 class="h-label">%s</h3>\n'
            '    <p><strong lang="ko">건국훈장 %s</strong> <span lang="ko">(%s)</span></p>\n'
            '    <p><span class="i18n" lang="en" data-en>%s</span>'
            '<span class="i18n" lang="ko" data-ko>%s</span></p>\n'
            "  </div>\n"
            % (ui("criteria_label"), html.escape(grade["ko_name"]),
               html.escape(grade["ko_class"]),
               html.escape(grade.get("criteria_en", "")),
               html.escape(grade.get("criteria_ko", "")))
        )

    return (
        '<section class="section roster" id="roster" aria-labelledby="roster-h">\n'
        '  <div class="shell">\n'
        '    <div class="roster__head">\n'
        '      <h2 class="h-section" id="roster-h">%s</h2>\n'
        '      <p class="roster__count"><strong>%d</strong> %s</p>\n'
        "    </div>\n"
        '    <p class="roster__note">%s</p>\n'
        "%s"
        '    <div class="roster__tools">\n'
        '      <input class="roster__search" type="search" placeholder="%s" aria-label="%s"'
        ' data-ph-en="%s" data-ph-ko="%s">\n'
        '      <p class="roster__shown" aria-live="polite"></p>\n'
        "    </div>\n"
        '    <div class="roster__scroll">\n'
        '      <table class="roster__table">\n'
        "        <thead><tr><th>%s</th><th>%s</th><th>%s</th><th>%s</th><th>%s</th>"
        "<th>%s</th></tr></thead>\n"
        "        <tbody>\n          %s\n        </tbody>\n"
        "      </table>\n"
        "    </div>\n"
        '    <p class="roster__empty" hidden>%s</p>\n'
        "  </div>\n"
        "</section>"
        % (ui("roster"), len(rows), ui("entries"), ui("roster_note"), crit,
           html.escape(ui_raw("filter_ph", "en"), quote=True),
           html.escape(ui_raw("filter_label", "en"), quote=True),
           html.escape(ui_raw("filter_ph", "en"), quote=True),
           html.escape(ui_raw("filter_ph", "ko"), quote=True),
           ui("col_name"), ui("col_hanja"), ui("col_years"), ui("col_movement"),
           ui("col_award"), ui("col_origin"),
           "\n          ".join(trs), ui("filter_empty"))
    )


def render_index(profiles):
    if len(profiles) < 3:
        return ""
    rows = "\n      ".join(
        '<li><a href="#%s">%s</a></li>' % (a, html.escape(label)) for a, label in profiles
    )
    return (
        '<nav class="pageindex" aria-labelledby="idx-h">\n'
        '  <div class="shell">\n'
        '    <div class="pageindex__head">\n'
        '      <h2 class="h-label" id="idx-h">%s</h2>\n'
        '      <span class="pageindex__count">%d %s</span>\n'
        '      <input class="pageindex__search" type="search" placeholder="%s" aria-label="%s"'
        ' data-ph-en="%s" data-ph-ko="%s">\n'
        "    </div>\n"
        '    <ul class="pageindex__list">\n      %s\n    </ul>\n'
        '    <p class="pageindex__empty" hidden>%s</p>\n'
        "  </div>\n"
        "</nav>" % (ui("on_this_page"), len(profiles), ui("entries"),
                    html.escape(ui_raw("filter_ph", "en"), quote=True),
                    html.escape(ui_raw("filter_label", "en"), quote=True),
                    html.escape(ui_raw("filter_ph", "en"), quote=True),
                    html.escape(ui_raw("filter_ph", "ko"), quote=True),
                    rows, ui("filter_empty"))
    )


# -------------------------------------------------------------------- chrome --

def nav_html(current):
    def group(label, pages, key):
        gmap = I18N.get("grades", {})
        rows = []
        for name, slug in pages:
            n = re.match(r"(\d)", name)
            g = gmap.get(n.group(1)) if n else None
            ko = ("%s (%s)" % (g["ko_name"], g["ko_class"])) if g else name
            rows.append(
                '<li><a href="%s.html"%s>'
                '<span class="i18n" lang="en" data-en>%s</span>'
                '<span class="i18n" lang="ko" data-ko>%s</span></a></li>'
                % (slug, ' aria-current="page"' if slug == current else "",
                   html.escape(name), html.escape(ko))
            )
        rows = "\n          ".join(rows)
        label = ui("korean_activists") if key == "korean" else ui("foreign_activists")
        active = any(slug == current for _n, slug in pages)
        return (
            '<li class="nav__item" data-open="false">\n'
            '        <button class="nav__toggle" type="button" aria-expanded="false" aria-controls="menu-%s">'
            '%s<span class="nav__caret" aria-hidden="true"></span></button>\n'
            '        <ul class="nav__menu" id="menu-%s">\n          %s\n        </ul>\n'
            "      </li>" % (key, label, key, rows)
        ) if not active else (
            '<li class="nav__item" data-open="false">\n'
            '        <button class="nav__toggle" type="button" aria-expanded="false" aria-controls="menu-%s">'
            '%s<span class="nav__caret" aria-hidden="true"></span></button>\n'
            '        <ul class="nav__menu" id="menu-%s">\n          %s\n        </ul>\n'
            "      </li>" % (key, label, key, rows)
        )

    home_cur = ' aria-current="page"' if current == "index" else ""
    about_cur = ' aria-current="page"' if current == "about" else ""
    return (
        '<nav class="nav" id="sitenav" aria-label="Main">\n'
        '      <ul class="nav__list">\n'
        '        <li><a class="nav__link" href="index.html"%s>%s</a></li>\n'
        "        %s\n"
        "        %s\n"
        '        <li><a class="nav__link" href="about.html"%s>%s</a></li>\n'
        "      </ul>\n"
        "    </nav>"
        % (home_cur, ui("home"),
           group("KoreanActivists", KOREAN_PAGES, "korean"),
           group("ForeignActivists", FOREIGN_PAGES, "foreign"),
           about_cur, ui("about"))
    )


def footer_html(nodes):
    """Rebuild the shared GET IN TOUCH footer, keeping the original wording."""
    heads = [n for n in nodes if n["type"] in ("h1", "h2", "h3", "h4")]
    title = heads[0]["html"] if heads else "Get in Touch"
    labels, mark = [], []
    for n in heads[1:]:
        raw = n["html"]
        if "<br>" in raw:
            labels.extend(part for part in raw.split("<br>") if txt(part))
        elif txt(raw).lower() in ("email", "instagram"):
            labels.append(raw)
        else:
            mark.append(raw)
    if not labels:
        labels = ["Email", "INSTAGRAM"]
    email_label, insta_label = (labels + ["Email", "INSTAGRAM"])[:2]
    mark_lg = mark[0] if mark else "Korean"
    mark_sm = mark[1] if len(mark) > 1 else "Independent ACtivist"
    return (
        '<footer class="footer">\n'
        '  <div class="shell">\n'
        '    <div class="footer__top">\n'
        '      <h2 class="h-section">%s</h2>\n'
        "%s"
        '      <div class="footer__contact">\n'
        '        <a href="mailto:%s">%s <span>%s</span></a>\n'
        '        <a href="%s" target="_blank" rel="noopener">%s <span>%s</span></a>\n'
        "      </div>\n"
        "    </div>\n"
        "  </div>\n"
        '  <div class="footer__mark" aria-hidden="true">\n'
        '    <span class="mark-lg">%s</span>\n'
        '    <span class="mark-sm">%s</span>\n'
        "  </div>\n"
        '  <div class="shell">\n'
        '    <div class="footer__legal">\n'
        "      <p>&copy; %s</p>\n"
        "      <p>%s</p>\n"
        "    </div>\n"
        "  </div>\n"
        "</footer>" % (bi(title), "", EMAIL, bi(email_label), EMAIL,
                       INSTAGRAM, bi(insta_label), INSTAGRAM_HANDLE,
                       bi(mark_lg), bi(mark_sm), SITE_NAME, ui("footer_tagline"))
    )


SHELL = """<!DOCTYPE html>
<html lang="en" data-lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
{og_image}<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="styles.css">
</head>
<body data-menu="closed">
<a class="skip" href="#main">{t_skip}</a>

<header class="masthead">
  <div class="shell masthead__inner">
    <a class="wordmark" href="index.html">{site}</a>
    {nav}
    <div class="masthead__actions">
      <button class="langtoggle" type="button" data-lang-toggle
              aria-label="{t_lang_label}" title="{t_lang_label}">
        <span class="langtoggle__on">EN</span><span class="langtoggle__sep">/</span><span class="langtoggle__off" lang="ko">한국어</span>
      </button>
      <button class="burger" type="button" aria-label="{t_menu}" aria-expanded="false" aria-controls="sitenav">
        <span></span><span></span><span></span>
      </button>
    </div>
  </div>
</header>

<main id="main">
{body}
</main>

{footer}

<button class="totop" type="button" aria-label="{t_totop}">
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path d="M8 13V3M8 3L3.5 7.5M8 3l4.5 4.5" stroke="currentColor" stroke-width="1.8"
          stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
</button>

<script src="app.js" defer></script>
</body>
</html>
"""


def describe(sections):
    for sec in sections:
        for n in sec:
            if n["type"] == "p":
                t = txt(n["html"])
                if len(t) > 60:
                    return (t[:180] + "…") if len(t) > 180 else t
    for sec in sections:
        for n in sec:
            if n["type"] in ("h1", "h2", "h3"):
                return txt(n["html"])
    return "Commemorating the activists of the Korean independence movement."


def build_page(out, page, pages):
    sections = page["sections"]
    title = page["title"] or SITE_NAME
    body_parts = []
    profiles = []

    middle = sections[1:-1] if len(sections) > 2 else sections[1:]
    footer_nodes = sections[-1] if len(sections) > 1 else []

    if sections:
        body_parts.append(render_hero(sections[0], title))

    # first pass: find profiles so the on-page index can precede them
    rendered = []
    flip = False
    for sec in middle:
        has_img = any(n["type"] == "img" for n in sec)
        has_text = any(n["type"] in ("p", "h1", "h2", "h3", "h4", "list-item") for n in sec)
        if is_profile(sec):
            _img, name, _d, _r = split_profile(sec)
            label = txt(name["html"]).rstrip(" :") if name else "Entry"
            anchor = slugify(label)
            n = 2
            while any(a == anchor for a, _l in profiles):
                anchor = "%s-%d" % (slugify(label), n)
                n += 1
            profiles.append((anchor, label))
            rendered.append(render_profile(sec, anchor, (MATCHES.get(out) or {}).get(label)))
        elif has_img and not has_text:
            rendered.append(render_banner(sec))
        elif has_text:
            rendered.append(render_split(sec, flip))
            flip = not flip

    if profiles:
        # place the index right before the first profile block
        first = next(i for i, r in enumerate(rendered) if r.startswith('<article class="profile'))
        rendered.insert(first, render_index(profiles))

    body_parts.extend(r for r in rendered if r)

    cls = PAGE_CLASS.get(out)
    if cls:
        body_parts.append(render_roster(out, cls, [a for a, _l in profiles]))

    og = ""
    first_img = next((n["local"] for sec in sections for n in sec
                      if n["type"] == "img" and n.get("local")), None)
    if first_img:
        og = '<meta property="og:image" content="%s">\n' % first_img

    doc = SHELL.format(
        title=html.escape(title),
        desc=html.escape(describe(sections), quote=True),
        og_image=og,
        site=SITE_NAME,
        nav=nav_html(out),
        body="\n\n".join(body_parts),
        footer=footer_html(footer_nodes),
        t_skip=ui("skip"),
        t_menu=html.escape(ui_raw("menu", "en"), quote=True),
        t_totop=html.escape(ui_raw("back_to_top", "en"), quote=True),
        t_lang_label=html.escape(ui_raw("lang_label", "en"), quote=True),
    )
    with open(os.path.join(ROOT, out + ".html"), "w") as fh:
        fh.write(doc)
    return len(profiles)


def main():
    with open(os.path.join(DATA, "site.json")) as fh:
        pages = json.load(fh)
    load_side_data()
    global HREFS
    HREFS = build_href_map(pages)
    total = 0
    for out, page in pages.items():
        n = build_page(out, page, pages)
        total += n
        print("  %-24s %2d sections  %2d profiles" % (out + ".html", len(page["sections"]), n))
    print("\nbuilt %d pages, %d activist entries" % (len(pages), total))


if __name__ == "__main__":
    sys.exit(main())
