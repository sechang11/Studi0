#!/usr/bin/env python3
"""studio/_tools/guides.py - the guide library: index it, render it, link to it.

    python3 studio/_tools/guides.py                 list every guide and its route
    python3 studio/_tools/guides.py --check         validate links and page coverage
    python3 studio/_tools/guides.py --json          the index serve.py serves
    python3 studio/_tools/guides.py --render wizard the rendered HTML for one guide

WHY THIS EXISTS. Somebody asked whether the app is beginner friendly and whether there
are guides for each section. There were none. Every page in this studio assumes you
already know that a shot is a stack of layers, that style picks the engine, and that a
look is an ffmpeg grade rather than prompt text - none of which is guessable from the
screen. The guides are markdown in studio/guides/; this module is the only thing that
reads them.

THREE RULES THIS FILE OBEYS, EACH PAID FOR ELSEWHERE IN THIS REPO:

  1. NOTHING RUNS AT IMPORT, AND NOTHING RUNS ON --help. 17 of the 60 tools in this
     directory have no argparse and do their entire job when handed any argument,
     including --help; ten of them write files at module level. Probing them destroyed
     ten style cards. So: argparse first, no module-level work, and this file never
     writes anything anywhere. It is read-only over studio/guides/ by construction.

  2. THE MARKDOWN IS ESCAPED BEFORE IT IS FORMATTED. The guides quote card verdicts and
     error strings verbatim, and those contain angle brackets and quotes. Escaping after
     formatting would eat the tags this module just wrote; escaping before means a stray
     `<script>` in a guide is text, not script.

  3. THE PAGE LINK IS INJECTED, NOT EDITED IN. The nav lives in ten hand-written HTML
     files owned by other work, and serve.py already injects /video and /dossier links
     the same way for the same reason. page_link() below is conservative: if it does not
     recognise the nav it returns the document byte for byte unchanged. A guide link is
     not worth corrupting somebody else's page for.
"""
import argparse, html as _html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
GUIDES = os.path.join(STUDIO, "guides")

# The reading order. Ordering by filename would put capabilities first and getting-started
# fourth, which is exactly backwards for the person this is written for.
ORDER = ["getting-started", "mental-model", "wizard", "styles", "places", "cast",
         "loras", "motions", "video", "make", "gallery", "verify", "capabilities"]

# What each guide is, in one line, for the index page. Kept here rather than parsed out of
# the markdown because the first paragraph of a guide is written for somebody already
# reading it, and an index needs a different sentence.
BLURB = {
    "getting-started": "The shortest route from opening the app to a finished thing.",
    "mental-model":    "The five ideas nobody can guess and everything depends on.",
    "wizard":          "Eight steps from an empty stack to a rendered scene.",
    "styles":          "130 cards, and the field on each one that picks the engine.",
    "places":          "64 settings, each described twice because the engines read "
                       "different languages.",
    "cast":            "Characters that survive being in more than one scene.",
    "loras":           "Trained weights, and the one thing they do that no prompt can.",
    "motions":         "The one string the video model reads.",
    "video":           "375 clips, and what survives the motion pass.",
    "make":            "The five makers that are not films. The fastest way to get "
                       "anything out of the box.",
    "gallery":         "1828 generations, each carrying the recipe that produced it.",
    "verify":          "The human quality gate. Can you tell these apart?",
    "capabilities":    "Everything the box can do, including the 19 things the app does "
                       "not expose.",
}

# Which guide belongs to which page. The key is the HTML filename serve.py opens, so this
# table is matched against what _page() already has in hand and needs no route parsing.
#
# HAND-AUTHORED JUDGEMENT, not a derived fact. Two calls worth stating: /tags maps to the
# motions guide because motions are the tag family that actually changes a render and the
# guide covers the rest of the page in its last section; /character maps to the cast guide
# because a dossier is one cast member and splitting them would mean writing the reference
# sheet rule twice.
PAGE = {
    "app.html":        "getting-started",
    "wizard.html":     "wizard",
    "styles.html":     "styles",
    "places.html":     "places",
    "cast.html":       "cast",
    "character.html":  "cast",
    "loras.html":      "loras",
    "tags.html":       "motions",
    "video.html":      "video",
    "make.html":       "make",
    "gallery.html":    "gallery",
    "verify.html":     "verify",
    # Mapped ahead of the file existing. /capabilities is being built in a parallel wave;
    # PAGE is consulted by filename inside _page(), so the link starts working the moment
    # that page lands and nobody has to remember to come back here. --check reports it as
    # pending rather than broken for exactly that reason.
    "capabilities.html": "capabilities",
}


# ---------------------------------------------------------------------------
# reading
# ---------------------------------------------------------------------------

def slugs():
    """Every guide on disk, in reading order, with anything unlisted appended.

    Appending rather than dropping is deliberate: a guide somebody adds later should
    show up in the index without having to also edit ORDER, and showing it in the wrong
    place is a much smaller failure than not showing it at all.
    """
    if not os.path.isdir(GUIDES):
        return []
    have = {f[:-3] for f in os.listdir(GUIDES) if f.endswith(".md")}
    out = [s for s in ORDER if s in have]
    return out + sorted(have - set(out))


def read(slug):
    """The raw markdown for one guide, or None. Slug is used to build a path, so it is
    restricted to what a slug can be rather than trusted."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", str(slug or "")):
        return None
    p = os.path.join(GUIDES, slug + ".md")
    if not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8") as f:
        return f.read()


def title(slug, text=None):
    """The guide's own H1, which is the only title that can go stale in one place."""
    text = read(slug) if text is None else text
    for line in (text or "").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return slug.replace("-", " ")


def index():
    out = []
    for s in slugs():
        t = read(s)
        out.append({"slug": s, "title": title(s, t), "blurb": BLURB.get(s, ""),
                    "url": "/guide/" + s, "words": len((t or "").split())})
    return {"guides": out, "pages": PAGE}


# ---------------------------------------------------------------------------
# markdown -> html
#
# A deliberately small subset: headings, paragraphs, lists, tables, fenced code,
# blockquotes, hr, and inline em/strong/code/link. That is everything the guides use and
# nothing else, because every construct supported is a construct that can be got wrong.
# ---------------------------------------------------------------------------

_INLINE = [
    (re.compile(r"`([^`]+)`"),                     r"<code>\1</code>"),
    (re.compile(r"\*\*([^*]+)\*\*"),               r"<strong>\1</strong>"),
    (re.compile(r"(?<![*\w])\*([^*\n]+)\*(?!\*)"), r"<em>\1</em>"),
    # Links last: the label may contain the inline forms above, and the URL must not be
    # touched by them at all.
    (re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)"),     r'<a href="\2">\1</a>'),
]


def _inline(s):
    s = _html.escape(s, quote=False)
    for rx, rep in _INLINE:
        s = rx.sub(rep, s)
    return s


def _sub(items):
    """A nested bullet list inside a list item, or nothing."""
    if not items:
        return ""
    return "<ul>%s</ul>" % "".join("<li>%s</li>" % _inline(x) for x in items)


def _cells(row):
    return [c.strip() for c in row.strip().strip("|").split("|")]


def _is_rule(row):
    return bool(re.fullmatch(r"\|?[\s:|-]+\|?", row)) and "-" in row


def render(md):
    """Markdown subset -> HTML. Never returns None; an empty guide renders as nothing."""
    lines = (md or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        ln = lines[i]

        # fenced code - taken verbatim, escaped, no inline formatting inside
        if ln.startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>%s</code></pre>"
                       % _html.escape("\n".join(buf), quote=False))
            continue

        if not ln.strip():
            i += 1
            continue

        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", ln.strip()):
            out.append("<hr>")
            i += 1
            continue

        m = re.match(r"(#{1,6})\s+(.*)", ln)
        if m:
            lvl = len(m.group(1))
            out.append("<h%d>%s</h%d>" % (lvl, _inline(m.group(2)), lvl))
            i += 1
            continue

        # table: a header row, a rule, then body rows
        if ln.lstrip().startswith("|") and i + 1 < n and _is_rule(lines[i + 1]):
            head = _cells(ln)
            i += 2
            body = []
            while i < n and lines[i].lstrip().startswith("|"):
                body.append(_cells(lines[i]))
                i += 1
            # Wrapped, because a five-column table on a phone must scroll inside itself
            # rather than making the whole page scroll sideways.
            t = ["<div class='tw'><table><thead><tr>"]
            t += ["<th>%s</th>" % _inline(c) for c in head]
            t.append("</tr></thead><tbody>")
            for r in body:
                t.append("<tr>" + "".join("<td>%s</td>" % _inline(c) for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t))
            continue

        if ln.lstrip().startswith(">"):
            buf = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(lines[i].lstrip()[1:].strip())
                i += 1
            out.append("<blockquote>%s</blockquote>" % _inline(" ".join(buf)))
            continue

        m = re.match(r"\s*(\d+)\.\s+(.*)", ln)
        if m:
            # Items are (text, [nested bullets]). The nesting is not decoration: a wizard
            # step whose sub-choices got folded into its own sentence rendered as
            # "Bands are stacked in containment order. - Open the Style band and pick
            # one. - Open Place..." - one run-on paragraph with stray hyphens in it. That
            # was found by screenshotting the page and reading it, which is the only way
            # this class of bug is ever found.
            start, items = m.group(1), []
            while i < n:
                mm = re.match(r"\s*\d+\.\s+(.*)", lines[i])
                if mm:
                    items.append([mm.group(1), []])
                    i += 1
                    continue
                if not items or not lines[i].strip():
                    break
                sub = re.match(r"\s{2,}[-*]\s+(.*)", lines[i])
                if sub:                                   # an indented bullet: nest it
                    items[-1][1].append(sub.group(1))
                    i += 1
                elif lines[i].startswith("   "):          # a wrapped line of the item
                    if items[-1][1]:                      # ...or of its last bullet
                        items[-1][1][-1] += " " + lines[i].strip()
                    else:
                        items[-1][0] += " " + lines[i].strip()
                    i += 1
                else:
                    break
            body = "".join(
                "<li>%s%s</li>" % (_inline(t), _sub(subs)) for t, subs in items)
            out.append("<ol start='%s'>%s</ol>" % (start, body))
            continue

        if re.match(r"\s*[-*]\s+", ln):
            indent = len(ln) - len(ln.lstrip())
            items = []
            while i < n:
                mm = re.match(r"(\s*)[-*]\s+(.*)", lines[i])
                if mm and len(mm.group(1)) <= indent:
                    items.append([mm.group(2), []])
                    i += 1
                    continue
                if not items or not lines[i].strip():
                    break
                if mm:                                    # a deeper bullet: nest it
                    items[-1][1].append(mm.group(2))
                    i += 1
                elif lines[i].startswith(" " * (indent + 2)):
                    if items[-1][1]:
                        items[-1][1][-1] += " " + lines[i].strip()
                    else:
                        items[-1][0] += " " + lines[i].strip()
                    i += 1
                else:
                    break
            out.append("<ul>%s</ul>" % "".join(
                "<li>%s%s</li>" % (_inline(t), _sub(subs)) for t, subs in items))
            continue

        # paragraph: run on until a blank line or something that starts a new block
        buf = []
        while i < n and lines[i].strip() and not re.match(
                r"\s*([-*]\s|\d+\.\s|#{1,6}\s|>|```|\|)", lines[i]):
            buf.append(lines[i].strip())
            i += 1
        if buf:
            out.append("<p>%s</p>" % _inline(" ".join(buf)))
        else:
            i += 1
    return "\n".join(out)


def payload(slug):
    """What /api/guide/<slug> answers."""
    md = read(slug)
    if md is None:
        return None
    ss = slugs()
    j = ss.index(slug) if slug in ss else -1
    nav = lambda k: ({"slug": ss[k], "title": title(ss[k])}
                     if 0 <= k < len(ss) else None)
    return {"slug": slug, "title": title(slug, md), "blurb": BLURB.get(slug, ""),
            "html": render(md), "prev": nav(j - 1) if j > 0 else None,
            "next": nav(j + 1) if j >= 0 else None}


# ---------------------------------------------------------------------------
# the page link
# ---------------------------------------------------------------------------

# Matches the nav container every page in this studio uses - <div class="right"> or
# <span class="right"> - plus the wizard, which uses an inline margin-left:auto span
# instead of the class. Anchored on the opening tag so the link lands as the FIRST item
# in the nav, where a "how does this work" affordance belongs.
_NAV = [re.compile(r'<(div|span)\s+class="right"\s*>'),
        re.compile(r'<span\s+style="margin-left:auto;display:flex;gap:8px"\s*>')]

_LINK = ('<a href="/guide/%s" title="a plain-language guide to this page: what it is '
         'for, what to do first, and what will confuse you">%s</a>')


def page_link(html, page):
    """Inject a `How this page works` link into one page's nav. Returns html unchanged if
    the page has no guide, already links to one, or has a nav this does not recognise."""
    slug = PAGE.get(page)
    if not slug or "/guide/" in html:
        return html
    for rx in _NAV:
        m = rx.search(html)
        if not m:
            continue
        # Match the neighbour's case so `How this page works` does not sit in a nav of
        # lowercase words, the same contract serve.py's nav_video works under.
        nxt = re.search(r'<a [^>]*>\s*([A-Za-z])', html[m.end():m.end() + 400])
        word = ("How this page works" if (nxt and nxt.group(1).isupper())
                else "how this page works")
        return html[:m.end()] + (_LINK % (slug, word)) + html[m.end():]
    return html


# ---------------------------------------------------------------------------
# cli - the only thing that does anything, and it only ever reads
# ---------------------------------------------------------------------------

def _check():
    """Validate the library against itself and against the pages. Read-only."""
    bad = 0
    ss = slugs()
    print("%d guides in %s" % (len(ss), GUIDES))

    for s in ORDER:
        if s not in ss:
            print("  MISSING  %s.md is in ORDER but not on disk" % s)
            bad += 1
    for s in ss:
        if s not in BLURB:
            print("  NOTE     %s has no index blurb" % s)

    # every /guide/<x> link in every guide must resolve
    for s in ss:
        md = read(s) or ""
        for target in re.findall(r"\]\(/guide/([a-z0-9-]+)", md):
            if target not in ss:
                print("  BROKEN   %s links to /guide/%s, which does not exist"
                      % (s, target))
                bad += 1
        if not md.startswith("# "):
            print("  WRONG    %s.md does not open with an H1" % s)
            bad += 1

    # every page named in PAGE must exist, and must accept the link
    for page, slug in sorted(PAGE.items()):
        p = os.path.join(STUDIO, page)
        if not os.path.isfile(p):
            # Not a failure. A guide may be mapped to a page another wave has not landed
            # yet, and the mapping is what makes the link appear the moment it does.
            print("  PENDING  %s is mapped to %s.md but is not on disk yet" % (page, slug))
            continue
        if slug not in ss:
            print("  BROKEN   %s maps to %s.md, which does not exist" % (page, slug))
            bad += 1
            continue
        with open(p, encoding="utf-8") as f:
            src = f.read()
        if page_link(src, page) == src:
            print("  WRONG    %s has a nav this cannot recognise - no link injected"
                  % page)
            bad += 1

    # pages with no guide at all, reported rather than assumed acceptable
    pages = sorted(f for f in os.listdir(STUDIO)
                   if f.endswith(".html") and f not in PAGE)
    if pages:
        print("  NOTE     no guide mapped: %s" % ", ".join(pages))

    print("OK" if not bad else "%d problem(s)" % bad)
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="print the guide index as JSON")
    ap.add_argument("--render", metavar="SLUG", help="print one guide as HTML")
    ap.add_argument("--check", action="store_true",
                    help="validate links, titles and page coverage; exit 1 on a problem")
    a = ap.parse_args()

    if a.check:
        return _check()
    if a.render:
        p = payload(a.render)
        if not p:
            sys.exit("no such guide: %s" % a.render)
        print(p["html"])
        return 0
    if a.json:
        print(json.dumps(index(), indent=1))
        return 0
    for g in index()["guides"]:
        print("%-16s %-34s %5d words  %s"
              % (g["slug"], g["title"], g["words"], g["url"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
