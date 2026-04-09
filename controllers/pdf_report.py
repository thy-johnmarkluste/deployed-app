"""
PDF report builder — generates a styled per-subdomain PDF.
"""
import os
import re
import datetime
from pathlib import Path
from tkinter import messagebox

from models.config import HAS_FPDF, VULTR_TARGET_DOMAIN
from models.paths import get_reports_dir
from models.paths import open_path_cross_platform

if HAS_FPDF:
    from fpdf import FPDF


def build_pdf_report(domain, ip, metrics, log_callback=None,
                     repo_info=None, activities=None):
    """
    Create a styled PDF report for *domain* and return the Path to
    the generated file.  Opens the file automatically.

    *repo_info* is a dict with keys: has_git, remote_url, branch, last_commit
    *activities* is a list of dicts with keys: hash, date, author, action, message
    """
    if not HAS_FPDF:
        messagebox.showerror(
            "Missing Library",
            "fpdf2 is required for PDF reports.\n\nInstall it with: pip install fpdf2",
        )
        return None


    repo_info = repo_info or {}
    activities = activities or []

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()


    pdf.set_fill_color(26, 26, 46)
    pdf.rect(0, 0, 210, 40, "F")
    pdf.set_text_color(233, 69, 96)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_y(10)
    pdf.cell(0, 12, "Subdomain Report", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(184, 184, 184)
    pdf.cell(
        0, 6,
        f'Generated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        ln=True, align="C",
    )
    pdf.ln(12)


    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Domain Information", ln=True)
    pdf.set_draw_color(233, 69, 96)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 11)
    info_rows = [
        ("Domain", domain),
        ("IP Address", ip),
        ("Target Domain", VULTR_TARGET_DOMAIN),
    ]
    for label, value in info_rows:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(50, 8, f"{label}:", align="L")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, str(value), ln=True)
    pdf.ln(8)


    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Performance Metrics", ln=True)
    pdf.set_draw_color(233, 69, 96)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    col_w = [90, 90]
    pdf.set_fill_color(15, 52, 96)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(col_w[0], 9, "Metric", border=1, fill=True, align="C")
    pdf.cell(col_w[1], 9, "Value", border=1, fill=True, align="C", ln=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    metric_rows = [
        ("SSL Status", metrics.get("ssl_status", "N/A")),
        ("SSL Expiry (days)", metrics.get("ssl_expiry_days", 0)),
        ("Response Time (ms)", metrics.get("response_time_ms", 0)),
        ("Uptime (%)", metrics.get("uptime_pct", 0)),
        ("Bandwidth (kbps)", metrics.get("bandwidth_kbps", 0)),
        ("DB Speed (ms)", metrics.get("db_speed_ms", 0)),
        ("CPU Usage (%)", metrics.get("cpu_pct", 0)),
        ("Memory Usage (%)", metrics.get("memory_pct", 0)),
    ]
    fill = False
    for label, value in metric_rows:
        if fill:
            pdf.set_fill_color(230, 240, 250)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.cell(col_w[0], 8, label, border=1, fill=True, align="L")
        pdf.cell(col_w[1], 8, str(value), border=1, fill=True, align="C", ln=True)
        fill = not fill
    pdf.ln(10)


    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Repository Information", ln=True)
    pdf.set_draw_color(233, 69, 96)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 11)
    has_git = repo_info.get("has_git", False)
    if has_git:
        repo_rows = [
            ("Git Initialized", "Yes"),
            ("Remote URL", repo_info.get("remote_url", "Not configured")),
            ("Branch", repo_info.get("branch", "N/A")),
            ("Last Commit", repo_info.get("last_commit", "N/A")),
        ]
    else:
        repo_rows = [
            ("Git Initialized", "No"),
            ("Remote URL", "N/A"),
            ("Branch", "N/A"),
            ("Last Commit", "N/A"),
        ]

    for label, value in repo_rows:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(50, 8, f"{label}:", align="L")
        pdf.set_font("Helvetica", "", 11)

        display_val = str(value)[:60] + "..." if len(str(value)) > 60 else str(value)
        pdf.cell(0, 8, display_val, ln=True)
    pdf.ln(8)


    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Recent Activity Log", ln=True)
    pdf.set_draw_color(233, 69, 96)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    if activities:

        act_col_w = [30, 50, 35, 75]
        pdf.set_fill_color(15, 52, 96)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(act_col_w[0], 8, "Date", border=1, fill=True, align="C")
        pdf.cell(act_col_w[1], 8, "Author", border=1, fill=True, align="C")
        pdf.cell(act_col_w[2], 8, "Action", border=1, fill=True, align="C")
        pdf.cell(act_col_w[3], 8, "Message", border=1, fill=True, align="C", ln=True)

        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 8)
        fill = False

        for entry in activities[:15]:
            if fill:
                pdf.set_fill_color(230, 240, 250)
            else:
                pdf.set_fill_color(255, 255, 255)

            date_str = str(entry.get("date", ""))[:10]
            author = str(entry.get("author", ""))[:18]
            action = str(entry.get("action", "commit")).capitalize()
            message = str(entry.get("message", ""))[:35]
            if len(str(entry.get("message", ""))) > 35:
                message += "..."

            pdf.cell(act_col_w[0], 7, date_str, border=1, fill=True, align="L")
            pdf.cell(act_col_w[1], 7, author, border=1, fill=True, align="L")
            pdf.cell(act_col_w[2], 7, action, border=1, fill=True, align="C")
            pdf.cell(act_col_w[3], 7, message, border=1, fill=True, align="L", ln=True)
            fill = not fill

        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, f"Showing {min(len(activities), 15)} of {len(activities)} activities", ln=True)
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 8, "No activity recorded for this subdomain.", ln=True)

    pdf.ln(10)


    ssl = metrics.get("ssl_status", "Unknown")
    uptime = metrics.get("uptime_pct", 0)
    if ssl == "Valid" and uptime >= 99:
        status_text, r, g, b = "HEALTHY", 78, 204, 163
    elif ssl == "Valid" and uptime >= 90:
        status_text, r, g, b = "WARNING", 255, 193, 7
    else:
        status_text, r, g, b = "CRITICAL", 233, 69, 96

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Overall Status", ln=True)
    pdf.set_draw_color(233, 69, 96)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)
    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(60, 12, f"  {status_text}", fill=True, ln=True)


    pdf.set_y(-20)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, "Domain Connector - Server Subdomain Manager", align="C")


    safe_name = re.sub(r"[^\w.-]", "_", domain)
    reports_dir = get_reports_dir()
    filename = reports_dir / f"{safe_name}_report.pdf"
    pdf.output(str(filename))

    if log_callback:
        log_callback(f"PDF report saved: {filename}")

    open_path_cross_platform(filename)

    return filename
