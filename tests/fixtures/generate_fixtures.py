"""
generate_fixtures.py - Demo fixture generator for SovereignForge

Generates realistic sample files for the hackathon demo:
  1. sample_inspection_report.pdf  - scanned-style electrical inspection report
  2. sample_pid_diagram.png        - P&ID (Piping & Instrumentation Diagram)
  3. sample_sop.txt                - Standard Operating Procedure (for KB ingestion)
  4. sample_board_brief.txt        - Board briefing document
  5. sample_code_problem.py        - Sample code for sandbox demo

Run: python tests/fixtures/generate_fixtures.py
"""
import os
import sys
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


# ─────────────────────────────────────────────────────────────────────────────
#  1. Generate PDF - Electrical Inspection Report
# ─────────────────────────────────────────────────────────────────────────────

def generate_inspection_pdf():
    try:
        from fpdf import FPDF
    except ImportError:
        print("  [SKIP] fpdf2 not installed - using text fallback")
        _generate_inspection_txt()
        return

    class InspectionPDF(FPDF):
        def header(self):
            self.set_fill_color(0, 51, 102)
            self.rect(0, 0, 210, 18, "F")
            self.set_font("Helvetica", "B", 14)
            self.set_text_color(255, 255, 255)
            self.cell(0, 12, "MANGALORE REFINERY AND PETROCHEMICALS LIMITED", align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_fill_color(255, 107, 53)
            self.rect(0, 18, 210, 2, "F")
            self.ln(6)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 10, f"CONFIDENTIAL - Page {self.page_no()} | SovereignForge Demo Fixture", align="C")

    pdf = InspectionPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Title block
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 12, "ELECTRICAL SYSTEMS INSPECTION REPORT", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, "Quarterly Inspection - Q3 2026 | Unit 4 - Crude Distillation Unit (CDU)", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Meta table
    pdf.set_fill_color(240, 240, 245)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(0, 51, 102)
    meta = [
        ("Inspection Date:", "September 12, 2026"),
        ("Report Number:", "MRPL/ELE/2026/Q3/047"),
        ("Inspected By:", "Er. R. K. Sharma, Chief Electrical Engineer"),
        ("Area / Section:", "Unit 4 - CDU Electrical Substation & Field Equipment"),
        ("Classification:", "CONFIDENTIAL - For Internal Use Only"),
    ]
    for label, val in meta:
        pdf.cell(60, 7, label, fill=True, border=1)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(130, 7, val, border=1, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(0, 51, 102)
    pdf.ln(6)

    # Executive Summary
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 51, 102)
    pdf.set_fill_color(0, 51, 102)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, "  1.  EXECUTIVE SUMMARY", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(0, 6,
        "A comprehensive quarterly inspection of the Unit 4 Crude Distillation Unit electrical systems was "
        "conducted on September 12, 2026. The inspection covered the main switchgear room, MCC panels, "
        "field instruments, earthing systems, and emergency lighting. A total of 11 discrepancies were "
        "identified, of which 3 are classified HIGH severity and require immediate corrective action. "
        "Production continuity risk is assessed as MODERATE-HIGH until the main switchgear issue is resolved."
    )
    pdf.ln(4)

    # Key Findings
    pdf.set_fill_color(0, 51, 102)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "  2.  KEY FINDINGS", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(30, 30, 30)

    findings = [
        ("HIGH",   "Main 11kV switchgear panel (Panel SG-4A) shows thermal discoloration and carbon tracking on Bus Bar Section B. Internal temperature measured at 78degC against rated 55degC. Risk of arc flash or busbar failure under load."),
        ("HIGH",   "Motor Control Centre MCC-4B: Contactor for Pump P-401A shows severe pitting and contact erosion. Estimated remaining life < 2 weeks under current operational load. Pump is critical for crude feed."),
        ("HIGH",   "Earthing resistance at transformer TR-4C measures 14.8 ohms (acceptable limit: <= 5 ohms). Inadequate earthing poses serious personnel safety risk and equipment damage potential during fault conditions."),
        ("MEDIUM", "Cable trays in sections E-4 through E-7 showing corrosion-induced structural weakening. 6 cable tray supports observed with >40% cross-section loss due to H2S-induced corrosion."),
        ("MEDIUM", "Emergency lighting system: 4 of 22 luminaires in the CDU pump area found non-functional. Does not meet IS:3646 requirements for emergency egress illumination. Replacement bulbs requisitioned."),
        ("MEDIUM", "UPS system for control room (UPS-CR-01) shows battery bank health at 62% (threshold: 80%). Auto-changeover test failed on 2nd attempt. Battery replacement recommended before October 2026."),
        ("MEDIUM", "Conduit sealing fittings EF-4-101 through EF-4-108 (Hazardous Zone 1) show cracking in sealing compound. Fire and explosion propagation risk in the event of gas release."),
        ("LOW",    "Cable identification tags missing or faded on 23 cables in Junction Box JB-4-12. Increases maintenance time and misidentification risk during emergency isolation."),
        ("LOW",    "Motor terminal box covers for M-403B and M-407A show loose fasteners. Ingress protection rating compromised - IP65 no longer assured."),
        ("LOW",    "Control panel CP-4-02 door seal shows 15cm gap due to hinge damage. Dust and moisture ingress possible; may affect relay calibration long-term."),
        ("LOW",    "Annunciation panel AP-4-01: 3 alarm points found latched in unacknowledged state for >72 hours. Operational response procedure not followed per SOP-ELE-012."),
    ]

    sev_colors = {"HIGH": (192, 57, 43), "MEDIUM": (230, 126, 22), "LOW": (39, 174, 96)}
    pdf.set_font("Helvetica", "", 9)
    for i, (sev, desc) in enumerate(findings, 1):
        r, g, b = sev_colors[sev]
        pdf.set_fill_color(r, g, b)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(18, 12, f" {sev}", fill=True, border=1)
        pdf.set_fill_color(250, 250, 255)
        pdf.set_text_color(20, 20, 20)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(172, 6, f"F-{i:02d}  {desc}", border=1, fill=True)
        pdf.ln(1)

    pdf.ln(4)

    # Risk Assessment
    pdf.set_fill_color(0, 51, 102)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "  3.  RISK ASSESSMENT", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(30, 30, 30)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6,
        "CRITICAL RISK: Simultaneous failure of SG-4A switchgear and MCC-4B contactor could result in "
        "complete loss of power to the CDU pump area, leading to unplanned shutdown of crude distillation "
        "and estimated production loss of 450 MT/day (approximately INR 2.7 Cr/day). Arc flash hazard at "
        "SG-4A poses serious risk of personnel injury to maintenance staff. "
        "HIGH RISK: Earthing failure at TR-4C poses risk of equipment damage and personnel electrocution. "
        "MEDIUM RISK: Conduit seal failures in Zone 1 areas could result in gas leak propagation. "
        "LOW RISK: Documentation and minor maintenance issues - no immediate production impact."
    )
    pdf.ln(4)

    # Recommendations
    pdf.set_fill_color(0, 91, 153)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "  4.  RECOMMENDATIONS", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(30, 30, 30)
    recs = [
        ("IMMEDIATE - Within 24 Hours",
         "De-energize SG-4A Bus Section B and arrange OEM inspection. Isolate from service and switch load to standby SG-4B. Do not restore until thermal scan confirms no hot spots above 60degC."),
        ("IMMEDIATE - Within 48 Hours",
         "Replace contactor assembly in MCC-4B for pump P-401A. Procure spare from central stores (part no. ABB-A75-30-11). Arrange shutdown window with Operations."),
        ("Within 7 Days",
         "Commission earthing remediation at TR-4C. Engage MRPL Civil dept. for additional earth pits (minimum 3 additional pits required to achieve <= 5 ohm)."),
        ("Within 14 Days",
         "Replace all 4 non-functional emergency luminaires. Conduct IS:3646 compliant lux-level test and submit compliance certificate to Safety Dept."),
        ("Within 30 Days",
         "Replace UPS battery bank UPS-CR-01. Schedule maintenance window with IT/Instrumentation. Conduct load test after replacement to verify auto-changeover within 20ms."),
        ("Within 30 Days",
         "Re-seal all 8 conduit sealing fittings in Zone 1 (EF-4-101 to EF-4-108). Use EX-rated compound grade M60. Verify against zone classification drawing."),
    ]
    for i, (timeline, action) in enumerate(recs, 1):
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6, f"R-{i:02d}  [{timeline}]", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(15)
        pdf.multi_cell(185, 5, action)
        pdf.ln(1)

    # Sign-off
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(0, 51, 102)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, "  5.  SIGN-OFF & APPROVALS", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(30, 30, 30)
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 10)
    approvers = [
        ("Inspected By",   "Er. R. K. Sharma", "Chief Electrical Engineer"),
        ("Reviewed By",    "Er. P. N. Bhat",   "DGM - Electrical Maintenance"),
        ("Approved By",    "Mr. S. K. Menon",  "VP - Operations & Maintenance"),
    ]
    for role, name, title in approvers:
        pdf.set_fill_color(240, 240, 245)
        pdf.cell(50, 8, role, fill=True, border=1)
        pdf.cell(80, 8, name, border=1)
        pdf.cell(60, 8, title, border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "This report was generated and analyzed entirely on-premise by SovereignForge AI Workbench.", align="C")

    out_path = FIXTURE_DIR / "sample_inspection_report.pdf"
    pdf.output(str(out_path))
    print(f"  ✅ Generated: {out_path}")


def _generate_inspection_txt():
    """Fallback: write raw text version of the inspection report."""
    content = """MANGALORE REFINERY AND PETROCHEMICALS LIMITED
ELECTRICAL SYSTEMS INSPECTION REPORT - Q3 2026
Report No: MRPL/ELE/2026/Q3/047 | Unit 4 - Crude Distillation Unit (CDU)
Inspection Date: September 12, 2026 | Inspected By: Er. R. K. Sharma

EXECUTIVE SUMMARY
A comprehensive quarterly inspection of Unit 4 CDU electrical systems was conducted.
11 discrepancies identified: 3 HIGH, 4 MEDIUM, 4 LOW severity.
Immediate action required on switchgear and earthing issues.

FINDINGS
[HIGH] F-01: Main 11kV switchgear SG-4A - thermal discoloration on Bus Bar Section B. Temperature 78degC vs rated 55degC. Arc flash risk.
[HIGH] F-02: MCC-4B Contactor for Pump P-401A - severe pitting, contact erosion. Remaining life < 2 weeks.
[HIGH] F-03: Earthing resistance at TR-4C = 14.8 ohms (limit: 5 ohms). Personnel safety risk.
[MEDIUM] F-04: Cable trays E-4 to E-7 - corrosion, 40% structural loss on 6 supports.
[MEDIUM] F-05: 4 of 22 emergency luminaires non-functional in CDU pump area.
[MEDIUM] F-06: UPS-CR-01 battery health at 62% (threshold 80%). Auto-changeover failed.
[MEDIUM] F-07: Conduit seals EF-4-101 to EF-4-108 cracked in Zone 1. Gas propagation risk.
[LOW] F-08: 23 cable tags missing in JB-4-12.
[LOW] F-09: Motor terminal box covers loose on M-403B and M-407A.
[LOW] F-10: Control panel CP-4-02 door seal gap 15cm.
[LOW] F-11: Alarm panel AP-4-01 - 3 alarms unacknowledged >72 hours.

RISKS
- Risk of arc flash at SG-4A Bus Section B - HIGH
- Production loss risk 450 MT/day if CDU pump trip - HIGH (INR 2.7 Cr/day)
- Personnel electrocution risk from TR-4C earthing failure - HIGH
- Gas propagation in Zone 1 via cracked conduit seals - MEDIUM

RECOMMENDATIONS
R-01 [IMMEDIATE <24H]: De-energize SG-4A Bus Section B, arrange OEM thermal inspection.
R-02 [IMMEDIATE <48H]: Replace MCC-4B contactor for P-401A. Part: ABB-A75-30-11.
R-03 [7 Days]: Earthing remediation at TR-4C - 3 additional earth pits required.
R-04 [14 Days]: Replace 4 emergency luminaires, conduct IS:3646 lux test.
R-05 [30 Days]: Replace UPS-CR-01 battery bank, verify auto-changeover.
R-06 [30 Days]: Re-seal conduit fittings EF-4-101 to EF-4-108 with M60 compound.

APPROVAL
Inspected By: Er. R. K. Sharma - Chief Electrical Engineer
Reviewed By:  Er. P. N. Bhat - DGM Electrical Maintenance
Approved By:  Mr. S. K. Menon - VP Operations & Maintenance
"""
    out_path = FIXTURE_DIR / "sample_inspection_report.txt"
    out_path.write_text(content, encoding="utf-8")
    print(f"  ✅ Generated (text fallback): {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
#  2. Generate P&ID Diagram PNG
# ─────────────────────────────────────────────────────────────────────────────

def generate_pid_diagram():
    from PIL import Image, ImageDraw, ImageFont
    import math

    W, H = 1600, 1100
    img = Image.new("RGB", (W, H), color=(252, 252, 252))
    draw = ImageDraw.Draw(img)

    # Try to load a font
    try:
        font_sm  = ImageFont.truetype("arial.ttf", 14)
        font_med = ImageFont.truetype("arial.ttf", 16)
        font_lrg = ImageFont.truetype("arial.ttf", 20)
        font_ttl = ImageFont.truetype("arial.ttf", 24)
        font_bold = ImageFont.truetype("arialbd.ttf", 18)
    except Exception:
        font_sm = font_med = font_lrg = font_ttl = font_bold = ImageFont.load_default()

    DARK_BLUE = (0, 51, 102)
    MID_BLUE  = (0, 91, 153)
    PIPE_CLR  = (40, 40, 40)
    INST_CLR  = (0, 80, 160)
    VALVE_CLR = (20, 20, 80)
    VESSEL_CLR= (0, 60, 120)
    LINE_W    = 4
    THIN_W    = 2

    # ── Title block ──────────────────────────────────────────────────────────
    draw.rectangle([0, 0, W, 60], fill=DARK_BLUE)
    draw.rectangle([0, 60, W, 64], fill=(255, 107, 53))
    draw.text((20, 15), "MRPL - CRUDE DISTILLATION UNIT (CDU) - UNIT 4", fill="white", font=font_ttl)
    draw.text((20, 42), "P&ID DIAGRAM  |  Sheet 1 of 3  |  Rev: 04  |  CONFIDENTIAL", fill=(180, 200, 220), font=font_sm)
    draw.text((W - 320, 15), "Doc No: MRPL-CDU-PID-004-R04", fill=(180, 200, 220), font=font_sm)
    draw.text((W - 320, 42), "SovereignForge Demo Fixture", fill=(255, 150, 100), font=font_sm)

    def draw_pipe(x1, y1, x2, y2, w=LINE_W, color=PIPE_CLR):
        draw.line([(x1, y1), (x2, y2)], fill=color, width=w)

    def draw_vessel(cx, cy, w, h, label, sub=""):
        """Draw a process vessel (rectangle with rounded indication)"""
        x0, y0 = cx - w//2, cy - h//2
        draw.rectangle([x0, y0, x0+w, y0+h], outline=VESSEL_CLR, fill=(230, 240, 255), width=3)
        draw.rectangle([x0, y0, x0+w, y0+16], fill=VESSEL_CLR)
        draw.text((cx, y0+8), label, fill="white", font=font_med, anchor="mm")
        if sub:
            draw.text((cx, cy), sub, fill=VESSEL_CLR, font=font_sm, anchor="mm")

    def draw_pump(cx, cy, label):
        """Draw a centrifugal pump symbol (circle with triangle)"""
        r = 28
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=PIPE_CLR, fill=(220, 230, 245), width=3)
        pts = [(cx-14, cy+14), (cx-14, cy-14), (cx+18, cy)]
        draw.polygon(pts, fill=INST_CLR)
        draw.text((cx, cy+r+12), label, fill=PIPE_CLR, font=font_sm, anchor="mm")

    def draw_valve(cx, cy, label="", orientation="H"):
        """Draw a gate valve symbol"""
        if orientation == "H":
            pts = [(cx-16, cy-14), (cx+16, cy-14), (cx, cy), (cx+16, cy+14), (cx-16, cy+14), (cx, cy)]
        else:
            pts = [(cx-14, cy-16), (cx-14, cy+16), (cx, cy), (cx+14, cy+16), (cx+14, cy-16), (cx, cy)]
        draw.polygon(pts, outline=VALVE_CLR, fill=(200, 210, 240), width=2)
        if label:
            draw.text((cx, cy + 22), label, fill=VALVE_CLR, font=font_sm, anchor="mm")

    def draw_instrument(cx, cy, tag, label=""):
        """Draw instrument circle (ISA 5.1 style)"""
        r = 22
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=INST_CLR, fill=(240, 248, 255), width=2)
        draw.text((cx, cy-6), tag[:4], fill=INST_CLR, font=font_sm, anchor="mm")
        draw.text((cx, cy+7), tag[4:] if len(tag) > 4 else "", fill=INST_CLR, font=font_sm, anchor="mm")
        if label:
            draw.text((cx+r+4, cy), label, fill=(80, 80, 80), font=font_sm, anchor="lm")

    def draw_control_valve(cx, cy, label=""):
        """Draw control valve (triangle with actuator circle)"""
        pts = [(cx-18, cy-14), (cx+18, cy-14), (cx, cy+8)]
        draw.polygon(pts, outline=VALVE_CLR, fill=(180, 195, 230), width=2)
        draw.ellipse([cx-12, cy-30, cx+12, cy-10], outline=INST_CLR, fill=(200, 220, 255), width=2)
        draw.line([(cx, cy+8), (cx, cy+20)], fill=PIPE_CLR, width=2)
        if label:
            draw.text((cx+22, cy), label, fill=VALVE_CLR, font=font_sm, anchor="lm")

    # ── Process Flow - Main crude line ────────────────────────────────────────
    # Feed surge drum
    draw_vessel(160, 280, 120, 160, "V-401", "SURGE\nDRUM")
    # Crude feed pump A
    draw_pump(340, 280, "P-401A")
    # Crude feed pump B (standby)
    draw_pump(340, 380, "P-401B\n(STBY)")
    # Preheat train
    draw_vessel(540, 280, 110, 80, "E-401", "PHT-1")
    draw_vessel(700, 280, 110, 80, "E-402", "PHT-2")
    # Atmospheric heater
    draw_vessel(900, 260, 130, 200, "H-401", "ATM\nHEATER")
    # Atmospheric distillation column
    draw_vessel(1130, 300, 140, 440, "C-401", "ATMOS. DIST.\nCOLUMN")
    # Overhead condenser
    draw_vessel(1130, 130, 120, 80, "E-403", "OHD COND.")
    # Reflux drum
    draw_vessel(1360, 130, 110, 70, "V-402", "REFLUX\nDRUM")

    # ── Piping ─────────────────────────────────────────────────────────────────
    # Feed line
    draw_pipe(0, 280, 100, 280)                          # crude inlet
    draw_pipe(220, 280, 312, 280)                        # drum → pump A
    draw_pipe(220, 380, 312, 380)                        # drum → pump B
    draw_pipe(368, 280, 485, 280)                        # pump A → PHT1
    draw_pipe(595, 280, 645, 280)                        # PHT1 → PHT2
    draw_pipe(755, 280, 835, 280)                        # PHT2 → heater
    draw_pipe(965, 280, 1060, 280)                       # heater → column

    # Column side draws
    draw_pipe(1200, 380, 1280, 380); draw.text((1290, 375), "KERO DRAW", fill=PIPE_CLR, font=font_sm)
    draw_pipe(1200, 460, 1280, 460); draw.text((1290, 455), "DIESEL DRAW", fill=PIPE_CLR, font=font_sm)
    draw_pipe(1200, 540, 1280, 540); draw.text((1290, 535), "AGO DRAW", fill=PIPE_CLR, font=font_sm)
    draw_pipe(1200, 680, 1280, 680); draw.text((1290, 675), "LONG RESID", fill=PIPE_CLR, font=font_sm)

    # Overhead
    draw_pipe(1200, 220, 1200, 170)
    draw_pipe(1200, 170, 1070, 130)
    draw_pipe(1070, 130, 1130, 130) # wait already handled
    draw_pipe(1190, 130, 1305, 130)                      # cond → reflux drum
    draw_pipe(1415, 165, 1415, 250)
    draw.text((1425, 200), "NAPHTHA\nOUTLET", fill=PIPE_CLR, font=font_sm)

    # ── Valves ─────────────────────────────────────────────────────────────────
    draw_valve(60, 280, "XV-401"); draw_valve(260, 280, "BDV-401")
    draw_valve(260, 380, "BDV-402")
    draw_valve(620, 280, "HC-401")
    draw_control_valve(800, 280, "FCV-401")
    draw_valve(1030, 280, "XV-402")

    # ── Instruments ────────────────────────────────────────────────────────────
    draw_instrument(130, 210, "PT", "PT-401")     # pressure transmitter
    draw_instrument(250, 210, "LT", "LT-401")     # level transmitter
    draw_instrument(430, 220, "FT", "FT-401")     # flow transmitter
    draw_instrument(590, 210, "TT", "TT-401")     # temp transmitter - PHT1 in
    draw_instrument(750, 210, "TT", "TT-402")     # temp transmitter - PHT2 out
    draw_instrument(880, 200, "PT", "PT-402")     # heater inlet P
    draw_instrument(980, 200, "TT", "TT-403")     # heater outlet T
    draw_instrument(1080, 200, "FT", "FT-402")    # column feed flow
    draw_instrument(1390, 80, "PT", "PT-403")     # reflux drum P
    draw_instrument(1450, 80, "LT", "LT-402")     # reflux drum L

    # Instrument signal lines (dashed)
    for x, y in [(130, 232), (250, 232), (430, 242), (590, 232), (750, 232)]:
        for dy in range(0, 48, 8):
            draw.line([(x, y+dy), (x, y+dy+4)], fill=INST_CLR, width=1)

    # ── Legend ────────────────────────────────────────────────────────────────
    lx, ly = 30, 800
    draw.rectangle([lx, ly, lx+360, ly+240], outline=DARK_BLUE, fill=(245, 248, 255), width=2)
    draw.rectangle([lx, ly, lx+360, ly+26], fill=DARK_BLUE)
    draw.text((lx+10, ly+8), "LEGEND", fill="white", font=font_bold)

    items = [
        ("━━━━", "Process Pipeline (4\" and above)"),
        ("- - -", "Instrument Signal Line"),
        ("○", "Instrument Circle (ISA 5.1)"),
        ("◇", "Control Valve"),
        ("▷", "Centrifugal Pump"),
        ("▭", "Vessel / Exchanger / Heater"),
    ]
    for i, (sym, desc) in enumerate(items):
        draw.text((lx+15, ly+36+i*32), sym, fill=PIPE_CLR, font=font_med)
        draw.text((lx+65, ly+36+i*32), desc, fill=(40, 40, 40), font=font_sm)

    # ── Notes ────────────────────────────────────────────────────────────────
    nx, ny = 420, 800
    draw.rectangle([nx, ny, nx+480, ny+240], outline=DARK_BLUE, fill=(245, 248, 255), width=2)
    draw.rectangle([nx, ny, nx+480, ny+26], fill=DARK_BLUE)
    draw.text((nx+10, ny+8), "ENGINEERING NOTES", fill="white", font=font_bold)
    notes = [
        "1. All pipe sizes are nominal; insulation not shown.",
        "2. Equipment nozzle connections per respective data sheets.",
        "3. All instruments are field-mounted unless noted.",
        "4. Control valve fail positions: FCV-401 → Fail-Close (FC).",
        "5. Pump P-401B is auto-standby; starts on P-401A failure.",
        "6. Column C-401 design pressure: 2.5 kg/cm2g.",
        "7. This drawing is CONFIDENTIAL - not for external circulation.",
    ]
    for i, note in enumerate(notes):
        draw.text((nx+12, ny+34+i*28), note, fill=(40, 40, 40), font=font_sm)

    # ── Revision block ───────────────────────────────────────────────────────
    rx, ry = 950, 800
    draw.rectangle([rx, ry, W-20, ry+240], outline=DARK_BLUE, fill=(245, 248, 255), width=2)
    draw.rectangle([rx, ry, W-20, ry+26], fill=DARK_BLUE)
    draw.text((rx+10, ry+8), "REVISION HISTORY", fill="white", font=font_bold)
    revs = [
        ("04", "2026-09-01", "Updated control valve specs for FCV-401", "RKS"),
        ("03", "2026-06-15", "Added P-401B auto-standby logic",          "PNB"),
        ("02", "2026-03-10", "Corrected PHT-2 area class designation",   "RKS"),
        ("01", "2025-12-01", "Issued for construction",                  "SKM"),
        ("00", "2025-10-15", "HAZOP study revision",                     "RKS"),
    ]
    for i, (rev, dt, desc, by) in enumerate(revs):
        y = ry + 32 + i*40
        fill = (230, 240, 255) if i % 2 == 0 else (245, 248, 255)
        draw.rectangle([rx+5, y, W-25, y+36], fill=fill)
        draw.text((rx+15,  y+10), rev,  fill=DARK_BLUE, font=font_bold)
        draw.text((rx+55,  y+10), dt,   fill=(40,40,40), font=font_sm)
        draw.text((rx+175, y+10), desc, fill=(40,40,40), font=font_sm)
        draw.text((W-70,   y+10), by,   fill=DARK_BLUE,  font=font_bold)

    # Border
    draw.rectangle([0, 64, W-1, H-1], outline=DARK_BLUE, width=3)

    out_path = FIXTURE_DIR / "sample_pid_diagram.png"
    img.save(str(out_path), "PNG", dpi=(150, 150))
    print(f"  ✅ Generated: {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
#  3. SOP document (for knowledge base ingestion)
# ─────────────────────────────────────────────────────────────────────────────

def generate_sop():
    content = """MANGALORE REFINERY AND PETROCHEMICALS LIMITED
STANDARD OPERATING PROCEDURE

Document No: SOP-ELE-012 | Title: ELECTRICAL MAINTENANCE - INSPECTION & REPORTING
Revision: 03 | Effective Date: January 2026 | Approved By: VP Operations

═══════════════════════════════════════════════════════════════════════════════
1. PURPOSE
═══════════════════════════════════════════════════════════════════════════════
This procedure defines the standards for quarterly electrical inspection, 
documentation, reporting, and corrective action follow-up for all electrical 
equipment in the Crude Distillation Unit (CDU), Vacuum Distillation Unit (VDU), 
and associated utilities at MRPL.

═══════════════════════════════════════════════════════════════════════════════
2. SCOPE
═══════════════════════════════════════════════════════════════════════════════
Applies to: All electrical equipment rated 415V and above, MCC panels, HT switchgear, 
transformers, emergency systems, earthing networks, and field instruments within 
the battery limits of CDU, VDU, and FCC units.

═══════════════════════════════════════════════════════════════════════════════
3. INSPECTION FREQUENCY
═══════════════════════════════════════════════════════════════════════════════
3.1 HT Switchgear (11kV/6.6kV): Quarterly visual, Annual shutdown inspection
3.2 MCC Panels (415V): Quarterly
3.3 Transformers: Monthly thermal scan, Annual oil sampling
3.4 Field Instruments: Monthly calibration check
3.5 Earthing Network: Semi-annual resistance measurement (limit: <=5 ohms)
3.6 Emergency Lighting: Monthly functional test

═══════════════════════════════════════════════════════════════════════════════
4. SEVERITY CLASSIFICATION
═══════════════════════════════════════════════════════════════════════════════
HIGH SEVERITY (Immediate Action Required):
  - Any finding posing immediate risk to personnel safety
  - Equipment temperature exceeding rated value by >10degC
  - Earthing resistance >10 ohms
  - Any HT insulation fault
  - Failure of safety-critical protection relay
  Corrective Action Timeline: Within 24-48 hours. Plant shutdown if required.

MEDIUM SEVERITY (Action Within 30 Days):
  - Equipment showing accelerated wear but operational
  - Earthing resistance 5-10 ohms
  - Non-critical instrument drift
  - Cable tray structural issues
  Corrective Action Timeline: Within 30 days. Document and monitor.

LOW SEVERITY (Scheduled Maintenance):
  - Minor housekeeping issues
  - Missing labels or tags
  - Cosmetic damage not affecting function
  Corrective Action Timeline: Next scheduled maintenance window.

═══════════════════════════════════════════════════════════════════════════════
5. REPORTING REQUIREMENTS
═══════════════════════════════════════════════════════════════════════════════
5.1 All inspection findings must be documented in the prescribed format.
5.2 HIGH severity findings must be reported to DGM (Electrical) within 2 hours.
5.3 All findings must be entered in the CMMS (SAP PM module) within 24 hours.
5.4 Quarterly Inspection Report must be approved by VP Operations within 7 days.
5.5 Corrective action closure must be evidenced with photographs and test results.

═══════════════════════════════════════════════════════════════════════════════
6. APPROVAL NOTE REQUIREMENTS
═══════════════════════════════════════════════════════════════════════════════
For HIGH severity findings requiring immediate expenditure (>INR 5 Lakhs):
  - Prepare Approval Note in MRPL standard format
  - Include: Root cause, risk assessment, cost estimate, recommended action
  - Route for approval: CE → DGM → VP Operations
  - Emergency approvals: Verbal from VP, followed by written within 24 hours

═══════════════════════════════════════════════════════════════════════════════
7. EARTHING STANDARDS
═══════════════════════════════════════════════════════════════════════════════
All earthing systems must comply with IS:3043:2018.
  - Earth resistance: <=1 ohm for HT equipment, <=5 ohms for LT equipment
  - Earth continuity: Test annually, document in Earth Test Register
  - Pipe earthing: Mandatory for all process piping in hazardous areas

═══════════════════════════════════════════════════════════════════════════════
8. HAZARDOUS AREA REQUIREMENTS
═══════════════════════════════════════════════════════════════════════════════
Zone 0: Continuous explosive atmosphere - Only intrinsically safe equipment (Ex-ia)
Zone 1: Periodic explosive atmosphere - Ex-d, Ex-e, or Ex-ia equipment
Zone 2: Infrequent explosive atmosphere - Ex-n or higher classification

All Zone 1 conduit sealing fittings must be verified for integrity quarterly.
Sealing compound: Chico-A (UL Listed) or equivalent M60 grade compound.
Any damaged seals in Zone 1 or Zone 2 must be repaired within 7 days (MEDIUM) 
or 24 hours if near ignition source (HIGH).

═══════════════════════════════════════════════════════════════════════════════
9. EMERGENCY LIGHTING STANDARDS
═══════════════════════════════════════════════════════════════════════════════
Comply with IS:3646 (Code of Practice for Interior Illumination).
  - Emergency egress: Minimum 10 lux at floor level
  - Battery backup: Minimum 1 hour at rated load
  - Self-test: Monthly via test switch, annual discharge test
  - Non-functional luminaires: Replace within 48 hours in critical areas

═══════════════════════════════════════════════════════════════════════════════
10. REFERENCES
═══════════════════════════════════════════════════════════════════════════════
IS:3043:2018 - Code of Practice for Earthing
IS:3646 - Code of Practice for Interior Illumination
IS:13947 - LV Switchgear and Controlgear
IEC 60079 series - Explosive Atmospheres
IS:732 - Code of Practice for Electrical Wiring Installations
MRPL Safety Manual Rev-06 (2025)
OISD-STD-137 - Inspection of Electrical Equipment

Prepared by: Electrical Engineering Dept., MRPL
"""
    out_path = FIXTURE_DIR / "sample_sop.txt"
    out_path.write_text(content, encoding="utf-8")
    print(f"  ✅ Generated: {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
#  4. Board briefing document
# ─────────────────────────────────────────────────────────────────────────────

def generate_board_brief():
    content = """MANGALORE REFINERY AND PETROCHEMICALS LIMITED
BOARD BRIEFING NOTE - CAPITAL EXPENDITURE APPROVAL

Subject: Emergency Replacement of HT Switchgear Panel SG-4A and Electrical Remediation Works
Ref: MRPL/ELE/2026/Q3/047 | Date: September 2026 | Urgency: HIGH

BACKGROUND
The quarterly electrical inspection of CDU Unit 4, conducted on September 12, 2026, has 
identified three HIGH severity deficiencies requiring immediate capital expenditure approval:

1. HT Switchgear SG-4A (Panel Rating: 11kV, 630A) - Thermal failure with carbon tracking
2. MCC-4B Critical Contactor Replacement - Pump P-401A (crude feed critical service)
3. TR-4C Earthing System Upgrade - Current resistance 14.8 ohm vs limit of 5 ohm

FINANCIAL IMPACT ASSESSMENT
Estimated Capital Cost:
  - SG-4A Switchgear OEM Inspection + Repair/Replace: INR 45-65 Lakhs
  - MCC-4B Contactor Assembly: INR 3.2 Lakhs
  - Earthing Remediation (3 earth pits, cable, connections): INR 8.5 Lakhs
  - Total Estimated CAPEX: INR 56.7 - 76.7 Lakhs

Production Risk if NOT Acted Upon:
  - Estimated probability of unplanned CDU shutdown: 85% within 30 days
  - Production loss on CDU shutdown: 450 MT/day crude processed
  - Revenue impact: INR 2.7 Crores/day
  - Expected downtime for emergency repair vs planned: 12 days vs 4 days
  - Additional cost of emergency vs planned shutdown: INR 32 Crores

RECOMMENDATION
Board approval requested for emergency CAPEX of INR 77 Lakhs (including 15% contingency).
Works to be executed during the emergency maintenance window planned for September 22-25, 2026.

Recommended by: VP Operations & Maintenance
For Board Approval: Managing Director
"""
    out_path = FIXTURE_DIR / "sample_board_brief.txt"
    out_path.write_text(content, encoding="utf-8")
    print(f"  ✅ Generated: {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
#  5. Sample code problem (for sandbox demo)
# ─────────────────────────────────────────────────────────────────────────────

def generate_code_problem():
    content = '''"""
MRPL Engineering Calculation - Pipe Wall Thickness Estimation
Using ASME B31.3 Process Piping Code

Task: Calculate minimum required pipe wall thickness for crude oil line.
Given:
  - Design pressure P = 24 bar = 2.4 MPa
  - Pipe outer diameter D = 168.3 mm (6-inch NPS)
  - Material: A106 Gr. B carbon steel
  - Design temperature: 350degC
  - Allowable stress S at 350degC = 103.4 MPa (from ASME tables)
  - Corrosion allowance c = 3.0 mm
  - Quality factor E = 1.0 (seamless)
  - Y coefficient = 0.4 (ferritic steel, T < 482degC)

Formula (ASME B31.3, Clause 304.1.2):
  t_min = (P × D) / (2 × (S×E + P×Y)) + c
"""

import math

def calculate_pipe_wall_thickness(P_bar, D_mm, S_MPa, E=1.0, Y=0.4, c_mm=3.0):
    """
    ASME B31.3 minimum pipe wall thickness calculation.
    
    Args:
        P_bar  : Design pressure in bar
        D_mm   : Outer diameter in mm
        S_MPa  : Allowable stress at design temperature in MPa
        E      : Quality factor (1.0 for seamless)
        Y      : Y-coefficient (temp dependent, 0.4 for <482degC ferritic)
        c_mm   : Corrosion allowance in mm
    
    Returns:
        dict with all intermediate values and results
    """
    P_MPa = P_bar / 10.0       # convert bar to MPa
    
    # ASME B31.3 Formula
    t_pressure = (P_MPa * D_mm) / (2 * (S_MPa * E + P_MPa * Y))
    t_min = t_pressure + c_mm   # add corrosion allowance
    
    # Select next standard wall thickness (schedule)
    # Common wall thicknesses for 6" pipe in mm
    schedules = {
        "Sch 10S": 3.40, "Sch 20":  4.78, "Sch 30":  5.56,
        "Sch 40 (Std)": 7.11, "Sch 60": 8.74, "Sch 80 (XH)": 10.97,
        "Sch 120": 14.27, "Sch 160": 18.26, "Sch XXH": 21.95
    }
    selected_sch = None
    selected_t   = None
    for sch, t in schedules.items():
        if t >= t_min:
            selected_sch = sch
            selected_t   = t
            break
    
    # Pressure at selected wall thickness (back-calculation)
    if selected_t:
        t_eff = selected_t - c_mm   # effective thickness after corrosion
        P_max = (2 * S_MPa * E * t_eff) / (D_mm - 2 * Y * t_eff)
        P_max_bar = P_max * 10
    else:
        P_max_bar = None
    
    return {
        "design_pressure_bar": P_bar,
        "design_pressure_MPa": round(P_MPa, 3),
        "outer_diameter_mm": D_mm,
        "allowable_stress_MPa": S_MPa,
        "quality_factor_E": E,
        "Y_coefficient": Y,
        "corrosion_allowance_mm": c_mm,
        "t_pressure_mm": round(t_pressure, 3),
        "t_minimum_required_mm": round(t_min, 3),
        "selected_schedule": selected_sch,
        "selected_wall_thickness_mm": selected_t,
        "max_allowable_pressure_bar": round(P_max_bar, 2) if P_max_bar else None,
        "design_factor": round(P_max_bar / P_bar, 2) if P_max_bar else None,
    }


def print_report(result):
    print("=" * 60)
    print("  ASME B31.3 PIPE WALL THICKNESS CALCULATION")
    print("  MRPL - CDU Unit 4 - Crude Feed Line")
    print("=" * 60)
    print(f"  Design Pressure      : {result[\'design_pressure_bar\']} bar ({result[\'design_pressure_MPa\']} MPa)")
    print(f"  Outer Diameter       : {result[\'outer_diameter_mm\']} mm (6-inch NPS)")
    print(f"  Allowable Stress     : {result[\'allowable_stress_MPa\']} MPa @ 350degC")
    print(f"  Quality Factor (E)   : {result[\'quality_factor_E\']}")
    print(f"  Y Coefficient        : {result[\'Y_coefficient\']}")
    print(f"  Corrosion Allowance  : {result[\'corrosion_allowance_mm\']} mm")
    print("-" * 60)
    print(f"  Pressure Term (t)    : {result[\'t_pressure_mm\']} mm")
    print(f"  Minimum t required   : {result[\'t_minimum_required_mm\']} mm")
    print("-" * 60)
    print(f"  Selected Schedule    : {result[\'selected_schedule\']}")
    print(f"  Selected Wall t      : {result[\'selected_wall_thickness_mm\']} mm")
    print(f"  Max Allowable Press  : {result[\'max_allowable_pressure_bar\']} bar")
    print(f"  Design Factor        : {result[\'design_factor\']}x")
    print("=" * 60)
    print("  ✓ COMPLIANT with ASME B31.3" if result[\'design_factor\'] and result[\'design_factor\'] >= 1.0 else "  ✗ NON-COMPLIANT")
    print("=" * 60)


if __name__ == "__main__":
    result = calculate_pipe_wall_thickness(
        P_bar=24,        # design pressure
        D_mm=168.3,      # 6-inch NPS OD
        S_MPa=103.4,     # A106 Gr.B @ 350degC
        E=1.0,           # seamless
        Y=0.4,           # ferritic, <482degC
        c_mm=3.0,        # corrosion allowance
    )
    print_report(result)
'''
    out_path = FIXTURE_DIR / "sample_code_problem.py"
    out_path.write_text(content, encoding="utf-8")
    print(f"  ✅ Generated: {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("\n[*] SovereignForge -- Generating Demo Fixtures\n")
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    print("1. Inspection Report PDF...")
    generate_inspection_pdf()

    print("2. P&ID Diagram PNG...")
    generate_pid_diagram()

    print("3. SOP Text (for KB ingestion)...")
    generate_sop()

    print("4. Board Briefing Note...")
    generate_board_brief()

    print("5. Sample Code Problem...")
    generate_code_problem()

    print(f"\n[OK] All fixtures written to: {FIXTURE_DIR}\n")
