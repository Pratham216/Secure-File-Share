import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .config import settings

def send_verification_email(email: str, token: str):
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    
    message = MIMEMultipart()
    message["From"] = settings.SMTP_USERNAME
    message["To"] = email
    message["Subject"] = "Email Verification"
    
    body = f"""
    <html>
        <body>
            <h2>Email Verification</h2>
            <p>Please click the following link to verify your email:</p>
            <a href="{verification_url}">Verify Email</a>
            <p>If you didn't request this, please ignore this email.</p>
        </body>
    </html>
    """
    
    message.attach(MIMEText(body, "html"))
    
    with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(message)