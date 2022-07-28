import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

def send_email(to: str, message: str, html_content: str = None):
    """Sends an email"""
    msg = MIMEMultipart()
    msg['From'] = 'your@email.com'
    msg['To'] = to
    msg['Subject'] = 'Update'
    msg.attach(MIMEText(message))
    if html_content:
        msg.attach(MIMEText(html_content, 'html'))
    mailserver = smtplib.SMTP('mail.privateemail.com', 587)
    # identify ourselves to smtp client
    mailserver.ehlo()
    # secure our email with tls encryption
    mailserver.starttls()
    # re-identify ourselves as an encrypted connection
    mailserver.ehlo()
    load_dotenv()
    mailserver.login('your@email.com', os.environ['EMAIL_PASSWORD'])
    mailserver.sendmail('your@email.com', to, msg.as_string())
    mailserver.quit()
