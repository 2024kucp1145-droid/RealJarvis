# -*- coding: utf-8 -*-
"""
generate_first_time_manual.py
==============================
Creates a First-Time User Action Manual (Scenario-Driven: "Agar ye bologe/karoge -> toh Jarvis ye karega").
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas

PDF_OUTPUT_PATH = os.path.join(os.path.expanduser("~"), "Desktop", "JARVIS_First_Time_User_Manual.pdf")
LOCAL_COPY_PATH = os.path.join(os.path.dirname(__file__), "JARVIS_First_Time_User_Manual.pdf")


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

        if self._pageNumber > 1:
            self.drawString(54, 750, "📘 JARVIS FIRST-TIME USER ACTION MANUAL — 'KAISE USE KAREIN'")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.75)
            self.line(54, 742, 558, 742)

        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.75)
        self.line(54, 45, 558, 45)

        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_str)
        self.drawString(54, 32, "Jarvis AI Companion — Complete Beginner & Action Guide")
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

    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=22, leading=26,
        textColor=colors.HexColor("#0F172A"), spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=11, leading=15,
        textColor=colors.HexColor("#0284C7"), spaceAfter=12
    )

    h1_style = ParagraphStyle(
        'H1', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=13, leading=16,
        textColor=colors.HexColor("#0F172A"), spaceBefore=12, spaceAfter=6,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9, leading=13,
        textColor=colors.HexColor("#334155"), spaceAfter=4
    )

    code_style = ParagraphStyle(
        'CodeText', parent=styles['Normal'],
        fontName='Courier-Bold', fontSize=8.5, leading=11,
        textColor=colors.HexColor("#0284C7")
    )

    table_cell_style = ParagraphStyle(
        'TableCell', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, leading=11.5,
        textColor=colors.HexColor("#1E293B")
    )

    table_header_style = ParagraphStyle(
        'TableHeader', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=9, leading=12,
        textColor=colors.white
    )

    callout_style = ParagraphStyle(
        'Callout', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9, leading=13,
        textColor=colors.HexColor("#0F766E")
    )

    story = []

    # TITLE
    story.append(Paragraph("📘 JARVIS FIRST-TIME USER MANUAL", title_style))
    story.append(Paragraph("Aapka Complete 'Kaise Use Karein' Guide: Agar aap ye bologe ya karoge -> toh Jarvis ye karega!", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284C7"), spaceAfter=10))

    # STARTUP BOX
    intro_box = (
        "<b>🚀 PEHLI BAAR START KAISE KAREIN:</b><br/>"
        "1. Terminal kholiye aur type karein: <code>cd C:\\RealJarvis_v2\\RealJarvis</code><br/>"
        "2. Run karein: <code>venv\\Scripts\\python.exe main.py</code><br/>"
        "3. Screen par Jarvis ka floating animated widget aa jayega. Bas mic par <b>'Jarvis'</b> boliye aur baat karna shuru karein!"
    )
    story.append(Table([[Paragraph(intro_box, callout_style)]],
                       colWidths=[504],
                       style=[
                           ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F0FDFA")),
                           ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#99F6E4")),
                           ('PADDING', (0, 0), (-1, -1), 7),
                       ]))
    story.append(Spacer(1, 10))

    # =========================================================================
    # 1. BASIC CONVERSATION & WAKE
    # =========================================================================
    story.append(Paragraph("1. Jarvis Ko Jagana Aur Baat Karna", h1_style))
    t1_data = [
        [Paragraph("Agar aap YE KAROGE ya BOLOGE...", table_header_style), Paragraph("Toh Jarvis YE KAREGA...", table_header_style), Paragraph("Real-Life Example", table_header_style)],
        [
            Paragraph("Bolo: <b>'Jarvis'</b>", code_style),
            Paragraph("Jarvis mic chalu karke blue eye mein convert ho jayegi aur aapki baat sunegi.", table_cell_style),
            Paragraph("'Jarvis, aaj mausam kaisa hai?'", table_cell_style)
        ],
        [
            Paragraph("Do baar <b>taali (clap)</b> bajao", code_style),
            Paragraph("Bina kuch bole taali ki aawaz se Jarvis wake up ho jayegi.", table_cell_style),
            Paragraph("Jab aap laptop se thoda door baithe hon.", table_cell_style)
        ],
        [
            Paragraph("Jarvis bol rahi ho aur aap <b>beech mein bol padho</b> (Barge-in)", code_style),
            Paragraph("Jarvis turant bolna band kar degi aur aapki nayi baat sunne lagegi.", table_cell_style),
            Paragraph("Agar Jarvis lambi kahani sunane lage toh bas bolo 'ruko'.", table_cell_style)
        ],
        [
            Paragraph("Bolo: <b>'So jao'</b> ya <b>'Band ho jao'</b>", code_style),
            Paragraph("Jarvis apni aankhein band karke sleeping mode mein chali jayegi.", table_cell_style),
            Paragraph("Jab aapko koi disturb nahi chahiye.", table_cell_style)
        ],
        [
            Paragraph("Bolo: <b>'Chat mode on'</b>", code_style),
            Paragraph("Floating icon ek dark text chat window mein badal jayega jahan aap type karke chat kar sakte hain.", table_cell_style),
            Paragraph("Jab mic use nahi karna ho aur typing karni ho.", table_cell_style)
        ],
    ]
    t1 = Table(t1_data, colWidths=[160, 200, 144])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t1)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 2. PROACTIVE ACTIONS (BINA KUCH BOLE JARVIS KYA KAREGA)
    # =========================================================================
    story.append(Paragraph("2. Proactive Actions: Jab aap kuch karenge, Jarvis bina puche khud kya karega", h1_style))
    t2_data = [
        [Paragraph("Jab AAP laptop par YE KAROGE...", table_header_style), Paragraph("Toh JARVIS background mein YE KAREGA...", table_header_style), Paragraph("Aapko Aage KYA BOLNA HAI...", table_header_style)],
        [
            Paragraph("Kisi code mein error ho aur aapne use <b>Ctrl+C (Copy)</b> kiya", code_style),
            Paragraph("Jarvis error detect karke background mein fix karegi, theek code clipboard par daalegi aur bolegi: <i>'Maine code fix kar diya hai.'</i>", table_cell_style),
            Paragraph("Bolo: <b>'replace karo'</b> ya <b>'paste karo'</b> → Seedha theek code cursor par paste ho jayega.", code_style)
        ],
        [
            Paragraph("Charger connect ya disconnect karoge", code_style),
            Paragraph("<b>1 second ke andar</b> Jarvis bolegi: <i>'Charger connect ho gaya hai'</i> ya <i>'Charger disconnect ho gaya hai'</i>.", table_cell_style),
            Paragraph("Kuch nahi bolna, bas status confirm hoga.", table_cell_style)
        ],
        [
            Paragraph("Battery <b>25% se 30% ke beech</b> aa gayi aur charger nahi laga", code_style),
            Paragraph("Jarvis warning degi: <i>'Boss, battery 28% par hai. Laptop 25% par lock hota hai, please charger lagaiye.'</i>", table_cell_style),
            Paragraph("Charger connect kar lijiye taaki laptop band na ho.", table_cell_style)
        ],
        [
            Paragraph("Internet se koi <b>PDF / ZIP / App download</b> ki", code_style),
            Paragraph("Download complete hote hi bolegi: <i>'Aapne [File Name] download kiya hai, kya ise open ya organize kar doon?'</i>", table_cell_style),
            Paragraph("Bolo: <b>'open karo'</b> (file khulegi), <b>'organize karo'</b> (folder mein jayegi), <b>'extract karo'</b> (unzip hogi).", code_style)
        ],
        [
            Paragraph("College/Exam/Job ka koi <b>urgent email</b> aaya", code_style),
            Paragraph("Jarvis alert bolegi: <i>'Boss, [Subject] par urgent email aaya hai.'</i>", table_cell_style),
            Paragraph("Bolo: <b>'haan sunao'</b> (2-line summary degi), <b>'inbox kholo'</b> (Gmail khulega).", code_style)
        ],
        [
            Paragraph("Zoom / Google Meet call start hui", code_style),
            Paragraph("Jarvis <b>Meeting Shield ON</b> karke poori tarah silent ho jayegi taaki meeting mein aawaz na jaye.", table_cell_style),
            Paragraph("Meeting khatam hone par normal ho jayegi.", table_cell_style)
        ],
        [
            Paragraph("Terminal mein koi library missing aayi (e.g. <code>ModuleNotFoundError: fastapi</code>)", code_style),
            Paragraph("Jarvis bolega: <i>'fastapi library missing hai. Kya main install kar doon?'</i>", table_cell_style),
            Paragraph("Bolo: <b>'haan install karo'</b> → Background mein `pip install` chal jayega.", code_style)
        ],
    ]
    t2 = Table(t2_data, colWidths=[150, 190, 164])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0369A1")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t2)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 3. DAILY CODING, STUDY & MEDIA VOICE ACTIONS
    # =========================================================================
    story.append(PageBreak())
    story.append(Paragraph("3. Daily Workflows: Bolkar Kaam Karwane Ka Cheatsheet", h1_style))
    t3_data = [
        [Paragraph("Situation / Kaam", table_header_style), Paragraph("Aapko YE BOLNA HAI...", table_header_style), Paragraph("Jarvis KYA KAREGA...", table_header_style)],
        # LeetCode
        [
            Paragraph("<b>LeetCode question par atke hain</b>", table_cell_style),
            Paragraph("<b>'hint do'</b> ya <b>'approach kya hogi'</b>", code_style),
            Paragraph("Screen dekhkar bina full answer spoil kiye 2 line ka smart algorithm intuition bolegi.", table_cell_style)
        ],
        [
            Paragraph("<b>Lamba Article ya Docs padhna hai</b>", table_cell_style),
            Paragraph("<b>'page samjhao'</b> ya <b>'summary sunao'</b>", code_style),
            Paragraph("Screen padhkar 3 bullet points mein bolkar samjha degi.", table_cell_style)
        ],
        [
            Paragraph("<b>YouTube par video dekh rahe hain</b>", table_cell_style),
            Paragraph("<b>'10 second aage karo'</b> / <b>'peeche karo'</b><br/><b>'video speed badhao'</b><br/><b>'subtitles on karo'</b><br/><b>'theater mode'</b>", code_style),
            Paragraph("Bina keyboard touch kiye video forward/rewind, 1.5x/2x speed aur captions switch karegi.", table_cell_style)
        ],
        [
            Paragraph("<b>Desktop par bohot saari files bikhari hain</b>", table_cell_style),
            Paragraph("<b>'desktop organize karo'</b>", code_style),
            Paragraph("Sabhi files ko Documents, Code, Screenshots, Videos, Archives folders mein auto-sort kar degi.", table_cell_style)
        ],
        [
            Paragraph("<b>Downloads mein bohot kachra ho gaya hai</b>", table_cell_style),
            Paragraph("<b>'purani files saaf karo'</b>", code_style),
            Paragraph("30 din se purani heavy files dhoondhkar puchegi aur Recycle Bin mein safe move karegi.", table_cell_style)
        ],
        [
            Paragraph("<b>Port 3000 / 8000 busy aa raha hai</b>", table_cell_style),
            Paragraph("<b>'port 3000 free karo'</b>", code_style),
            Paragraph("Port 3000 ke ghost background process ko dhoondhkar kill kar degi.", table_cell_style)
        ],
        [
            Paragraph("<b>Din bhar ka code Git par save karna hai</b>", table_cell_style),
            Paragraph("<b>'aaj ka kaam save karo'</b>", code_style),
            Paragraph("Git changes dekhkar AI se meaningful commit message banakar repo commit karegi.", table_cell_style)
        ],
        [
            Paragraph("<b>Jarvis ko apna naya routine sikhana hai</b>", table_cell_style),
            Paragraph("<b>'jab main boloon morning setup toh spotify aur vs code kholo'</b>", code_style),
            Paragraph("Jarvis ise yaad kar legi! Agli baar bas 'morning setup' bolo, dono khul jayenge.", table_cell_style)
        ],
        [
            Paragraph("<b>System health aur status janna hai</b>", table_cell_style),
            Paragraph("<b>'apna health check karo'</b>", code_style),
            Paragraph("Sabhi 10 sentries, battery aur memory ko test karke full status debrief bolegi.", table_cell_style)
        ],
    ]
    t3 = Table(t3_data, colWidths=[150, 180, 174])
    t3.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t3)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 4. FIRST-DAY SUMMARY BOX
    # =========================================================================
    story.append(Paragraph("4. Pehle Din Ka Quick Checklist", h1_style))
    summary_box = (
        "<b>💡 PRO-TIPS FOR BEST EXPERIENCE:</b><br/>"
        "• <b>Natural boliye</b> — Hindi, English, ya Hinglish kisi mein bhi baat karein.<br/>"
        "• <b>Bejhijhak rokiye</b> — Agar Jarvis bol rahi hai aur aapko kuch aur chahiye, beech mein bol dijiye (Barge-in on hai).<br/>"
        "• <b>Background mein chalne dein</b> — Jarvis ko start karke minimize kar dein, wo background mein silent guardian ki tarah aapke hardware aur files ka dhyan rakhegi!"
    )
    story.append(Table([[Paragraph(summary_box, body_style)]],
                       colWidths=[504],
                       style=[
                           ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                           ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                           ('PADDING', (0, 0), (-1, -1), 8),
                       ]))

    # BUILD DOCUMENT
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[First-Time User Manual generated at: {PDF_OUTPUT_PATH}]")

    try:
        import shutil
        shutil.copyfile(PDF_OUTPUT_PATH, LOCAL_COPY_PATH)
        print(f"[Local copy created at: {LOCAL_COPY_PATH}]")
    except Exception:
        pass


if __name__ == "__main__":
    build_pdf()
