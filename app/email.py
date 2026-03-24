import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.config import settings


def send_set_password_email(to_email: str, name: str, token: str):
    """
    Sends a 'Set your password' email to a guest after they place an order.
    The link points to your frontend's /set-password?token=<token> page.
    """
    set_password_url = f"{settings.FRONTEND_URL}/set-password?token={token}"

    html = f"""
    <div style="font-family: 'DM Sans', Arial, sans-serif; max-width: 560px; margin: 0 auto; color: #111;">
      <div style="background: #0a0a0a; padding: 32px 40px;">
        <p style="color: #f9a8d4; font-size: 11px; font-weight: 700; letter-spacing: 0.4em; text-transform: uppercase; margin: 0;">
          Your Order is Confirmed
        </p>
        <h1 style="color: #fff; font-size: 32px; font-weight: 900; margin: 12px 0 0;">
          Thank you, {name.split()[0]}
        </h1>
      </div>

      <div style="padding: 40px;">
        <p style="font-size: 15px; line-height: 1.7; color: #444;">
          We've received your order and it's being prepared. We also created an account for you
          so you can track your orders anytime.
        </p>

        <p style="font-size: 15px; line-height: 1.7; color: #444;">
          Set a password to secure your account and get full access:
        </p>

        <div style="text-align: center; margin: 36px 0;">
          <a href="{set_password_url}"
             style="background: #ec4899; color: #fff; font-size: 13px; font-weight: 700;
                    letter-spacing: 0.2em; text-transform: uppercase; padding: 16px 36px;
                    text-decoration: none; display: inline-block;">
            Set My Password
          </a>
        </div>

        <p style="font-size: 12px; color: #999; line-height: 1.6;">
          This link expires in 48 hours. If you didn't place this order, you can safely ignore this email.
        </p>
      </div>

      <div style="border-top: 1px solid #f0f0f0; padding: 24px 40px;">
        <p style="font-size: 11px; color: #bbb; margin: 0;">
          Can't click the button? Copy this link into your browser:<br/>
          <span style="color: #ec4899;">{set_password_url}</span>
        </p>
      </div>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your order is confirmed — set your password"
    msg["From"]    = settings.MAIL_FROM
    msg["To"]      = to_email
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.MAIL_HOST, settings.MAIL_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
        server.sendmail(settings.MAIL_FROM, to_email, msg.as_string())