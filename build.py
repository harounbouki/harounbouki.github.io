#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مولّد الموقع — يحوّل ملفات content/ إلى موقع ثابت في dist/

    python3 build.py            يبني الموقع للنشر
    python3 build.py --local    نسخة للمعاينة من القرص (روابط تنتهي بـ index.html)
    python3 build.py --og       يجهّز بطاقات المشاركة في .og/ (تُصوَّر بعدها بـ tools/og.mjs)

لا يحتاج أي مكتبة خارجية.
"""
import html
import json
import random
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
THEME = ROOT / "theme"
ASSETS = ROOT / "assets"
LOCAL = "--local" in sys.argv
OG = "--og" in sys.argv
DIST = ROOT / ("dist-local" if LOCAL else "dist")

MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
          "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
AGES = {30: "الثلاثين", 31: "الحادية والثلاثين", 32: "الثانية والثلاثين", 33: "الثالثة والثلاثين",
        34: "الرابعة والثلاثين", 35: "الخامسة والثلاثين", 36: "السادسة والثلاثين",
        37: "السابعة والثلاثين", 38: "الثامنة والثلاثين", 39: "التاسعة والثلاثين"}
PALETTES = {"cream": "#F6EDE3", "burgundy": "#6D1F2C", "ink": "#1F2421"}

esc = html.escape


# ————————————————— أدوات —————————————————

def href(root, path=""):
    target = root + path
    if LOCAL:
        target += "index.html"
    return target or "./"


def ar_date(d):
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def plural(n, one, two, few, many):
    if n == 1:
        return one
    if n == 2:
        return two
    if 3 <= n <= 10:
        return f"{n} {few}"
    return f"{n} {many}"


def reading_time(text):
    n = max(1, round(len(re.findall(r"\S+", text)) / 200))
    return plural(n, "دقيقة قراءة", "دقيقتا قراءة", "دقائق قراءة", "دقيقة قراءة")


def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def parse_front_matter(raw):
    meta, body = {}, raw
    m = re.match(r"^﻿?---\s*\n(.*?)\n---\s*\n?(.*)$", raw, re.S)
    if m:
        body = m.group(2)
        for line in m.group(1).splitlines():
            if ":" in line and not line.strip().startswith("#"):
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, body


# ————————————————— Markdown → HTML —————————————————

LINK_ROOT = ""      # جذر الصفحة الجارية، ليصحّ الرابط الداخلي المكتوب في Markdown مثل (notes/)


def link(m):
    url = m.group(2)
    if url.startswith("http"):
        return f'<a href="{url}" target="_blank" rel="noopener">{m.group(1)}</a>'
    if not re.match(r"^(#|/|mailto:|\.\.?/)", url):
        url = LINK_ROOT + url + ("index.html" if LOCAL and url.endswith("/") else "")
    return f'<a href="{url}">{m.group(1)}</a>'


def inline(text):
    text = esc(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])", r"<em>\1</em>", text)
    return text


def picture(src, alt="", cls="duo"):
    """كل صور الموقع تمرّ من هنا لتأخذ المعالجة الموحّدة (صبغة عنابية وحبيبات)."""
    return f'<span class="{cls}"><img src="{esc(src)}" alt="{esc(alt)}" loading="lazy"></span>'


def markdown(src, root=""):
    global LINK_ROOT
    LINK_ROOT = root
    lines = src.replace("\r\n", "\n").split("\n")
    out, i, n = [], 0, len(lines)

    def is_block_start(s):
        return bool(re.match(r"^(#{1,4} |>|[-*+] |\d+[.)] |```|!\[|(-{3,}|\*{3,})\s*$)", s))

    while i < n:
        s = lines[i].strip()
        if not s:
            i += 1
            continue

        if s.startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + esc("\n".join(buf)) + "</code></pre>")
            continue

        if re.match(r"^(-{3,}|\*{3,})$", s):
            out.append("<hr>")
            i += 1
            continue

        m = re.match(r"^(#{1,4}) (.+)$", s)
        if m:
            level = min(len(m.group(1)) + 1, 4)
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            i += 1
            continue

        m = re.match(r'^!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)$', s)
        if m:
            alt, src_, cap = m.group(1), m.group(2), m.group(3)
            if not re.match(r"^(https?:)?//", src_) and not src_.startswith("/"):
                src_ = root + src_
            fig = "<figure>" + picture(src_, alt)
            if cap:
                fig += f"<figcaption>{inline(cap)}</figcaption>"
            out.append(fig + "</figure>")
            i += 1
            continue

        if s.startswith(">>"):
            buf = []
            while i < n and lines[i].strip().startswith(">>"):
                buf.append(lines[i].strip()[2:].strip())
                i += 1
            out.append('<p class="pullquote">' + inline(" ".join(buf)) + "</p>")
            continue

        if s.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^>\s?", "", lines[i].strip()))
                i += 1
            paras = [p for p in re.split(r"\n\s*\n", "\n".join(buf)) if p.strip()]
            out.append("<blockquote>" + "".join(
                f"<p>{inline(' '.join(p.split()))}</p>" for p in paras) + "</blockquote>")
            continue

        m = re.match(r"^([-*+]|\d+[.)]) ", s)
        if m:
            ordered = m.group(1)[0].isdigit()
            pat = r"^\d+[.)] " if ordered else r"^[-*+] "
            items = []
            while i < n and re.match(pat, lines[i].strip()):
                items.append(re.sub(pat, "", lines[i].strip()))
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
            continue

        buf = [s]
        i += 1
        while i < n and lines[i].strip() and not is_block_start(lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        out.append("<p>" + inline(" ".join(buf)) + "</p>")

    return "\n".join(out)


# ————————————————— عناصر الهوية —————————————————

def pen_pattern(cls="hero__pattern", W=1440, H=820, seed=30):
    """خطوط قلم رفيعة غير منتظمة على شبكة (القسم 5 من دليل الهوية). ثابتة في كل بناء."""
    rnd = random.Random(seed)
    paths, one_done, y = [], False, 40
    while y < H:
        x = rnd.uniform(-40, 60)
        while x < W:
            seg = rnd.uniform(40, 210)
            if rnd.random() < 0.72:
                x2 = min(x + seg, W)
                c = ""
                if not one_done and y > H * 0.55 and x < W * 0.35 and seg > 140:
                    c, one_done = ' class="one"', True
                paths.append(f'<path{c} d="M{x:.0f} {y + rnd.uniform(-2, 2):.1f} '
                             f'Q{(x + x2) / 2:.0f} {y + rnd.uniform(-3.5, 3.5):.1f} {x2:.0f} {y + rnd.uniform(-2, 2):.1f}"/>')
            x += seg + rnd.uniform(14, 70)
        y += 46 + rnd.uniform(-6, 6)
    return (f'<svg class="{cls}" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" '
            f'aria-hidden="true">{"".join(paths)}</svg>')


def current_age(site, today=None):
    raw = str(site.get("thirtieth_birthday", "")).strip()
    m = re.match(r"^(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?$", raw)
    if not m:
        return None
    b = date(int(m.group(1)), int(m.group(2) or 1), int(m.group(3) or 1))
    t = today or date.today()
    return 30 + t.year - b.year - ((t.month, t.day) < (b.month, b.day))


def hero_visual(site, posts, root, notes=()):
    """العنصر البصري في الجهة الفارغة من الهيرو. يُختار من site.json → hero.visual"""
    kind = site["hero"].get("visual", "age")
    if kind == "age":
        age = current_age(site)
        if not age:
            return ""
        label = f"في {AGES[age]}" if age in AGES else ""
        chs, _ = chapters(site, posts)
        cnt = next((len(c["posts"]) for c in chs if c["key"] == age), 0)
        count = plural(cnt, "تدوينة واحدة", "تدوينتان", "تدوينات", "تدوينة") if cnt else "لم يُكتب فيه شيء بعد"
        return f"""<a class="hero__visual age" href="{href(root, 'archive/')}" aria-label="الفصل الحالي: {esc(label)}">
      <span class="age__label">الفصل الحالي</span>
      <span class="age__num" dir="ltr">{age}</span>
      <span class="age__cap"><b>{esc(label)}</b> · {count}</span>
    </a>"""
    if kind == "photo" and site["hero"].get("photo"):
        return f'<div class="hero__visual portrait">{picture(root + site["hero"]["photo"], site["author"])}</div>'
    if kind == "sketch" and site["hero"].get("sketch"):
        return (f'<div class="hero__visual sketchp" data-motion="ink"><img src="{root}{esc(site["hero"]["sketch"])}" '
                f'alt="رسم لصاحب المدونة {esc(site["author"])}"></div>'
                f'<script src="{root}assets/js/portrait.js" defer></script>')
    if kind == "notes" and notes:
        slips = ""
        for i, n in enumerate(list(notes)[:3], 1):
            text = re.sub(r"<[^>]+>", "", n["html"]).strip()
            slips += (f'<a class="slip slip--{i}" href="{href(root, "notes/")}#n-{n["num"]:03d}">'
                      f'<span class="slip__num" dir="ltr">{n["num"]:03d}</span>'
                      f'<span class="slip__text">{esc(text)}</span></a>')
        return f'<div class="hero__visual stack" aria-label="آخر سطور الدفتر">{slips}</div>'
    if kind == "decade":
        age = current_age(site)
        if not age:
            return ""
        cells = "".join(f'<i class="{"past" if a < age else "now" if a == age else ""}">{a}</i>' for a in range(30, 40))
        cap = f"أنا الآن في {AGES[age]}" if age in AGES else ""
        return f"""<a class="hero__visual decade" href="{href(root, 'archive/')}" aria-label="سنوات الثلاثين: {esc(cap)}">
      <span class="age__label">سنوات الثلاثين</span>
      <span class="decade__grid" dir="ltr">{cells}</span>
      <span class="age__cap"><b>{esc(cap)}</b></span>
    </a>"""
    if kind == "pen":
        return """<div class="hero__visual pen" aria-hidden="true">
      <svg viewBox="0 0 520 420">
        <path class="pen__ink" pathLength="1" d="M505 302 C478 290 458 318 430 302 S384 272 362 300 S318 334 292 304 C276 284 258 288 250 302 S214 318 196 306 C182 296 168 300 158 304"/>
        <g transform="translate(156 304) rotate(35)">
          <path class="pen__body" pathLength="1" d="M0 0 C-10 -50 -55 -100 -62 -160 L-62 -200 L62 -200 L62 -160 C55 -100 10 -50 0 0 Z"/>
          <path class="pen__collar" pathLength="1" d="M-66 -200 H66 V-234 H-66 Z"/>
          <path class="pen__slit" pathLength="1" d="M0 -4 L0 -118"/>
          <circle class="pen__hole" pathLength="1" cx="0" cy="-128" r="9"/>
        </g>
      </svg>
    </div>"""
    return ""


LOGO = ('<svg class="brand__mark" viewBox="0 0 120 110" aria-hidden="true">'
        '<path class="m1" d="M8 50 C8 116, 112 116, 112 40 L93 40 C93 84, 27 84, 27 50 Z"/>'
        '<path class="m2" d="M60 8 L74 22 L60 36 L46 22 Z"/></svg>')
ENDMARK = ('<p class="endmark" aria-hidden="true"><svg viewBox="0 0 28 28">'
           '<path d="M14 2 L26 14 L14 26 L2 14 Z"/></svg></p>')
MENU_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
             'stroke-linecap="round" aria-hidden="true"><path d="M4 8h16M4 16h16"/></svg>')

BOOT = "<script>document.documentElement.classList.add('js');</script>"

SITE_JS = r"""<script>
(function () {
  var burger = document.getElementById('menuBtn');
  if (burger) burger.addEventListener('click', function () {
    var open = document.body.dataset.menu === 'open';
    if (open) { delete document.body.dataset.menu; } else { document.body.dataset.menu = 'open'; }
    burger.setAttribute('aria-expanded', String(!open));
  });

  var still = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var jobs = [];

  // الكلمات التي تُكتب مع النزول
  var blocks = [].slice.call(document.querySelectorAll('[data-reveal]'));
  if (blocks.length && !still) {
    var groups = [];
    blocks.forEach(function (el) {
      var words = el.textContent.trim().split(/\s+/);
      el.textContent = '';
      words.forEach(function (w, i) {
        var s = document.createElement('span');
        s.className = 'w';
        s.textContent = w;
        el.appendChild(s);
        if (i < words.length - 1) el.appendChild(document.createTextNode(' '));
      });
      var g = groups.filter(function (x) { return x.parent === el.parentNode; })[0];
      if (!g) { g = { parent: el.parentNode, els: [], words: [] }; groups.push(g); }
      g.els.push(el);
      g.words = g.words.concat([].slice.call(el.children));
    });
    jobs.push(function () {
      var vh = window.innerHeight, start = vh * 0.82, end = vh * 0.45;
      groups.forEach(function (g) {
        var top = g.els[0].getBoundingClientRect().top;
        var bottom = g.els[g.els.length - 1].getBoundingClientRect().bottom;
        var p = Math.max(0, Math.min(1, (start - top) / (bottom - top + start - end)));
        var n = Math.round(p * g.words.length);
        g.words.forEach(function (s, i) {
          s.classList.toggle('on', i < n);
          s.classList.toggle('cur', i === n - 1 && n < g.words.length);
        });
      });
    });
  }

  // خط التقدّم في صفحة التدوينة
  var bar = document.getElementById('progress'), body = document.getElementById('reading');
  if (bar && body) jobs.push(function () {
    var r = body.getBoundingClientRect(), vh = window.innerHeight;
    var p = Math.max(0, Math.min(1, (vh * 0.5 - r.top) / Math.max(1, r.height)));
    bar.style.transform = 'scaleX(' + p + ')';
  });

  if (jobs.length) {
    var ticking = false;
    var run = function () { ticking = false; jobs.forEach(function (f) { f(); }); };
    var req = function () { if (!ticking) { ticking = true; requestAnimationFrame(run); } };
    window.addEventListener('scroll', req, { passive: true });
    window.addEventListener('resize', req);
    run();
  }

  var form = document.getElementById('subForm');
  if (form) form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    var note = document.getElementById('subNote');
    fetch(form.action, { method: 'POST', body: new FormData(form), mode: 'no-cors' })
      .then(function () { form.reset(); note.textContent = form.dataset.ok; note.className = 'form__note form__ok'; })
      .catch(function () { note.textContent = form.dataset.fail; });
  });
})();
</script>"""


# ————————————————— القالب العام —————————————————

def news_on(site):
    return bool(site.get("newsletter", {}).get("enabled"))


def nav_items(site):
    items = [("", "الرئيسية", "home"),
             ("archive/", "سنوات الثلاثين" if site.get("thirtieth_birthday") else "الأرشيف", "archive"),
             ("notes/", "الدفتر", "notes"),
             ("now/", "الآن", "now"),
             ("about/", "عني", "about")]
    if news_on(site):
        items.append(("subscribe/", site["newsletter"].get("nav_label", "اشترك"), "subscribe"))
    return items


def base_url(site):
    return site["url"].rstrip("/") + "/" if site.get("url") else ""


def page(site, root, title, description, body, current="", og_type="website", path="", og_image="", extra=""):
    nav = nav_items(site)
    links = "\n        ".join(
        f'<a class="nav__link" href="{href(root, p)}"'
        + (' aria-current="page"' if key == current else "") + f">{label}</a>"
        for p, label, key in nav)
    foot_links = "\n          ".join(f'<a href="{href(root, p)}">{label}</a>' for p, label, _ in nav)
    base = base_url(site)
    head = ""
    for fam, w in (("thmanyah-serif-display", "Regular"), ("thmanyah-serif-text", "Regular")):
        f = f"assets/fonts/{fam}/woff2/{fam}-{w}.woff2"
        if (ROOT / f).exists() and not LOCAL:      # المعاينة من القرص لا تدعم التحميل المسبق
            head += f'<link rel="preload" href="{root}{f}" as="font" type="font/woff2" crossorigin>\n'
    if base:
        head += f'<link rel="canonical" href="{base}{path}">\n'
        head += f'<meta property="og:url" content="{base}{path}">\n'
        img = og_image if (ROOT / og_image).exists() and og_image else "assets/og/default.png"
        if (ROOT / img).exists():
            head += (f'<meta property="og:image" content="{base}{img}">\n'
                     '<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n'
                     '<meta name="twitter:card" content="summary_large_image">\n')
        head += (f'<link rel="alternate" type="application/rss+xml" title="{esc(site["title"])}" '
                 f'href="{base}feed.xml">\n')
        foot_links += f'\n          <a href="{base}feed.xml">خلاصة RSS</a>'
    full_title = title if title == site["title"] else f'{title} | {site["title"]}'
    palette = site.get("palette", "cream")
    img_mode = "" if site.get("image_treatment", True) else ' data-img="raw"'
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl" data-palette="{esc(palette)}"{img_mode}>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(description)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{esc(site["title"])}">
<meta name="theme-color" content="{PALETTES.get(palette, "#F6EDE3")}">
<link rel="icon" href="{root}assets/favicon.svg" type="image/svg+xml">
{head}<link rel="stylesheet" href="{root}assets/css/style.css">
{BOOT}
{site.get("analytics_snippet", "")}
</head>
<body>
{extra}<header class="nav">
  <div class="wrap nav__in">
    <a class="brand" href="{href(root)}">{LOGO}<span>{esc(site["title"])}</span></a>
    <nav class="nav__links" aria-label="التنقل الرئيسي">
        {links}
    </nav>
    <button class="icon-btn nav__burger" id="menuBtn" type="button" aria-label="القائمة" aria-expanded="false">{MENU_ICON}</button>
  </div>
</header>

<main>
{body}
</main>

<footer class="footer">
  <div class="wrap">
    <div class="footer__grid">
      <div>
        <p class="footer__name">{esc(site["title"])}</p>
        <p class="footer__about">{esc(site["description"])}</p>
      </div>
      <div>
        <p class="footer__h">تصفّح</p>
        <div class="footer__list">
          {foot_links}
        </div>
      </div>
    </div>
    <div class="footer__bottom meta">
      <span>© {date.today().year} {esc(site["author"])}</span>
      <span>{esc(site.get("footer_note", ""))}</span>
    </div>
  </div>
</footer>
{SITE_JS}
</body>
</html>
"""


def page_head(title, intro="", meta=""):
    intro = f"<p>{esc(intro)}</p>" if intro else ""
    meta = f'<p class="meta page-head__meta">{meta}</p>' if meta else ""
    return f"""<header class="page-head">
    {meta}
    <h1>{esc(title)}</h1>
    {intro}
  </header>"""


def newsletter_block(site, heading=True):
    if not news_on(site):
        return ""
    n = site["newsletter"]
    if n.get("form_action"):
        action = (f'<form class="form" id="subForm" action="{esc(n["form_action"])}" method="post" '
                  f'data-ok="{esc(n.get("success", ""))}" data-fail="تعذّر الإرسال. جرّب مرة أخرى.">'
                  f'<label class="sr" for="subEmail">بريدك الإلكتروني</label>'
                  f'<input id="subEmail" type="email" name="{esc(n.get("form_field", "email"))}" '
                  f'placeholder="بريدك الإلكتروني" required dir="ltr">'
                  f'<button class="btn" type="submit">{esc(n["button"])}</button>'
                  f'<p class="form__note" id="subNote">{esc(n.get("note", ""))}</p></form>')
    elif n.get("url"):
        action = (f'<div class="form"><a class="btn" href="{esc(n["url"])}" target="_blank" rel="noopener">'
                  f'{esc(n["button"])}</a><p class="form__note">{esc(n.get("note", ""))}</p></div>')
    else:
        return ""
    title = f'<h2 class="news__title">{esc(n["title"])}</h2>' if heading else ""
    return f"""<div class="news">
      {title}
      <p class="news__body">{esc(n["body"])}</p>
      {action}
    </div>"""


def post_meta(p):
    topic = f'<span class="topic">{esc(p["topic"])}</span> · ' if p["topic"] else ""
    return f'{topic}<time datetime="{p["date"].isoformat()}">{ar_date(p["date"])}</time> · {p["reading"]}'


def post_row(p, root):
    return f"""<a class="post-row" href="{href(root, 'post/' + p['slug'] + '/')}">
        <span class="post-row__num" dir="ltr">{p['num']:03d}</span>
        <span>
          <h3 class="post-row__title">{esc(p['title'])}</h3>
          <p class="post-row__excerpt">{esc(p['excerpt'])}</p>
          <p class="meta">{post_meta(p)}</p>
        </span>
      </a>"""


def note_card(n, root, link=False):
    num = f'<span class="note__num" dir="ltr">{n["num"]:03d}</span>'
    if link:
        num = f'<a class="note__num" dir="ltr" href="{href(root, "notes/")}#n-{n["num"]:03d}">{n["num"]:03d}</a>'
    return f"""<article class="note" id="n-{n['num']:03d}">
        {num}
        <div class="note__body">{n['html']}</div>
        <p class="meta"><time datetime="{n['date'].isoformat()}">{ar_date(n['date'])}</time></p>
      </article>"""


# ————————————————— قراءة المحتوى —————————————————

def load_posts():
    posts = []
    for f in sorted((CONTENT / "posts").glob("*.md")):
        meta, body = parse_front_matter(f.read_text(encoding="utf-8"))
        if meta.get("draft", "").lower() in ("true", "yes", "1"):
            continue
        m = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)$", f.stem)
        d = meta.get("date") or (m.group(1) if m else None)
        if not d:
            sys.exit(f"✗ لا يوجد تاريخ في: {f.name} — أضف date: YYYY-MM-DD أو ابدأ اسم الملف بالتاريخ")
        slug = meta.get("slug") or (m.group(2) if m else f.stem)
        if not re.match(r"^[a-z0-9-]+$", slug):
            sys.exit(f"✗ الاسم المختصر (slug) يجب أن يكون بحروف لاتينية صغيرة وأرقام وشرطات فقط: {f.name}")
        if not meta.get("title"):
            sys.exit(f"✗ لا يوجد عنوان (title) في: {f.name}")
        plain = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", body)
        plain = re.sub(r"[#>*`\[\]()!_-]", " ", plain)
        posts.append({
            "title": meta["title"], "slug": slug, "date": parse_date(d),
            "excerpt": meta.get("excerpt") or " ".join(plain.split()[:32]) + "…",
            "image": meta.get("image", ""), "topic": meta.get("topic", ""),
            "teaser": meta.get("teaser", ""),
            "order": int(meta.get("order") or 0),   # ترتيب تدوينات اليوم الواحد
            "body_md": body, "reading": reading_time(plain),
        })
    posts.sort(key=lambda p: (p["date"], p["order"], p["slug"]), reverse=True)
    for i, p in enumerate(posts):          # الأقدم يحمل الرقم 001
        p["num"] = len(posts) - i
    return posts


def load_notes():
    f = CONTENT / "notes.md"
    if not f.exists():
        return {}, []
    meta, body = parse_front_matter(f.read_text(encoding="utf-8"))
    parts = re.split(r"(?m)^## (\d{4}-\d{2}-\d{2})\s*$", body)
    notes = []
    for k in range(1, len(parts), 2):
        text = parts[k + 1].strip()
        if text:
            notes.append({"date": parse_date(parts[k]), "html": markdown(text), "order": k})
    notes.sort(key=lambda n: (n["date"], -n["order"]), reverse=True)   # الأحدث أولًا
    for i, n in enumerate(notes):
        n["num"] = len(notes) - i
    return meta, notes


def chapters(site, posts):
    """يقسّم التدوينات فصولًا: حسب عمر الكاتب إن عُرف تاريخ بلوغه الثلاثين، وإلا حسب السنة."""
    raw = str(site.get("thirtieth_birthday", "")).strip()
    bday = None
    if raw:
        m = re.match(r"^(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?$", raw)
        if not m:
            sys.exit('✗ thirtieth_birthday في site.json يُكتب هكذا: "2024" أو "2024-05" أو "2024-05-17"')
        bday = date(int(m.group(1)), int(m.group(2) or 1), int(m.group(3) or 1))
    groups = {}
    for p in posts:
        if bday:
            d = p["date"]
            key = 30 + d.year - bday.year - ((d.month, d.day) < (bday.month, bday.day))
        else:
            key = p["date"].year
        groups.setdefault(key, []).append(p)
    out = []
    for key in sorted(groups, reverse=True):
        if not bday:
            title = str(key)
        elif key < 30:
            title = "قبل الثلاثين"
        elif key in AGES:
            title = f"في {AGES[key]}"
        else:
            title = "بعد الثلاثينات"
        out.append({"key": key, "title": title, "posts": groups[key],
                    "line": site.get("years_notes", {}).get(str(key), "")})
    return out, bool(bday)


def og_card(site, kicker, title):
    size = 86 if len(title) < 28 else 70 if len(title) < 50 else 56
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl" data-palette="cream"><head><meta charset="UTF-8">
<link rel="stylesheet" href="../dist/assets/css/style.css">
<style>
html,body{{margin:0;width:1200px;height:630px;overflow:hidden}}
.c{{position:relative;width:1200px;height:630px;box-sizing:border-box;padding:64px 80px;display:flex;flex-direction:column;background:var(--paper)}}
.c svg.pat{{position:absolute;inset:0;width:100%;height:100%}}
.c svg.pat path{{fill:none;stroke:var(--gold);stroke-width:1.6;stroke-linecap:round;opacity:.22}}
.c svg.pat path.one{{stroke:var(--caret);opacity:.6}}
.top{{position:relative;display:flex;justify-content:space-between;align-items:center;font-family:var(--font-display);font-size:34px;color:var(--heading)}}
.top .b{{display:flex;align-items:center;gap:16px}}
.top svg{{width:48px}}
.k{{font-family:var(--font-ui);font-size:30px;color:var(--ink-faint);letter-spacing:.06em}}
.t{{position:relative;flex:1;display:flex;align-items:center}}
.t h1{{font-size:{size}px;font-weight:400;line-height:1.3;max-width:19ch;text-wrap:balance}}
.bot{{position:relative;display:flex;align-items:center;gap:20px;font-family:var(--font-ui);font-size:28px;color:var(--ink-soft)}}
.bot i{{display:block;width:64px;height:3px;background:var(--gold)}}
</style></head><body><div class="c">
{pen_pattern("pat", 1200, 630, 7)}
<div class="top"><span class="b">{LOGO}<span>{esc(site["title"])}</span></span><span class="k" dir="ltr">{esc(kicker)}</span></div>
<div class="t"><h1>{esc(title)}</h1></div>
<div class="bot"><i></i><span>{esc(site["author"])}</span></div>
</div></body></html>"""


def mail_html(site, p, base):
    """رسالة «تدوينة جديدة»: صورة، عنوان، مقتطف، وزر يقود إلى الموقع. جداول وأنماط مضمَّنة لأن برامج البريد لا تقبل غيرها."""
    link = f"{base}post/{p['slug']}/" if base else "#"
    src = (base or "../") + "assets/mail/"
    serif = "'Thmanyah Serif Display', Georgia, 'Times New Roman', serif"
    sans = "'Thmanyah Sans', 'Segoe UI', Tahoma, Arial, sans-serif"
    paras = [x.strip() for x in (p["teaser"] or p["excerpt"]).split("|") if x.strip()]
    text = "".join(f'<p style="margin:0 0 18px;font-family:{serif};font-size:18px;line-height:2;color:#1F2421;">{esc(x)}</p>'
                   for x in paras)
    cover = ""
    if p["image"] and (ROOT / "assets" / "mail" / f"{p['slug']}.jpg").exists():
        cover = (f'<tr><td style="padding:0;"><a href="{link}"><img src="{src}{p["slug"]}.jpg" width="600" alt="" '
                 f'style="display:block;width:100%;max-width:600px;height:auto;border:0;"></a></td></tr>')
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(p['title'])}</title>
</head>
<body style="margin:0;padding:0;background:#F6EDE3;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{esc(paras[0] if paras else p['excerpt'])}</div>
<table role="presentation" dir="rtl" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#F6EDE3;">
<tr><td align="center" style="padding:32px 16px;">
  <table role="presentation" dir="rtl" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;">
    <tr><td style="padding:0 4px 24px;text-align:right;">
      <table role="presentation" dir="rtl" cellpadding="0" cellspacing="0" border="0"><tr>
        <td style="padding-left:12px;vertical-align:middle;"><img src="{src}logo.png" width="34" height="31" alt="" style="display:block;border:0;"></td>
        <td style="vertical-align:middle;font-family:{serif};font-size:22px;color:#6D1F2C;">{esc(site['title'])}</td>
      </tr></table>
    </td></tr>
    {cover}
    <tr><td style="padding:36px 4px 0;text-align:right;">
      <p style="margin:0 0 14px;font-family:{sans};font-size:14px;letter-spacing:.5px;color:#6F655C;">تدوينة جديدة &nbsp;·&nbsp; <span dir="ltr">{p['num']:03d}</span></p>
      <h1 style="margin:0;font-family:{serif};font-size:30px;font-weight:normal;line-height:1.5;color:#6D1F2C;"><a href="{link}" style="color:#6D1F2C;text-decoration:none;">{esc(p['title'])}</a></h1>
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="right" style="margin:22px 0 24px;"><tr><td width="64" height="2" style="background:#C9971C;font-size:0;line-height:0;">&nbsp;</td></tr></table>
    </td></tr>
    <tr><td style="padding:0 4px;text-align:right;">
      {text}
    </td></tr>
    <tr><td style="padding:14px 4px 0;text-align:right;">
      <table role="presentation" dir="rtl" cellpadding="0" cellspacing="0" border="0" align="right"><tr>
        <td style="background:#6D1F2C;border-radius:4px;"><a href="{link}" style="display:inline-block;padding:14px 30px;font-family:{sans};font-size:16px;font-weight:bold;color:#F6EDE3;text-decoration:none;">اقرأ التدوينة كاملة &larr;</a></td>
      </tr></table>
    </td></tr>
    <tr><td style="padding:44px 4px 0;text-align:right;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td height="1" style="background:#E4D7C7;font-size:0;line-height:0;">&nbsp;</td></tr></table>
      <p style="margin:18px 0 0;font-family:{sans};font-size:13px;line-height:1.9;color:#6F655C;">وصلتك هذه الرسالة لأنك طلبت أن أخبرك حين أنشر تدوينة جديدة.<br>{esc(site['author'])}</p>
    </td></tr>
  </table>
</td></tr>
</table>
</body>
</html>
"""


def write(rel, content):
    out = DIST / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")


# ————————————————— البناء —————————————————

def build():
    site = json.loads((CONTENT / "site.json").read_text(encoding="utf-8"))
    posts = load_posts()
    notes_meta, notes = load_notes()
    base = base_url(site)
    urls = []          # لخريطة الموقع

    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "assets" / "css").mkdir(parents=True)
    shutil.copy(THEME / "style.css", DIST / "assets" / "css" / "style.css")
    shutil.copy(THEME / "favicon.svg", DIST / "assets" / "favicon.svg")
    (DIST / "assets" / "js").mkdir(parents=True)
    shutil.copy(THEME / "portrait.js", DIST / "assets" / "js" / "portrait.js")
    if ASSETS.exists():
        shutil.copytree(ASSETS, DIST / "assets", dirs_exist_ok=True)
    (DIST / ".nojekyll").write_text("", encoding="utf-8")
    if site.get("domain"):
        (DIST / "CNAME").write_text(site["domain"].strip() + "\n", encoding="utf-8")

    # ——— الرئيسية ———
    root = ""
    h = site["hero"]
    accent = (f'<span><em>{esc(h["title_accent"])}</em><i class="caret" aria-hidden="true"></i></span>'
              if h.get("title_accent") else "")
    second = (f'<a class="link-more" href="{href(root, "subscribe/")}">{esc(site["newsletter"]["button"])}</a>'
              if news_on(site) else
              f'<a class="link-more" href="{href(root, "about/")}">{esc(h.get("cta2", "من يكتب هنا"))}</a>')
    visual = hero_visual(site, posts, root, notes)
    body = f"""<section class="hero">
  {pen_pattern()}
  <div class="wrap{' hero__grid' if visual else ''}">
    <div class="hero__text">
      <p class="hero__kicker">{esc(h["kicker"])}</p>
      <h1 class="hero__title"><span>{esc(h["title"])}</span>{accent}</h1>
      <p class="hero__lead">{esc(h["lead"])}</p>
      <div class="hero__actions">
        <a class="btn" href="#posts">{esc(h["cta"])}</a>
        {second}
      </div>
    </div>
    {visual}
  </div>
  <span class="hero__down" aria-hidden="true"></span>
</section>
"""
    paras = [x for x in site.get("manifesto", []) if x.strip()]
    if paras:
        body += '<section class="manifesto">\n  <div class="wrap">\n' + "\n".join(
            f'    <p class="manifesto__text" data-reveal>{esc(x)}</p>' for x in paras) + "\n  </div>\n</section>\n"
    recent = posts[:int(site.get("home_posts", 6))]
    if recent:
        more = (f'<p class="more"><a class="link-more" href="{href(root, "archive/")}">كل التدوينات</a></p>'
                if len(posts) > len(recent) else "")
        body += f"""<section class="posts" id="posts">
  <div class="wrap">
    <div class="section-head"><h2>آخر التدوينات</h2></div>
    {''.join(post_row(p, root) for p in recent)}
    {more}
  </div>
</section>
"""
    if notes:
        body += f"""<section class="home-notes">
  <div class="wrap">
    <div class="section-head"><h2>من الدفتر</h2></div>
    <div class="notes-grid">
      {''.join(note_card(n, root, link=True) for n in notes[:3])}
    </div>
    <p class="more"><a class="link-more" href="{href(root, 'notes/')}">افتح الدفتر</a></p>
  </div>
</section>
"""
    nb = newsletter_block(site)
    if nb:
        body += f'<section class="band">\n  <div class="wrap">\n    {nb}\n  </div>\n</section>\n'
    q = site.get("pull_quote", {})
    if q.get("text"):
        by = f'<p class="pull__by meta">{esc(q["by"])}</p>' if q.get("by") else ""
        body += f'<section class="pull">\n  <div class="wrap">\n    <p class="pull__q">{esc(q["text"])}</p>\n    {by}\n  </div>\n</section>\n'
    write("index.html", page(site, root, site["title"], site["description"], body, "home"))
    urls.append("")

    # ——— التدوينات ———
    root = "../../"
    for i, p in enumerate(posts):
        newer = posts[i - 1] if i > 0 else None
        older = posts[i + 1] if i + 1 < len(posts) else None

        def neighbor(x, cls, label):
            if not x:
                return (f'<span class="neighbor {cls} neighbor--empty"><span class="neighbor__dir">{label}</span>'
                        f'<span class="neighbor__title">—</span></span>')
            return (f'<a class="neighbor {cls}" href="{href(root, "post/" + x["slug"] + "/")}">'
                    f'<span class="neighbor__dir">{label}</span>'
                    f'<span class="neighbor__title">{esc(x["title"])}</span></a>')

        fig = (f'<figure class="article__fig">{picture(root + p["image"])}</figure>' if p["image"] else "")
        reply = ""
        if site.get("reply_email"):
            subject = "ردّ على: " + p["title"]
            reply = (f'<p class="reply">عندك تعليق على هذه التدوينة؟ '
                     f'<a href="mailto:{esc(site["reply_email"])}?subject={esc(subject)}">اكتب لي</a>.</p>')
        nb = newsletter_block(site)
        nb = f'<div class="article__news">{nb}</div>' if nb else ""
        body = f"""<article class="article">
  <div class="wrap">
    <header class="article__head">
      <p class="post-num" dir="ltr" aria-label="التدوينة رقم {p['num']}">{p['num']:03d}</p>
      <h1 class="article__title">{esc(p['title'])}</h1>
      <p class="meta article__meta">{post_meta(p)}</p>
    </header>
    {fig}
    <div class="prose" id="reading">
{markdown(p['body_md'], root)}
    </div>
    {ENDMARK}
    <footer class="article__end">
      <p class="sig">— {esc(site['author'])}</p>
      {reply}
      {nb}
      <nav class="neighbors" aria-label="تدوينات مجاورة">
        {neighbor(older, 'neighbor--next', 'التدوينة السابقة')}
        {neighbor(newer, 'neighbor--prev', 'التدوينة التالية')}
      </nav>
    </footer>
  </div>
</article>
"""
        rel = f"post/{p['slug']}/"
        write(rel + "index.html",
              page(site, root, p["title"], p["excerpt"], body, og_type="article", path=rel,
                   og_image=f"assets/og/{p['slug']}.png",
                   extra='<div class="progress" id="progress" aria-hidden="true"></div>\n'))
        urls.append(rel)

    # ——— سنوات الثلاثين / الأرشيف ———
    root = "../"
    chs, by_age = chapters(site, posts)
    arch_title = "سنوات الثلاثين" if by_age else "الأرشيف"
    blocks = ""
    for c in chs:
        items = "".join(
            f'<a class="chapter__item" href="{href(root, "post/" + p["slug"] + "/")}">'
            f'<span class="chapter__num" dir="ltr">{p["num"]:03d}</span>'
            f'<span class="chapter__title">{esc(p["title"])}</span>'
            f'<time datetime="{p["date"].isoformat()}">{p["date"].day} {MONTHS[p["date"].month - 1]}'
            + (f' {p["date"].year}' if by_age else "") + "</time></a>" for p in c["posts"])
        line = f'<p class="chapter__line">{esc(c["line"])}</p>' if c["line"] else ""
        count = plural(len(c["posts"]), "تدوينة واحدة", "تدوينتان", "تدوينات", "تدوينة")
        blocks += f"""<section class="chapter">
    <header class="chapter__head">
      <h2>{esc(c["title"])}</h2>
      <p class="meta">{count}</p>
      {line}
    </header>
    <div class="chapter__list">{items}</div>
  </section>
"""
    body = f"""<div class="wrap">
  {page_head(arch_title, site.get('archive_intro', ''))}
  {blocks}
</div>
"""
    write("archive/index.html", page(site, root, arch_title, site["description"], body, "archive", path="archive/"))
    urls.append("archive/")

    # ——— الدفتر ———
    if (CONTENT / "notes.md").exists():
        count = plural(len(notes), "سطر واحد", "سطران", "سطور", "سطرًا") if notes else ""
        body = f"""<div class="wrap">
  {page_head(notes_meta.get('title', 'الدفتر'), notes_meta.get('intro', ''), count)}
  <div class="notes">
    {''.join(note_card(n, root) for n in notes)}
  </div>
</div>
"""
        write("notes/index.html", page(site, root, notes_meta.get("title", "الدفتر"),
                                       notes_meta.get("intro", site["description"]), body, "notes", path="notes/"))
        urls.append("notes/")

    # ——— صفحات نصية: الآن، عني ———
    for name, key in (("now", "now"), ("about", "about")):
        f = CONTENT / "pages" / f"{name}.md"
        if not f.exists():
            continue
        meta, md = parse_front_matter(f.read_text(encoding="utf-8"))
        title = meta.get("title", name)
        stamp = f'آخر تحديث: {ar_date(parse_date(meta["updated"]))}' if meta.get("updated") else ""
        fig = (f'<figure class="article__fig article__fig--portrait">{picture(root + meta["image"], title)}</figure>'
               if meta.get("image") else "")
        if meta.get("sketch"):       # رسم جاهز بخلفية شفافة: يُعرض كما هو بلا صبغة
            motion = meta.get("sketch_motion", "")
            attrs, cap, js = "", "", ""
            if motion == "letters":  # وجه من حروف عناوين التدوينات
                words = " ".join(p["title"] for p in posts) + " " + site["title"]
                attrs = f' data-motion="letters" data-letters="{esc(words)}"'
                cap = '<figcaption class="article__sketchcap">وجهٌ من حروف تدويناتي. مرّر عليه.</figcaption>'
            if motion:
                js = f'<script src="{root}assets/js/portrait.js" defer></script>'
            fig = (f'<figure class="article__sketch article__sketch--{esc(motion or "still")}"><span class="sketchp"{attrs}>'
                   f'<img src="{root}{esc(meta["sketch"])}" alt="رسم لصاحب المدونة"></span>{cap}</figure>{js}')
        stamp_html = f'<p class="meta article__meta">{stamp}</p>' if stamp else ""
        body = f"""<article class="article">
  <div class="wrap">
    <header class="article__head">
      <h1 class="article__title">{esc(title)}</h1>
      {stamp_html}
    </header>
    {fig}
    <div class="prose">
{markdown(md, root)}
    </div>
  </div>
</article>
"""
        write(f"{name}/index.html", page(site, root, title, meta.get("description", site["description"]),
                                         body, key, path=f"{name}/"))
        urls.append(f"{name}/")

    # ——— النشرة (تُبنى فقط حين تُفعَّل في site.json) ———
    if news_on(site):
        n = site["newsletter"]
        latest = "".join(post_row(p, root) for p in posts[:3])
        latest = (f'<section class="posts"><div class="section-head"><h2>آخر ما نُشر</h2></div>{latest}</section>'
                  if latest else "")
        body = f"""<div class="wrap">
  {page_head(n.get('title', 'النشرة'), n.get('page_intro', ''))}
  {newsletter_block(site, heading=False)}
  {latest}
</div>
"""
        write("subscribe/index.html", page(site, root, n.get("title", "النشرة"), n["body"], body,
                                           "subscribe", path="subscribe/"))
        urls.append("subscribe/")

    # ——— 404: تُعرض من أي عمق، فروابطها مطلقة ———
    root404 = "/"
    if base:
        tail = base.split("://", 1)[-1].split("/", 1)[-1].strip("/")
        root404 = f"/{tail}/" if tail else "/"
    body = f"""<div class="wrap">
  {page_head('هذه الصفحة غير موجودة', 'ربما تغيّر الرابط أو حُذفت التدوينة.')}
  <p class="more"><a class="link-more" href="{root404}">العودة إلى الرئيسية</a></p>
</div>
"""
    write("404.html", page(site, root404, "غير موجودة", site["description"], body))

    # ——— RSS وخريطة الموقع (يحتاجان عنوان الموقع الكامل في site.json) ———
    if base:
        items = "".join(f"""
  <item>
    <title>{esc(p['title'])}</title>
    <link>{base}post/{p['slug']}/</link>
    <guid>{base}post/{p['slug']}/</guid>
    <pubDate>{datetime.combine(p['date'], datetime.min.time()).strftime('%a, %d %b %Y 00:00:00 +0000')}</pubDate>
    <description>{esc(p['excerpt'])}</description>
  </item>""" for p in posts[:20])
        write("feed.xml", f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>{esc(site['title'])}</title>
  <link>{base}</link>
  <description>{esc(site['description'])}</description>
  <language>ar</language>{items}
</channel></rss>
""")
        write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
              + "".join(f"  <url><loc>{base}{u}</loc></url>\n" for u in urls) + "</urlset>\n")
        write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {base}sitemap.xml\n")

    # ——— رسائل التنبيه: رسالة لكل تدوينة في mail/ (لا تُنشر مع الموقع) ———
    if not LOCAL:
        mail = ROOT / "mail"
        mail.mkdir(exist_ok=True)
        for old in mail.glob("*.html"):
            old.unlink()
        for p in posts:
            (mail / f"{p['date'].isoformat()}-{p['slug']}.html").write_text(mail_html(site, p, base), encoding="utf-8")

    # ——— بطاقات المشاركة: ملفات HTML تُصوَّر بـ tools/og.mjs ———
    if OG:
        og = ROOT / ".og"
        if og.exists():
            shutil.rmtree(og)
        og.mkdir()
        (og / "default.html").write_text(
            og_card(site, "", site["hero"]["title"] + " " + site["hero"].get("title_accent", "")), encoding="utf-8")
        for p in posts:
            (og / f"{p['slug']}.html").write_text(og_card(site, f"{p['num']:03d}", p["title"]), encoding="utf-8")
        raw = "" if site.get("image_treatment", True) else ' data-img="raw"'
        for p in posts:
            if p["image"]:
                (og / f"mail-{p['slug']}.html").write_text(
                    f'<!DOCTYPE html><html data-palette="cream"{raw}><head><meta charset="UTF-8">'
                    '<link rel="stylesheet" href="../dist/assets/css/style.css"><style>html,body{margin:0;width:1200px;height:675px;overflow:hidden}'
                    '.duo{width:1200px;height:675px;border-radius:0}.duo img{width:1200px;height:675px;object-fit:cover}</style></head>'
                    f'<body><span class="duo"><img src="../{esc(p["image"])}" alt=""></span></body></html>', encoding="utf-8")
        (og / "mail-logo.html").write_text(
            '<!DOCTYPE html><html><head><meta charset="UTF-8"><style>html,body{margin:0;background:transparent}svg{display:block;width:240px;height:220px}</style></head><body>'
            '<svg viewBox="0 0 120 110"><path fill="#6D1F2C" d="M8 50 C8 116, 112 116, 112 40 L93 40 C93 84, 27 84, 27 50 Z"/>'
            '<path fill="#C1571B" d="M60 8 L74 22 L60 36 L46 22 Z"/></svg></body></html>', encoding="utf-8")
        print(f"✓ جُهّزت {len(posts) + 1} بطاقة مشاركة في .og/")

    print(f"✓ بُني الموقع في {DIST.name}/ — {len(posts)} تدوينة، {len(notes)} سطرًا في الدفتر")


if __name__ == "__main__":
    build()
