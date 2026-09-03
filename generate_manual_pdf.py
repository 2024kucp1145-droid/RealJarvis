# -*- coding: utf-8 -*-
"""
generate_manual_pdf.py
=======================
Generates a comprehensive, beautifully styled PDF User Manual for RealJarvis AI Assistant.
"""

import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

PDF_OUTPUT_PATH = os.path.join(os.path.expanduser("~"), "Desktop", "JARVIS_Complete_User_Manual.pdf")
LOCAL_COPY_PATH = os.path.join(os.path.dirname(__file__), "JARVIS_Complete_User_Manual.pdf")


class NumberedCanvas(canvas.Canvas):
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
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#64748B"))

        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "🤖 REAL JARVIS v2.0 — ULTIMATE OPERATIONAL USER MANUAL")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.75)
            self.line(54, 742, 558, 742)

        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.75)
        self.line(54, 45, 558, 45)

        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_str)
        self.drawString(54, 32, "Confidential — DeepMind / Personal AI Companion Engine")
        self.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        PDF_OUTPUT_PATH,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0284C7"),
        spaceAfter=14
    )

    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#0369A1"),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#334155"),
        spaceAfter=6
    )

    bold_body_style = ParagraphStyle(
        'BoldBody',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    code_style = ParagraphStyle(
        'CodeText',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0284C7")
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#1E293B")
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.white
    )

    callout_style = ParagraphStyle(
        'Callout',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0F766E")
    )

    story = []

    # =========================================================================
    # TITLE & HEADER
    # =========================================================================
    story.append(Paragraph("🤖 REAL JARVIS AI — COMPLETE USER MANUAL", title_style))
    story.append(Paragraph("A to Z Operating Guide, 10 Autonomous Proactive Sentries & Full Voice Commands", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284C7"), spaceAfter=14))

    # Architecture Overview Callout Box
    arch_summary = (
        "<b>SYSTEM ARCHITECTURE OVERVIEW:</b><br/>"
        "RealJarvis v2.0 is a 39-module, full-stack Windows Autonomous AI Companion. "
        "It operates via a multi-threaded daemon architecture featuring <b>10 Proactive Background Sentries</b>, "
        "real-time streaming Text-to-Speech (Edge-TTS `hi-IN-SwaraNeural`), Gemini 2.0 Flash multimodal vision, "
        "Windows Kernel Level hardware monitoring (0.8s AC status), eye-tracking, and autonomous self-evolution."
    )
    story.append(Table([[Paragraph(arch_summary, callout_style)]],
                       colWidths=[504],
                       style=[
                           ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F0FDFA")),
                           ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#99F6E4")),
                           ('PADDING', (0, 0), (-1, -1), 8),
                       ]))
    story.append(Spacer(1, 12))

    # =========================================================================
    # SECTION 1: VOICE & INTERACTION PIPELINE
    # =========================================================================
    story.append(Paragraph("1. Voice & Interaction System", h1_style))
    voice_data = [
        [Paragraph("Feature", table_header_style), Paragraph("How to Trigger / Use", table_header_style), Paragraph("Internal Behavior", table_header_style)],
        [Paragraph("<b>Wake Word</b>", table_cell_style), Paragraph("Say <b>'Jarvis'</b>", code_style), Paragraph("Instant live microphone listening with animated visual orb.", table_cell_style)],
        [Paragraph("<b>Barge-In (Interruption)</b>", table_cell_style), Paragraph("Speak while Jarvis is talking", code_style), Paragraph("Audio stream unloads instantly with zero delay; mic resumes listening.", table_cell_style)],
        [Paragraph("<b>Clap Detection</b>", table_cell_style), Paragraph("Clap twice consecutively", code_style), Paragraph("Audio energy threshold trigger activates wake pipeline.", table_cell_style)],
        [Paragraph("<b>Sleep / Mute</b>", table_cell_style), Paragraph("'So jao' / 'Band ho jao'", code_style), Paragraph("GUI eyes close (`sleeping` state); proactive alerts paused.", table_cell_style)],
        [Paragraph("<b>Dictation Mode</b>", table_cell_style), Paragraph("'Likhna shuru karo'", code_style), Paragraph("Speech is directly typed into active cursor location in real time.", table_cell_style)],
        [Paragraph("<b>Chat Mode Window</b>", table_cell_style), Paragraph("'Chat mode on' / 'off'", code_style), Paragraph("Expands floating widget into modern dark glass text chat window.", table_cell_style)],
    ]
    t_voice = Table(voice_data, colWidths=[120, 160, 224])
    t_voice.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_voice)
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 2: 10 AUTONOMOUS PROACTIVE SENTRIES (THE CORE ENGINE)
    # =========================================================================
    story.append(Paragraph("2. The 10 Autonomous Proactive Sentries", h1_style))
    story.append(Paragraph("Jarvis runs 10 autonomous background sentries that monitor your desktop, hardware, and code without requiring manual commands:", body_style))

    sentries_data = [
        [Paragraph("Phase & Sentry", table_header_style), Paragraph("Superpower & Functionality", table_header_style), Paragraph("Voice Commands / Actions", table_header_style)],
        [
            Paragraph("<b>Phase 1: Code & Error Auto-Guardian</b>", table_cell_style),
            Paragraph("Silently inspects copied code. If syntax/logic error is found, auto-fixes in background and replaces clipboard content with clean code.", table_cell_style),
            Paragraph("<b>'replace karo'</b> / <b>'paste karo'</b> → Types fixed code directly at cursor.", code_style)
        ],
        [
            Paragraph("<b>Phase 2: Hardware & Battery Sentry</b>", table_cell_style),
            Paragraph("<b>0.8s Kernel Level</b> AC plug/unplug detection. Alerts on continuous <b>25%–30% danger zone</b> (laptop lock prevention), 100% full charge, and RAM choke (>88%).", table_cell_style),
            Paragraph("<b>'haan close karo'</b> → Kills top memory-hogging process via PID.", code_style)
        ],
        [
            Paragraph("<b>Phase 3: Health & Focus Coach</b>", table_cell_style),
            Paragraph("<b>20-20-20 Eye Strain Guard</b>, 50-minute deep work hydration reminder, late-night (1AM–5AM) overwork sentry, and native Windows idle detection.", table_cell_style),
            Paragraph("<b>'mera focus time batao'</b> / <b>'kitni der se kaam kar raha hoon'</b>", code_style)
        ],
        [
            Paragraph("<b>Phase 4: Proactive Download Janitor</b>", table_cell_style),
            Paragraph("Multi-directory real-time watcher (Downloads, Telegram, Desktop). Auto-detects completed PDFs, ZIPs, Code, and Installers within 1.8s.", table_cell_style),
            Paragraph("<b>'open karo'</b> (Launch)<br/><b>'organize karo'</b> (Move to Category)<br/><b>'extract karo'</b> (Unzip archive)", code_style)
        ],
        [
            Paragraph("<b>Phase 5: Urgent Email Sentry</b>", table_cell_style),
            Paragraph("Silent IMAP background checker with AI Urgency Filter. Filters spam/marketing; alerts ONLY on College notices, Exams, Placements & Security alerts.", table_cell_style),
            Paragraph("<b>'haan sunao'</b> (2-sentence summary)<br/><b>'inbox kholo'</b> (Open Gmail)", code_style)
        ],
        [
            Paragraph("<b>Phase 6: Workspace Harmonizer</b>", table_cell_style),
            Paragraph("<b>Meeting & Class Shield</b>: Auto-detects Zoom, Google Meet, MS Teams calls and mutes all proactive audio. Adapts to coding/study workflows.", table_cell_style),
            Paragraph("<b>'coding mode on'</b><br/><b>'study mode on'</b><br/><b>'meeting mode on/off'</b>", code_style)
        ],
        [
            Paragraph("<b>Phase 7: Web Workflow Assistant</b>", table_cell_style),
            Paragraph("<b>LeetCode Hint Master</b>: Gives algorithmic intuition without spoilers. Webpage 3-bullet summarizer. Zero-click YouTube controls.", table_cell_style),
            Paragraph("<b>'hint do'</b> / <b>'approach kya hogi'</b><br/><b>'page samjhao'</b><br/><b>'10 second aage/peeche'</b>", code_style)
        ],
        [
            Paragraph("<b>Phase 8: Project & Git Auto-Doctor</b>", table_cell_style),
            Paragraph("Auto-detects `ModuleNotFoundError` on clipboard (offers 1-word pip install). Kills ghost processes on Port 3000/8000. AI Git commit from diff.", table_cell_style),
            Paragraph("<b>'aaj ka kaam save karo'</b><br/><b>'git status batao'</b><br/><b>'port 3000 free karo'</b>", code_style)
        ],
        [
            Paragraph("<b>Phase 9: Desktop Janitor & Cleanup</b>", table_cell_style),
            Paragraph("Auto-sorts messy Desktop files into categorized subfolders. Scans 30-day+ old download files for safe Recycle Bin purge. Duplicate finder.", table_cell_style),
            Paragraph("<b>'desktop organize karo'</b><br/><b>'purani files saaf karo'</b><br/><b>'disk space batao'</b>", code_style)
        ],
        [
            Paragraph("<b>Phase 10: Autonomous Evolution</b>", table_cell_style),
            Paragraph("Multi-step complex mission planner. Voice-learned custom macros saved to persistent JSON. Autonomous 10-sentry system health diagnostic.", table_cell_style),
            Paragraph("<b>'jab main boloon X toh Y karo'</b><br/><b>'system diagnostic chalao'</b><br/><b>'apni routines batao'</b>", code_style)
        ],
    ]

    t_sentries = Table(sentries_data, colWidths=[125, 220, 159])
    t_sentries.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0369A1")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_sentries)
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 3: MASTER VOICE COMMANDS DIRECTORY
    # =========================================================================
    story.append(PageBreak())
    story.append(Paragraph("3. Master Voice Commands Directory", h1_style))
    story.append(Paragraph("Complete reference of vocal commands recognized natively by Jarvis:", body_style))

    commands_data = [
        [Paragraph("Category", table_header_style), Paragraph("Spoken Voice Triggers", table_header_style), Paragraph("Action Performed", table_header_style)],
        # System & Hardware
        [Paragraph("<b>Hardware & Power</b>", table_cell_style), Paragraph("'battery batao', 'charger lag gaya', 'kitna charge hai'", code_style), Paragraph("Reports battery percentage, remaining time, and AC status.", table_cell_style)],
        [Paragraph("<b>Volume & Brightness</b>", table_cell_style), Paragraph("'volume badhao', 'volume kam karo', 'mute karo', 'brightness 70 percent karo'", code_style), Paragraph("Adjusts Windows system master volume and screen backlight.", table_cell_style)],
        [Paragraph("<b>Time & Date</b>", table_cell_style), Paragraph("'time kya hua', 'aaj ki date kya hai'", code_style), Paragraph("Speaks formatted local time and date.", table_cell_style)],
        # Developer & Git
        [Paragraph("<b>Coding & LeetCode</b>", table_cell_style), Paragraph("'hint do', 'approach kya hogi', 'code likh do', 'solution likho'", code_style), Paragraph("Inspects problem on screen; gives mentor hint or types full solution.", table_cell_style)],
        [Paragraph("<b>Git & Version Control</b>", table_cell_style), Paragraph("'git commit karo', 'aaj ka kaam save karo', 'git status batao'", code_style), Paragraph("Inspects git diff, writes AI conventional commit, and commits changes.", table_cell_style)],
        [Paragraph("<b>Port & Server Cleanup</b>", table_cell_style), Paragraph("'port 3000 free karo', 'port 8000 clean karo', 'port 5000 kill karo'", code_style), Paragraph("Finds listening PID on port and terminates process via taskkill.", table_cell_style)],
        # Web & Media
        [Paragraph("<b>Webpage Summarizer</b>", table_cell_style), Paragraph("'page samjhao', 'summary sunao', 'kya likha hai short mein'", code_style), Paragraph("Reads active screen article and speaks 3-bullet executive summary.", table_cell_style)],
        [Paragraph("<b>YouTube Controls</b>", table_cell_style), Paragraph("'10 second aage', '10 second peeche', 'speed 1.5x karo', 'subtitles on karo', 'theater mode'", code_style), Paragraph("Executes zero-click native YouTube player keyboard hotkeys.", table_cell_style)],
        # Desktop & File Cleanup
        [Paragraph("<b>Desktop Cleanup</b>", table_cell_style), Paragraph("'desktop organize karo', 'desktop saaf karo'", code_style), Paragraph("Sorts Desktop into Documents, Code, Screenshots, Videos, Archives.", table_cell_style)],
        [Paragraph("<b>Downloads Purge</b>", table_cell_style), Paragraph("'purani files saaf karo', 'downloads clean karo'", code_style), Paragraph("Identifies 30+ day old large files and safely moves to Recycle Bin.", table_cell_style)],
        [Paragraph("<b>Disk Space Analysis</b>", table_cell_style), Paragraph("'disk space batao', 'laptop mein kitna space bacha hai'", code_style), Paragraph("Reports total/free C: space and top 3 largest user directories.", table_cell_style)],
        # Health & Self-Evolution
        [Paragraph("<b>Focus & Ergonomics</b>", table_cell_style), Paragraph("'mera focus time batao', 'kitni der se kaam kar raha hoon'", code_style), Paragraph("Speaks uninterrupted active work duration (excludes idle time).", table_cell_style)],
        [Paragraph("<b>Teach New Routine</b>", table_cell_style), Paragraph("'jab main boloon morning setup toh spotify aur vs code kholo'", code_style), Paragraph("Stores custom voice macro into persistent memory.", table_cell_style)],
        [Paragraph("<b>Health Diagnostics</b>", table_cell_style), Paragraph("'apna health check karo', 'system diagnostic chalao'", code_style), Paragraph("Audits all 10 subsystems and reports live operational readiness.", table_cell_style)],
    ]

    t_cmds = Table(commands_data, colWidths=[110, 210, 184])
    t_cmds.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_cmds)
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 4: CONFIGURATION, STARTUP & MAINTENANCE
    # =========================================================================
    story.append(Paragraph("4. Configuration & Startup Guide", h1_style))
    config_text = (
        "<b>Starting Jarvis:</b><br/>"
        "1. Open terminal in project folder: <code>C:\\RealJarvis_v2\\RealJarvis</code><br/>"
        "2. Activate virtual environment: <code>venv\\Scripts\\activate</code><br/>"
        "3. Launch Jarvis: <code>python main.py</code><br/><br/>"
        "<b>Key Configuration Settings (<code>config.py</code>):</b><br/>"
        "• <code>ASSISTANT_NAME</code> = 'Jarvis' (Wake word)<br/>"
        "• <code>ONLINE_VOICE</code> = 'hi-IN-SwaraNeural' (Natural Indian English/Hinglish TTS)<br/>"
        "• <code>BARGE_IN_ENABLED</code> = True (Allows interrupting speech anytime)<br/>"
        "• <code>BATTERY_DANGER_MIN</code> = 25, <code>BATTERY_DANGER_MAX</code> = 30 (Continuous alert range)<br/>"
        "• <code>GEMINI_API_KEY</code> = Set in <code>.env</code> for vision & reasoning capabilities."
    )
    story.append(Table([[Paragraph(config_text, body_style)]],
                       colWidths=[504],
                       style=[
                           ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
                           ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                           ('PADDING', (0, 0), (-1, -1), 8),
                       ]))

    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[PDF Generated successfully at: {PDF_OUTPUT_PATH}]")

    # Also copy locally
    try:
        import shutil
        shutil.copyfile(PDF_OUTPUT_PATH, LOCAL_COPY_PATH)
        print(f"[Local copy created at: {LOCAL_COPY_PATH}]")
    except Exception as e:
        print(f"[Copy error: {e}]")


if __name__ == "__main__":
    build_pdf()
