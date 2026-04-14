"""Send real emails via Gmail SMTP with EY branding."""

import smtplib
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

GMAIL_USER = "falgunisharma410@gmail.com"
GMAIL_APP_PASSWORD = "wolk ckon hfjc slrl"

# EY Logo as inline SVG data URI for email
EY_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 80" width="160" height="64">
  <rect width="200" height="80" fill="#2E2E38" rx="4"/>
  <text x="20" y="55" font-family="Arial,sans-serif" font-size="48" font-weight="bold" fill="#FFE600">EY</text>
  <text x="95" y="42" font-family="Arial,sans-serif" font-size="14" fill="#FFFFFF">Building a</text>
  <text x="95" y="60" font-family="Arial,sans-serif" font-size="14" fill="#FFFFFF">better working</text>
  <text x="95" y="78" font-family="Arial,sans-serif" font-size="14" fill="#FFFFFF">world</text>
</svg>"""

EY_LOGO_B64 = base64.b64encode(EY_LOGO_SVG.encode()).decode()


def send_collection_email(customer_email: str, customer_name: str,
                          invoice_id: str, amount: float,
                          days_overdue: int, custom_message: str = None) -> dict:
    """Send a real payment reminder email via Gmail SMTP with EY branding."""

    subject = f"Payment Reminder - Invoice {invoice_id} - Action Required"

    urgency_color = "#E74C3C" if days_overdue > 90 else "#E67E22" if days_overdue > 60 else "#F1C40F" if days_overdue > 30 else "#2ECC71"
    urgency_label = "CRITICAL" if days_overdue > 90 else "HIGH" if days_overdue > 60 else "MEDIUM" if days_overdue > 30 else "LOW"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
        <!-- EY Header with Logo -->
        <div style="background: #2E2E38; padding: 20px 30px; display: flex; align-items: center;">
            <div>
                <span style="color: #FFE600; font-size: 36px; font-weight: bold; font-family: Arial, sans-serif;">EY</span>
                <span style="color: #C4C4CD; font-size: 12px; margin-left: 15px;">Collections Department</span>
            </div>
        </div>

        <!-- Urgency Banner -->
        <div style="background: {urgency_color}; padding: 8px 30px; color: white; font-size: 12px; font-weight: bold;">
            PRIORITY: {urgency_label} — {days_overdue} DAYS OVERDUE
        </div>

        <!-- Body -->
        <div style="background: #ffffff; padding: 30px;">
            <p style="color: #333; font-size: 15px;">Dear <strong>{customer_name}</strong>,</p>

            <p style="color: #555; font-size: 14px; line-height: 1.6;">
                This is a formal reminder regarding your outstanding payment. Please review the details below and arrange for payment at your earliest convenience.
            </p>

            <!-- Invoice Table -->
            <table style="width: 100%; border-collapse: collapse; margin: 25px 0; border-radius: 6px; overflow: hidden;">
                <tr style="background: #2E2E38; color: #FFE600;">
                    <td colspan="2" style="padding: 12px 16px; font-weight: bold; font-size: 14px;">Invoice Details</td>
                </tr>
                <tr style="background: #f9f9f9;">
                    <td style="padding: 12px 16px; border-bottom: 1px solid #eee; font-weight: 600; color: #555; width: 40%;">Invoice ID</td>
                    <td style="padding: 12px 16px; border-bottom: 1px solid #eee; color: #333;">{invoice_id}</td>
                </tr>
                <tr>
                    <td style="padding: 12px 16px; border-bottom: 1px solid #eee; font-weight: 600; color: #555;">Amount Due</td>
                    <td style="padding: 12px 16px; border-bottom: 1px solid #eee; color: #E74C3C; font-weight: bold; font-size: 16px;">₹{amount:,.2f}</td>
                </tr>
                <tr style="background: #f9f9f9;">
                    <td style="padding: 12px 16px; border-bottom: 1px solid #eee; font-weight: 600; color: #555;">Days Overdue</td>
                    <td style="padding: 12px 16px; border-bottom: 1px solid #eee; color: {urgency_color}; font-weight: bold;">{days_overdue} days</td>
                </tr>
                <tr>
                    <td style="padding: 12px 16px; font-weight: 600; color: #555;">Status</td>
                    <td style="padding: 12px 16px;">
                        <span style="background: {urgency_color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px;">{urgency_label}</span>
                    </td>
                </tr>
            </table>

            <p style="color: #555; font-size: 14px; line-height: 1.6;">
                {custom_message if custom_message else "We kindly request you to process the payment at your earliest convenience to avoid further escalation."}
            </p>

            <p style="color: #555; font-size: 14px; line-height: 1.6;">
                If you have already made the payment, please disregard this reminder and share the payment confirmation with us at <a href="mailto:{GMAIL_USER}" style="color: #2E2E38;">{GMAIL_USER}</a>.
            </p>

            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                <p style="color: #333; font-size: 14px; margin: 0;">Best regards,</p>
                <p style="color: #2E2E38; font-size: 14px; font-weight: bold; margin: 5px 0;">Collections Team</p>
                <p style="color: #888; font-size: 12px; margin: 0;">EY Finance Operations</p>
            </div>
        </div>

        <!-- Footer -->
        <div style="background: #2E2E38; padding: 15px 30px; text-align: center;">
            <p style="color: #FFE600; font-size: 18px; font-weight: bold; margin: 0 0 4px 0;">EY</p>
            <p style="color: #888; font-size: 10px; margin: 0;">
                This is an automated reminder from EY Collections Assistant (Filli).<br>
                Building a better working world.
            </p>
        </div>
    </div>
    """

    plain_body = f"""Dear {customer_name},

This is a formal reminder regarding your outstanding payment.

PRIORITY: {urgency_label} — {days_overdue} DAYS OVERDUE

Invoice Details:
- Invoice ID: {invoice_id}
- Amount Due: Rs.{amount:,.2f}
- Days Overdue: {days_overdue} days

{custom_message if custom_message else "We kindly request you to process the payment at your earliest convenience to avoid further escalation."}

If you have already made the payment, please disregard this reminder and share the payment confirmation with us.

Best regards,
Collections Team
EY Finance Operations"""

    msg = MIMEMultipart("alternative")
    msg["From"] = f"EY Collections <{GMAIL_USER}>"
    msg["To"] = customer_email
    msg["Subject"] = subject
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, customer_email, msg.as_string())

        return {
            "status": "success",
            "message": f"Email sent successfully to {customer_email}",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to send email: {str(e)}",
        }


def send_escalation_email(manager_name: str, analyst_name: str,
                          customer_name: str, invoice_id: str,
                          amount: float, days_overdue: int,
                          emails_sent: int, calls_made: int,
                          broken_promises: int) -> dict:
    """Send an escalation notification email to a manager."""

    subject = f"🚨 ESCALATION — {customer_name} / Invoice {invoice_id} — Action Required"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
        <!-- Header -->
        <div style="background: #2E2E38; padding: 20px 30px;">
            <span style="color: #FFE600; font-size: 36px; font-weight: bold;">EY</span>
            <span style="color: #C4C4CD; font-size: 12px; margin-left: 15px;">Collections — Escalation Alert</span>
        </div>

        <!-- Red Banner -->
        <div style="background: #E74C3C; padding: 10px 30px; color: white; font-size: 13px; font-weight: bold;">
            🚨 ESCALATION REQUEST — MANAGEMENT INTERVENTION NEEDED
        </div>

        <!-- Body -->
        <div style="background: #ffffff; padding: 30px;">
            <p style="color: #333; font-size: 15px;">Dear <strong>{manager_name}</strong>,</p>

            <p style="color: #555; font-size: 14px; line-height: 1.6;">
                <strong>{analyst_name}</strong> has escalated the following account after exhausting standard collection methods.
                This requires your review and intervention.
            </p>

            <!-- Details Table -->
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0; border-radius: 6px; overflow: hidden;">
                <tr style="background: #2E2E38; color: #FFE600;">
                    <td colspan="2" style="padding: 12px 16px; font-weight: bold; font-size: 14px;">Account Details</td>
                </tr>
                <tr style="background: #f9f9f9;">
                    <td style="padding: 10px 16px; font-weight: 600; color: #555; width: 40%; border-bottom: 1px solid #eee;">Customer</td>
                    <td style="padding: 10px 16px; color: #333; border-bottom: 1px solid #eee;">{customer_name}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 16px; font-weight: 600; color: #555; border-bottom: 1px solid #eee;">Invoice</td>
                    <td style="padding: 10px 16px; color: #333; border-bottom: 1px solid #eee;">{invoice_id}</td>
                </tr>
                <tr style="background: #f9f9f9;">
                    <td style="padding: 10px 16px; font-weight: 600; color: #555; border-bottom: 1px solid #eee;">Amount</td>
                    <td style="padding: 10px 16px; color: #E74C3C; font-weight: bold; font-size: 16px; border-bottom: 1px solid #eee;">₹{amount:,.0f}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 16px; font-weight: 600; color: #555; border-bottom: 1px solid #eee;">Days Overdue</td>
                    <td style="padding: 10px 16px; color: #E74C3C; font-weight: bold; border-bottom: 1px solid #eee;">{days_overdue} days</td>
                </tr>
            </table>

            <!-- Follow-up History -->
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0; border-radius: 6px; overflow: hidden;">
                <tr style="background: #2E2E38; color: #FFE600;">
                    <td colspan="2" style="padding: 12px 16px; font-weight: bold; font-size: 14px;">Follow-up History</td>
                </tr>
                <tr style="background: #f9f9f9;">
                    <td style="padding: 10px 16px; font-weight: 600; color: #555; border-bottom: 1px solid #eee;">Emails Sent</td>
                    <td style="padding: 10px 16px; color: #333; border-bottom: 1px solid #eee;">{emails_sent}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 16px; font-weight: 600; color: #555; border-bottom: 1px solid #eee;">Calls Made</td>
                    <td style="padding: 10px 16px; color: #333; border-bottom: 1px solid #eee;">{calls_made}</td>
                </tr>
                <tr style="background: #f9f9f9;">
                    <td style="padding: 10px 16px; font-weight: 600; color: #555; border-bottom: 1px solid #eee;">Broken Promises to Pay</td>
                    <td style="padding: 10px 16px; color: #E74C3C; font-weight: bold; border-bottom: 1px solid #eee;">{broken_promises}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 16px; font-weight: 600; color: #555;">Escalated By</td>
                    <td style="padding: 10px 16px; color: #333;">{analyst_name}</td>
                </tr>
            </table>

            <div style="background: #FFF3CD; border: 1px solid #FFE600; border-radius: 6px; padding: 15px; margin: 20px 0;">
                <p style="color: #856404; font-size: 13px; font-weight: 600; margin: 0 0 8px 0;">Recommended Actions:</p>
                <ul style="color: #856404; font-size: 13px; margin: 0; padding-left: 20px; line-height: 1.8;">
                    <li>Direct negotiation with customer's senior management</li>
                    <li>Approve structured payment plan or settlement</li>
                    <li>Place account on credit hold</li>
                    <li>Issue formal demand notice via legal</li>
                </ul>
            </div>

            <p style="color: #555; font-size: 14px;">
                Please review this case on the <strong>Filli Dashboard</strong> and take appropriate action.
            </p>

            <div style="margin-top: 25px; padding-top: 15px; border-top: 1px solid #eee;">
                <p style="color: #333; font-size: 14px; margin: 0;">Best regards,</p>
                <p style="color: #2E2E38; font-size: 14px; font-weight: bold; margin: 5px 0;">Filli — AI Collections Assistant</p>
                <p style="color: #888; font-size: 12px; margin: 0;">EY Finance Operations</p>
            </div>
        </div>

        <!-- Footer -->
        <div style="background: #2E2E38; padding: 15px 30px; text-align: center;">
            <p style="color: #FFE600; font-size: 18px; font-weight: bold; margin: 0 0 4px 0;">EY</p>
            <p style="color: #888; font-size: 10px; margin: 0;">Automated escalation from Filli Collections Assistant</p>
        </div>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["From"] = f"EY Collections - Filli <{GMAIL_USER}>"
    msg["To"] = GMAIL_USER  # In production, this would be the manager's email
    msg["Subject"] = subject
    msg.attach(MIMEText(f"ESCALATION: {customer_name} / {invoice_id} / ₹{amount:,.0f} / {days_overdue}d overdue. Escalated by {analyst_name}. {emails_sent} emails, {calls_made} calls, {broken_promises} broken PTP.", "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, GMAIL_USER, msg.as_string())
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
