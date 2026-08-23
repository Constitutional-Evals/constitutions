#!/usr/bin/env python3
"""Build an offline reading PDF of the 24 provisional value-tradition anchor constitutions.

Usage:  python scripts/build_reading_pdf.py [output.pdf] [--verify]

Requires reportlab (`pip install reportlab`); `--verify` additionally needs pypdfium2 and
re-reads the finished PDF to confirm every source string was typeset verbatim.

Reads every constitution in `Provisional Constitutions/Provisional Anchors/` and typesets
them as a single navigable book: title page, reader's note, table of contents, PDF outline
bookmarks, and one chapter per tradition (overview, 12 comparative criteria with reasoning
and scenarios, then the guidelines / edge cases).
"""

import html
import json
import os
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)
from reportlab.platypus.tableofcontents import TableOfContents

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "Provisional Constitutions" / "Provisional Anchors"

# ---------------------------------------------------------------- fonts

FONT_DIRS = [
    "/usr/share/fonts/truetype/freefont",
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/truetype/dejavu",
]

FONT_FILES = {
    "Body": ["FreeSerif.ttf", "LiberationSerif-Regular.ttf", "DejaVuSerif.ttf"],
    "Body-Bold": ["FreeSerifBold.ttf", "LiberationSerif-Bold.ttf", "DejaVuSerif-Bold.ttf"],
    "Body-Italic": ["FreeSerifItalic.ttf", "LiberationSerif-Italic.ttf", "DejaVuSerif.ttf"],
    "Body-BoldItalic": ["FreeSerifBoldItalic.ttf", "LiberationSerif-BoldItalic.ttf", "DejaVuSerif-Bold.ttf"],
    "Display": ["LiberationSans-Regular.ttf", "DejaVuSans.ttf", "FreeSans.ttf"],
    "Display-Bold": ["LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf", "FreeSansBold.ttf"],
}


def register_fonts():
    for name, candidates in FONT_FILES.items():
        for cand in candidates:
            for d in FONT_DIRS:
                p = os.path.join(d, cand)
                if os.path.exists(p):
                    pdfmetrics.registerFont(TTFont(name, p))
                    break
            else:
                continue
            break
        else:
            raise RuntimeError(f"no font file found for {name} (tried {candidates})")
    pdfmetrics.registerFontFamily(
        "Body", normal="Body", bold="Body-Bold", italic="Body-Italic", boldItalic="Body-BoldItalic"
    )
    pdfmetrics.registerFontFamily("Display", normal="Display", bold="Display-Bold")


# ---------------------------------------------------------------- palette

INK = colors.HexColor("#1B1B1D")
MUTED = colors.HexColor("#5E6068")
FAINT = colors.HexColor("#9A9CA4")
ACCENT = colors.HexColor("#2E5266")
RULE = colors.HexColor("#D6D8DE")

# ---------------------------------------------------------------- the set
# (order is thematic, not alphabetical — it reads better front to back)

PARTS = [
    (
        "Religious & Spiritual Traditions",
        [
            ("Buddhism", "Buddhism_Constitution.json"),
            ("Hinduism", "Hinduism_Constitution.json"),
            ("Judaism", "Judaism_Constitution.json"),
            ("Christianity", "Christianity_Constitution.json"),
            ("Islam", "Islam_Constitution.json"),
            ("Confucianism", "Confucianism_Constitution.json"),
            ("Taoism", "Taoism_Constitution.json"),
        ],
    ),
    (
        "Classical & Modern Ethics",
        [
            ("Stoicism", "Stoicism_Constitution.json"),
            ("Kantian Deontology", "Kantian_Deontology_Constitution.json"),
            ("Utilitarianism", "Utilitarianism_Constitution.json"),
            ("Neo-Virtue Ethics", "Neo-Virtue-Ethics Constitution.json"),
            ("Care Ethics", "Care-Ethics Constitution.json"),
            ("Universal Kindness", "Universal_Kindness_Constitution.json"),
        ],
    ),
    (
        "Political & Social Philosophies",
        [
            ("Lockean Rights", "Lockean_Rights_Constitution.json"),
            ("Rawlsian Justice", "Rawlsian Justice Constitution.json"),
            ("Marxism", "Marxism_Constitution.json"),
            ("Conservatism", "Conservatism_Constitution.json"),
            ("Secular Humanism", "Secular Humanism Constitution.json"),
        ],
    ),
    (
        "Indigenous & Ecological Worldviews",
        [
            ("Ubuntu", "Ubuntu Constitution.json"),
            ("Māori", "Maori Constitution.json"),
            ("Aboriginal Australian", "Aboriginal Australian Constitution.json"),
            ("North American Indigenous", "North American Indigenous.json"),
            ("Buen Vivir", "Buen Vivir Constitution.json"),
            ("Environmental Ethics", "Environmental Ethics Constitution.json"),
        ],
    ),
]

# ---------------------------------------------------------------- styles

PAGE = A5
PW, PH = PAGE
ML = MR = 15 * mm
MT = 17 * mm
MB = 16 * mm


def build_styles():
    s = {}
    s["overview"] = ParagraphStyle(
        "overview", fontName="Body", fontSize=10.2, leading=15.4, textColor=INK,
        alignment=TA_JUSTIFY, spaceAfter=6, allowWidows=0, allowOrphans=0,
    )
    s["comparative"] = ParagraphStyle(
        "comparative", fontName="Body", fontSize=10.2, leading=15.2, textColor=INK,
        alignment=TA_JUSTIFY, spaceBefore=11, spaceAfter=4, allowWidows=0, allowOrphans=0,
    )
    s["reasoning"] = ParagraphStyle(
        "reasoning", fontName="Body-Italic", fontSize=8.9, leading=13.0, textColor=MUTED,
        leftIndent=9, spaceBefore=2, spaceAfter=4, allowWidows=0, allowOrphans=0,
    )
    s["scenario"] = ParagraphStyle(
        "scenario", fontName="Body", fontSize=8.7, leading=12.6, textColor=MUTED,
        leftIndent=18, bulletIndent=9, spaceAfter=2.5,
    )
    s["kicker"] = ParagraphStyle(
        "kicker", fontName="Display-Bold", fontSize=7.0, leading=9, textColor=ACCENT,
        spaceBefore=9, spaceAfter=2.5, keepWithNext=1,
    )
    s["scen_label"] = ParagraphStyle(
        "scen_label", fontName="Display-Bold", fontSize=6.4, leading=8.5, textColor=FAINT,
        leftIndent=9, spaceBefore=3, spaceAfter=2.5, keepWithNext=1,
    )
    s["section"] = ParagraphStyle(
        "section", fontName="Display-Bold", fontSize=8.2, leading=11, textColor=ACCENT,
        spaceBefore=16, spaceAfter=8, keepWithNext=1,
    )
    s["chapter_num"] = ParagraphStyle(
        "chapter_num", fontName="Display-Bold", fontSize=7.5, leading=10, textColor=FAINT,
        spaceAfter=5, keepWithNext=1,
    )
    s["chapter"] = ParagraphStyle(
        "chapter", fontName="Body-Bold", fontSize=21, leading=25, textColor=INK,
        spaceAfter=3, keepWithNext=1,
    )
    s["chapter_part"] = ParagraphStyle(
        "chapter_part", fontName="Body-Italic", fontSize=9, leading=12, textColor=MUTED,
        spaceAfter=14,
    )
    s["part_title"] = ParagraphStyle(
        "part_title", fontName="Body-Bold", fontSize=18, leading=23, textColor=INK,
        alignment=TA_CENTER,
    )
    s["part_num"] = ParagraphStyle(
        "part_num", fontName="Display-Bold", fontSize=8, leading=11, textColor=ACCENT,
        alignment=TA_CENTER, spaceAfter=8, keepWithNext=1,
    )
    s["part_list"] = ParagraphStyle(
        "part_list", fontName="Body", fontSize=9.5, leading=15, textColor=MUTED,
        alignment=TA_CENTER,
    )
    s["title"] = ParagraphStyle(
        "title", fontName="Body-Bold", fontSize=27, leading=32, textColor=INK,
        alignment=TA_CENTER,
    )
    s["subtitle"] = ParagraphStyle(
        "subtitle", fontName="Body-Italic", fontSize=11.5, leading=16, textColor=MUTED,
        alignment=TA_CENTER,
    )
    s["colophon"] = ParagraphStyle(
        "colophon", fontName="Display", fontSize=7.5, leading=11.5, textColor=FAINT,
        alignment=TA_CENTER,
    )
    s["note"] = ParagraphStyle(
        "note", fontName="Body", fontSize=9.6, leading=14.6, textColor=INK,
        alignment=TA_JUSTIFY, spaceAfter=7, allowWidows=0, allowOrphans=0,
    )
    s["note_h"] = ParagraphStyle(
        "note_h", fontName="Display-Bold", fontSize=8.2, leading=11, textColor=ACCENT,
        spaceBefore=12, spaceAfter=5, keepWithNext=1,
    )
    s["toc_part"] = ParagraphStyle(
        "toc_part", fontName="Display-Bold", fontSize=7.6, leading=11, textColor=ACCENT,
        spaceBefore=11, spaceAfter=3,
    )
    s["toc_entry"] = ParagraphStyle(
        "toc_entry", fontName="Body", fontSize=9.6, leading=15, textColor=INK,
    )
    return s


def esc(t):
    return html.escape(str(t), quote=False)


def sc(t):
    """Small-caps-ish label: uppercase and letterspaced.

    ReportLab normalises runs of Unicode whitespace, so the tracking is built from
    &nbsp; entities — those survive into the rendered line as real gaps.
    """
    words = esc(t).upper().split()
    return "&nbsp;&nbsp;&nbsp;".join("&nbsp;".join(w) for w in words)


# ---------------------------------------------------------------- doc template


class Book(BaseDocTemplate):
    """Adds running heads, page numbers and a PDF outline."""

    def __init__(self, filename, **kw):
        BaseDocTemplate.__init__(self, filename, **kw)
        self.chapter_title = None
        frame = Frame(ML, MB, PW - ML - MR, PH - MT - MB, id="body",
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([
            PageTemplate(id="plain", frames=[frame], onPage=self.plain_page),
            PageTemplate(id="body", frames=[frame], onPage=self.body_page),
            PageTemplate(id="opener", frames=[frame], onPage=self.opener_page),
        ])

    def beforeDocument(self):
        # multiBuild runs the story more than once; the running head must not leak
        # from the tail of one pass into the head of the next.
        self.chapter_title = None

    def plain_page(self, canv, doc):
        pass

    def opener_page(self, canv, doc):
        canv.saveState()
        canv.setFont("Display", 7.6)
        canv.setFillColor(FAINT)
        canv.drawCentredString(PW / 2.0, MB - 8 * mm, str(canv.getPageNumber()))
        canv.restoreState()

    def body_page(self, canv, doc):
        canv.saveState()
        if self.chapter_title:
            canv.setFont("Display", 6.6)
            canv.setFillColor(FAINT)
            canv.drawString(ML, PH - MT + 7 * mm, self.chapter_title.upper())
            canv.setStrokeColor(RULE)
            canv.setLineWidth(0.4)
            canv.line(ML, PH - MT + 5.6 * mm, PW - MR, PH - MT + 5.6 * mm)
        canv.setFont("Display", 7.6)
        canv.setFillColor(FAINT)
        canv.drawCentredString(PW / 2.0, MB - 8 * mm, str(canv.getPageNumber()))
        canv.restoreState()

    def afterFlowable(self, flowable):
        if not isinstance(flowable, Paragraph):
            return
        style = flowable.style.name
        text = flowable.getPlainText()
        if style == "chapter":
            self.chapter_title = text
            key = f"ch{self.page}-{abs(hash(text)) % 99999}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=1, closed=True)
            self.notify("TOCEntry", (1, text, self.page, key))
        elif style == "part_title":
            self.chapter_title = None
            key = f"pt{self.page}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=0, closed=True)
            self.notify("TOCEntry", (0, text, self.page, key))


# ---------------------------------------------------------------- content


def load(fname):
    with open(SRC / fname, encoding="utf-8") as fh:
        return json.load(fh)


def criterion_flowables(s, label, item, first=False):
    # The label rides on the first line of the statement rather than sitting in its own
    # flowable: keepWithNext would drag the whole statement to the next page and leave
    # a hole, whereas one paragraph can split after its second line.
    lead = (f'<font name="Display-Bold" size="7" color="#{ACCENT.hexval()[2:]}">'
            f'{sc(label)}</font><br/>{esc(item["comparative"])}')
    out = [Paragraph(lead, s["comparative"])]
    if item.get("reasoning"):
        out.append(Paragraph(esc(item["reasoning"]), s["reasoning"]))
    scen = item.get("scenarios") or []
    if scen:
        out.append(Paragraph(sc("Where it bites"), s["scen_label"]))
        for sx in scen:
            out.append(Paragraph(esc(sx), s["scenario"], bulletText="–"))
    return out


def front_matter(s, story, total_criteria):
    story.append(Spacer(1, 34 * mm))
    story.append(Paragraph("The Constitutions", s["title"]))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(
        "Twenty-four value traditions, written as decision criteria", s["subtitle"]))
    story.append(Spacer(1, 40 * mm))
    story.append(Paragraph(
        "Provisional anchor set &bull; Constitutional Evals<br/>"
        f"{total_criteria} comparative criteria across 24 traditions", s["colophon"]))
    story.append(PageBreak())

    story.append(Paragraph(sc("How to read this"), s["note_h"]))
    story.append(Paragraph(
        "Each constitution in this collection distils one value tradition into the form a "
        "judge can actually apply: not a creed, but a set of <i>comparative</i> criteria "
        "&mdash; instructions of the shape &ldquo;prefer the response that&hellip;&rdquo; &mdash; "
        "for choosing between two ways of answering the same question.", s["note"]))
    story.append(Paragraph(
        "Every chapter has the same four parts, so you can read one tradition end to end or "
        "read the same part across all twenty-four:", s["note"]))
    story.append(Paragraph(
        "<b>Overview</b> &mdash; the tradition in a paragraph, including where it refuses to "
        "generalise.", s["note"]))
    story.append(Paragraph(
        "<b>Criteria</b> &mdash; twelve preference rules. Each is the operative sentence; the "
        "italic paragraph beneath it is the textual warrant, naming the sources the rule was "
        "distilled from.", s["note"]))
    story.append(Paragraph(
        "<b>Where it bites</b> &mdash; the concrete requests that separate a response honouring "
        "the criterion from one that does not. These are the most revealing part: two traditions "
        "often agree on a principle and split on the scenario.", s["note"]))
    story.append(Paragraph(
        "<b>Guidelines</b> &mdash; the edge cases, where the tradition's own rules pull against "
        "each other and something has to give.", s["note"]))

    story.append(Paragraph(sc("Provenance"), s["note_h"]))
    story.append(Paragraph(
        "These are the twenty-four value-tradition anchors held in "
        "<i>Provisional Constitutions / Provisional Anchors</i> in the "
        "<b>Constitutional-Evals/constitutions</b> repository &mdash; the set the shared latent "
        "basis is intended to be fit on. They are provisional: the released, versioned "
        "<i>anchors/</i> folder currently carries only the EigenBench-derived Universal Kindness "
        "anchor plus two misaligned stubs (selfish power-seeking, unquestioning obedience), and "
        "these twenty-four are staged to be promoted into it. Text is reproduced verbatim; only "
        "the ordering and typography are editorial.", s["note"]))
    story.append(Paragraph(
        "Ordering here is thematic rather than alphabetical, and carries no ranking. The "
        "traditions are peers: the point of the set is that they disagree.", s["note"]))
    story.append(PageBreak())


def main():
    register_fonts()
    s = build_styles()
    positional = [a for a in sys.argv[1:] if not a.startswith("-")]
    out = positional[0] if positional else str(REPO / "dist" / "constitutions-reader.pdf")
    Path(out).parent.mkdir(parents=True, exist_ok=True)

    data = []
    total_criteria = 0
    for part, items in PARTS:
        for title, fname in items:
            d = load(fname)
            total_criteria += len(d.get("criteria", []))
            data.append((part, title, d))

    doc = Book(
        out, pagesize=PAGE, leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB,
        title="The Constitutions — 24 value traditions as decision criteria",
        author="Constitutional Evals", subject="Provisional anchor constitution set",
    )

    story = [NextPageTemplate("plain")]
    front_matter(s, story, total_criteria)

    # -- table of contents
    story.append(Paragraph(sc("Contents"), s["note_h"]))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("toc0", fontName="Display-Bold", fontSize=7.6, leading=11,
                       textColor=ACCENT, spaceBefore=11, spaceAfter=3),
        ParagraphStyle("toc1", fontName="Body", fontSize=9.6, leading=15.5,
                       textColor=INK, leftIndent=6, firstLineIndent=-6),
    ]
    toc.dotsMinLevel = 1
    story.append(toc)

    n = 0
    current_part = None
    for part, title, d in data:
        if part != current_part:
            current_part = part
            idx = [p for p, _ in PARTS].index(part) + 1
            names = [t for t, _ in next(its for p, its in PARTS if p == part)]
            # part and chapter openers carry no running head, so they get their own
            # template: onPage runs before afterFlowable, so a "body" opener would
            # print the *previous* chapter's title.
            story.append(NextPageTemplate("opener"))
            story.append(PageBreak())
            story.append(Spacer(1, 46 * mm))
            story.append(Paragraph(sc(f"Part {idx}"), s["part_num"]))
            story.append(Paragraph(esc(part), s["part_title"]))
            story.append(Spacer(1, 7 * mm))
            story.append(Paragraph(" &nbsp;&middot;&nbsp; ".join(esc(x) for x in names),
                                   s["part_list"]))
            story.append(NextPageTemplate("body"))

        n += 1
        story.append(NextPageTemplate("opener"))
        story.append(PageBreak())
        story.append(Paragraph(sc(f"{n:02d} of 24"), s["chapter_num"]))
        story.append(Paragraph(esc(title), s["chapter"]))
        story.append(Paragraph(esc(part), s["chapter_part"]))
        story.append(NextPageTemplate("body"))
        story.append(Paragraph(esc(d["overview"]), s["overview"]))

        story.append(Paragraph(sc("Criteria"), s["section"]))
        for i, c in enumerate(d.get("criteria", []), 1):
            story.extend(criterion_flowables(s, f"Criterion {i}", c))

        guides = d.get("guidelines") or []
        if guides:
            story.append(Paragraph(sc("Guidelines — edge cases"), s["section"]))
            for i, g in enumerate(guides, 1):
                story.extend(criterion_flowables(s, f"Guideline {i}", g))

    doc.multiBuild(story)
    print(f"wrote {out}")

    if "--verify" in sys.argv:
        verify(out, data)


def verify(path, data):
    """Re-read the built PDF and confirm no source text was dropped or mangled."""
    import re

    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(path)
    # Read the body region only: the running head and folio would otherwise splice
    # themselves into the middle of any passage that runs across a page break.
    body = "".join(
        doc[i].get_textpage().get_text_bounded(
            left=0, bottom=MB - 7, right=PW, top=PH - MT + 5)
        for i in range(len(doc))
    )
    flat = re.sub(r"\s+", "", body)

    missing, checked = [], 0
    for _, title, d in data:
        blocks = [d["overview"]]
        for c in d.get("criteria", []) + (d.get("guidelines") or []):
            blocks += [c["comparative"], c["reasoning"]] + list(c.get("scenarios", []))
        for b in blocks:
            checked += 1
            if re.sub(r"\s+", "", b) not in flat:
                missing.append((title, b[:70]))

    print(f"verify: {checked} text blocks checked, {len(missing)} missing")
    for m in missing[:20]:
        print("  MISSING", m)
    if missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
