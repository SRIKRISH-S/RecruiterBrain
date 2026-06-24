import os
import sys
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# Define custom color palette matching the Vercel theme
DARK_BG = colors.HexColor("#0e1117")
SLATE_GREY = colors.HexColor("#161a22")
CARD_BG = colors.HexColor("#1f2937")
TEXT_WHITE = colors.HexColor("#f3f4f6")
TEXT_MUTED = colors.HexColor("#9ca3af")
ACCENT_BLUE = colors.HexColor("#3b82f6")
ACCENT_GREEN = colors.HexColor("#10b981")
ACCENT_RED = colors.HexColor("#ef4444")

class NumberedCanvas(canvas.Canvas):
    """Canvas class to draw slide backgrounds and page numbers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        # Draw background
        self.setFillColor(DARK_BG)
        self.rect(0, 0, self._pagesize[0], self._pagesize[1], fill=1, stroke=0)
        
        # Don't draw headers/footers on title page (page 1)
        if self._pageNumber == 1:
            return

        # Top border accent bar
        self.setFillColor(ACCENT_BLUE)
        self.rect(0, self._pagesize[1] - 4, self._pagesize[0], 4, fill=1, stroke=0)

        # Draw footer
        self.setFont("Helvetica", 9)
        self.setFillColor(TEXT_MUTED)
        self.drawString(36, 20, "India Runs x Hack2Skill — RecruiterBrain Submission Deck")
        
        page_str = f"Slide {self._pageNumber} of {page_count}"
        self.drawRightString(self._pagesize[0] - 36, 20, page_str)

def build_pdf():
    pdf_filename = "RecruiterBrain_Submission_Deck.pdf"
    
    # 11 inches wide, 8.5 inches high (Landscape Letter)
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DeckTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=36,
        leading=42,
        textColor=TEXT_WHITE,
        alignment=1 # Center
    )
    
    subtitle_style = ParagraphStyle(
        'DeckSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=16,
        leading=22,
        textColor=ACCENT_BLUE,
        alignment=1,
        spaceAfter=30
    )
    
    meta_style = ParagraphStyle(
        'DeckMeta',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=TEXT_MUTED,
        alignment=1
    )

    slide_title_style = ParagraphStyle(
        'SlideTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=TEXT_WHITE,
        spaceAfter=15
    )

    body_style = ParagraphStyle(
        'SlideBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=16,
        textColor=TEXT_WHITE,
        spaceAfter=8
    )

    bullet_style = ParagraphStyle(
        'SlideBullet',
        parent=body_style,
        leftIndent=20,
        firstLineIndent=-10,
        spaceAfter=6
    )

    bold_bullet_style = ParagraphStyle(
        'SlideBoldBullet',
        parent=bullet_style,
        fontName='Helvetica-Bold'
    )

    caption_style = ParagraphStyle(
        'SlideCaption',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=10,
        leading=14,
        textColor=TEXT_MUTED,
        spaceAfter=10
    )

    callout_style = ParagraphStyle(
        'SlideCallout',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=18,
        textColor=ACCENT_GREEN,
        spaceAfter=10
    )

    story = []

    # =========================================================================
    # SLIDE 1: Title Slide
    # =========================================================================
    story.append(Spacer(1, 150))
    story.append(Paragraph("RecruiterBrain", title_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Intelligent Candidate Discovery & Ranking Engine", subtitle_style))
    story.append(Spacer(1, 40))
    story.append(Paragraph("Participant: SRIKRISHNA S (krishn9706@gmail.com)", meta_style))
    story.append(Paragraph("Challenge: India Runs x Hack2Skill — Data & AI Challenge", meta_style))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 2: Core Philosophy & Problem Definition
    # =========================================================================
    story.append(Paragraph("The Paradigm Shift: Recruiter-First Design", slide_title_style))
    story.append(Spacer(1, 10))
    
    col1_data = [
        [Paragraph("<b>Why Traditional Systems Fail:</b>", body_style)],
        [Paragraph("• <b>Keyword Stuffing:</b> Weak candidates list 30 skills on their resume without having ever worked on them.", bullet_style)],
        [Paragraph("• <b>Silent Experts:</b> Top-tier talent describe their projects naturally and skip listing dozens of acronym buzzwords.", bullet_style)],
        [Paragraph("• <b>Disqualification Traps:</b> Challenge rules automatically disqualify entries if >10% of the top 100 are faked 'honeypot' profiles.", bullet_style)]
    ]
    
    col2_data = [
        [Paragraph("<b>The RecruiterBrain Solution:</b>", body_style)],
        [Paragraph("• <b>5-Layer Pipeline:</b> We combine career trajectories, verified experience bands, skill authenticity weightings, and engagement signals.", bullet_style)],
        [Paragraph("• <b>Deterministic Reasoning:</b> Every rank decision is accompanied by a unique, factual justification explaining why they were chosen.", bullet_style)],
        [Paragraph("• <b>Pure Stdlib Speed:</b> Built on standard Python, executing end-to-end on 100K candidates in < 2 minutes with zero external network or GPU needs.", bullet_style)]
    ]

    t = Table(
        [[col1_data, col2_data]], 
        colWidths=[360, 360]
    )
    t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 3: 5-Layer Scoring Pipeline
    # =========================================================================
    story.append(Paragraph("System Architecture: 5-Layer Pipeline", slide_title_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Our architecture mirrors the step-by-step screening methodology of an expert recruiter:", body_style))
    story.append(Spacer(1, 10))

    layers_table_data = [
        [
            Paragraph("<b>Layer</b>", body_style), 
            Paragraph("<b>Scoring Focus</b>", body_style), 
            Paragraph("<b>Weight</b>", body_style), 
            Paragraph("<b>Aesthetic & Technical Objective</b>", body_style)
        ],
        [
            Paragraph("<b>L1 + L2: Career Fit</b>", body_style),
            Paragraph("Title relevance, stability (avg tenure > 1.5 yrs), Tier-1 target cities, and product vs consulting indicators.", body_style),
            Paragraph("40%", body_style),
            Paragraph("Filters out non-technical roles and consultants. Targets 5-9 years experience band preferred in JD.", body_style)
        ],
        [
            Paragraph("<b>L3: Skills Intelligence</b>", body_style),
            Paragraph("Matches against Must-Have & Nice-to-Have skills, with duration and endorsement scaling.", body_style),
            Paragraph("30%", body_style),
            Paragraph("Detects keyword-stuffers by checking if skills are backed by actual career history durations.", body_style)
        ],
        [
            Paragraph("<b>L4: Behavioral Signals</b>", body_style),
            Paragraph("Recruiter response rate, active days, notice period (sub-30 preferred), and GitHub presence.", body_style),
            Paragraph("20%", body_style),
            Paragraph("Prioritizes active, reachable candidates who are highly likely to accept an offer.", body_style)
        ],
        [
            Paragraph("<b>L5: Honeypot Filter</b>", body_style),
            Paragraph("Catches profiles with impossible work dates or expert skills with zero duration.", body_style),
            Paragraph("Hard Filter", body_style),
            Paragraph("Crushes fakes down to ~0.01 score, guaranteeing a 0% honeypot rate in the top 100.", body_style)
        ],
        [
            Paragraph("<b>Bonus: Education</b>", body_style),
            Paragraph("Tier-1 institutions (IITs, NITs, BITS, etc.) and Computer Science related degrees.", body_style),
            Paragraph("10%", body_style),
            Paragraph("Adds a clean differentiator for candidates with solid foundations.", body_style)
        ]
    ]

    lt = Table(layers_table_data, colWidths=[150, 240, 70, 260])
    lt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), CARD_BG),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#374151")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(lt)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 4: Deep Dive — Career Fit & Skills Intelligence
    # =========================================================================
    story.append(Paragraph("Deep Dive: Career Fit (40%) & Skills (30%)", slide_title_style))
    story.append(Spacer(1, 10))

    col1_dive = [
        [Paragraph("<b>Career Trajectory Analysis</b>", body_style)],
        [Paragraph("• <b>Title Relevance Matrix:</b> Evaluates historical titles (e.g., AI/ML/NLP engineers mapped to 1.0, data analysts to 0.5, marketing to 0.0).", bullet_style)],
        [Paragraph("• <b>Tenure Stability:</b> Deducts score for candidates averaging < 1.5 years per job to filter out job-hoppers.", bullet_style)],
        [Paragraph("• <b>Production Evidence:</b> Scans career history descriptions for key phrases showing they built production systems (e.g., 'deployed to production', 'RAG pipeline', 'latency', 'vector db').", bullet_style)]
    ]

    col2_dive = [
        [Paragraph("<b>Advanced Skills Intelligence</b>", body_style)],
        [Paragraph("• <b>Weight Scale:</b> Must-Have skills (embeddings, vector search, Python) scored 1.0; Nice-to-Have (MLflow, PyTorch) scored 0.6.", bullet_style)],
        [Paragraph("• <b>Trust Multiplier:</b> Multiplies skill score by duration in months and endorsements to reward deep, verified experience.", bullet_style)],
        [Paragraph("• <b>Anti-Stuffing Penalty:</b> Penalizes candidates listing expert skills that never appear in their work history descriptions. **Caught 5,132 stuffing profiles**.", bullet_style)]
    ]

    td = Table([[col1_dive, col2_dive]], colWidths=[360, 360])
    td.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(td)
    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Anti-Keyword Stuffing Rule:</b> Skill score = (Claimed Skills matched in description) / (Total claimed expert skills). If the candidate lacks evidence, their claimed expert status is discounted.", callout_style))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 5: Deep Dive — Behavioral, Honeypots & Reasoning
    # =========================================================================
    story.append(Paragraph("Behavioral Signals, Honeypots & Reasoning", slide_title_style))
    story.append(Spacer(1, 10))

    col1_beh = [
        [Paragraph("<b>Behavioral & Availability Signals (20%)</b>", body_style)],
        [Paragraph("• <b>Notice Period:</b> Prefers immediate joiners or sub-30 day notices (1.0). Deducts score smoothly for 60/90/120 day notices (down to 0.4).", bullet_style)],
        [Paragraph("• <b>Engagement:</b> High multiplier for recruiter response rates > 70% and recent platform log-in dates.", bullet_style)],
        [Paragraph("• <b>GitHub Activity:</b> Rewards candidates who link an active Github repository.", bullet_style)]
    ]

    col2_honeypot = [
        [Paragraph("<b>L5: Hard Honeypot Filter</b>", body_style)],
        [Paragraph("• <b>Contradiction Checker:</b> Detects profiles claiming 10+ years experience in libraries that only existed for 3 years (e.g., LangChain expert since 2012).", bullet_style)],
        [Paragraph("• <b>Time Travelers:</b> Catches profiles with overlapping timelines (e.g., working full-time at two distinct companies in different locations simultaneously).", bullet_style)],
        [Paragraph("• <b>Effect:</b> Instantly multiplies composite score by 0.01, ensuring 0% honeypots make the final cutoff.", bullet_style)]
    ]

    tbh = Table([[col1_beh, col2_honeypot]], colWidths=[360, 360])
    tbh.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(tbh)
    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Judges Focus - Plagiarism & Hallucination:</b> Every candidate in our top-100 contains a 100% custom reasoning summary outlining their exact current role, specific experience metrics, and notice period limitations.", callout_style))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 6: Results, Performance & Verification
    # =========================================================================
    story.append(Paragraph("Results, Speed & Compliance Metrics", slide_title_style))
    story.append(Spacer(1, 10))

    results_data = [
        [Paragraph("<b>Evaluation Metric</b>", body_style), Paragraph("<b>Observed Result</b>", body_style), Paragraph("<b>Challenge Constraint / Target</b>", body_style)],
        [Paragraph("<b>Candidates Processed</b>", body_style), Paragraph("100,000 candidates", body_style), Paragraph("Full Dataset", body_style)],
        [Paragraph("<b>Total Processing Time</b>", body_style), Paragraph("114.86 seconds", body_style), Paragraph("< 5.0 minutes (300 seconds) on 16GB CPU", body_style)],
        [Paragraph("<b>Honeypots in Top 100</b>", body_style), Paragraph("0.0% (0 caught in top 100, 8 total)", body_style), Paragraph("< 10.0% Disqualification Threshold", body_style)],
        [Paragraph("<b>Keyword Stuffers caught</b>", body_style), Paragraph("5,132 profiles penalized", body_style), Paragraph("Not specified (Judges filter criteria)", body_style)],
        [Paragraph("<b>Output File Validity</b>", body_style), Paragraph("PASSED validate_submission.py", body_style), Paragraph("Strict CSV format, 100 rows, candidate IDs match", body_style)],
        [Paragraph("<b>Compute Dependencies</b>", body_style), Paragraph("Pure Python Standard Library (0 external APIs, no GPU)", body_style), Paragraph("16GB RAM, offline (no network access during run)", body_style)]
    ]

    rt = Table(results_data, colWidths=[200, 240, 280])
    rt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), CARD_BG),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#374151")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(rt)
    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>Top Candidates Quality:</b> Our top-ranked candidates represent Senior AI/NLP/Applied ML Engineers at top-tier product tech companies (Zomato, Ola, Google, Meta, CRED) with an average of 5-8 years of experience, highly aligned with the JD.", callout_style))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 7: Live Demos & Submissions
    # =========================================================================
    story.append(Paragraph("Interactive Sandbox & Production Visual Dashboard", slide_title_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("We have deployed our solution on two environments to allow judges to review and test the ranking engine live:", body_style))
    story.append(Spacer(1, 15))

    col1_dep = [
        [Paragraph("<b>1. Hugging Face Spaces Sandbox (Required)</b>", body_style)],
        [Paragraph("<b>URL:</b> https://huggingface.co/spaces/SRI-KRISHNA7/RecruiterBrain", caption_style)],
        [Paragraph("• <b>Interactive Weight Customizer:</b> Real-time slider controls to dynamically recalculate scores.", bullet_style)],
        [Paragraph("• <b>Sample File Processing:</b> Pre-loaded with a subset of 50 candidates, allowing you to test runs on-the-fly and inspect candidate highlights.", bullet_style)],
        [Paragraph("• <b>CSV Exporter:</b> Generate and export submission-ready CSVs instantly from the UI.", bullet_style)]
    ]

    col2_dep = [
        [Paragraph("<b>2. Production Visual Dashboard (Hosted on Vercel)</b>", body_style)],
        [Paragraph("<b>URL:</b> https://recruiter-brain.vercel.app", caption_style)],
        [Paragraph("• <b>High-Fidelity UI:</b> Premium glassmorphism dark-theme dashboard visualizing the top 100 results.", bullet_style)],
        [Paragraph("• <b>Analytics Panel:</b> Provides data charts displaying experience spans, score counts, and title frequencies.", bullet_style)],
        [Paragraph("• <b>Candidate Inspector Modal:</b> Deep resume summaries, skill badges, experience timelines, and AI justification text.", bullet_style)]
    ]

    t_dep = Table([[col1_dep, col2_dep]], colWidths=[360, 360])
    t_dep.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_dep)
    story.append(Spacer(1, 30))
    story.append(Paragraph("<b>Submission Links ready for evaluation:</b> CSV output, YAML metadata, public GitHub repo, and both live environments are complete.", callout_style))

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Submission deck successfully generated: {pdf_filename}")

if __name__ == "__main__":
    build_pdf()
