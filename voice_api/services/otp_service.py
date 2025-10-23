"""
OTP Service for email verification using Brevo (Sendinblue)
File: voice_api/services/otp_service.py
"""

import random
import string
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
import logging
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

logger = logging.getLogger('voice_api')


class OTPService:
    """Service to handle OTP generation and sending via email (Brevo)"""

    @staticmethod
    def generate_otp(length=6):
        """Generate a random 6-digit OTP code"""
        return ''.join(random.choices(string.digits, k=length))

    @staticmethod
    def send_otp(email, otp_code):
        """
        Send OTP via Email using Brevo API

        Args:
            email: Email address (e.g., user@example.com)
            otp_code: The OTP code to send

        Returns:
            tuple: (success: bool, message: str, message_id: str or None)
        """
        try:
            # Get Brevo API key from settings
            brevo_api_key = getattr(settings, 'BREVO_API_KEY', None)

            if not brevo_api_key:
                logger.error("Brevo API key not configured")
                return (
                    False,
                    "Email service not configured. Please contact administrator.",
                    None
                )

            # Configure API key
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = brevo_api_key

            # Create API instance
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

            # Email subject
            subject = "Your Voicebot Verification Code"

            # HTML email content with Copilot-inspired styling
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{
                        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Roboto', 'Helvetica Neue', Arial, sans-serif;
                        background: linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 100%);
                        margin: 0;
                        padding: 0;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 50px auto;
                        background: white;
                        border-radius: 20px;
                        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
                        overflow: hidden;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
                        background-size: 200% 200%;
                        animation: gradientShift 8s ease infinite;
                        color: white;
                        padding: 40px;
                        text-align: center;
                        position: relative;
                    }}
                    @keyframes gradientShift {{
                        0%, 100% {{ background-position: 0% 50%; }}
                        50% {{ background-position: 100% 50%; }}
                    }}
                    .header h1 {{
                        margin: 0;
                        font-size: 32px;
                        font-weight: 700;
                        letter-spacing: -0.5px;
                    }}
                    .header-subtitle {{
                        margin-top: 8px;
                        font-size: 14px;
                        opacity: 0.9;
                    }}
                    .icon {{
                        font-size: 64px;
                        margin-bottom: 16px;
                        filter: drop-shadow(0 4px 12px rgba(0, 0, 0, 0.2));
                    }}
                    .content {{
                        padding: 48px 40px;
                    }}
                    .greeting {{
                        font-size: 18px;
                        color: #333;
                        margin-bottom: 16px;
                        font-weight: 500;
                    }}
                    .info {{
                        color: #666;
                        font-size: 15px;
                        line-height: 1.8;
                        margin-bottom: 32px;
                    }}
                    .otp-box {{
                        background: linear-gradient(135deg, rgba(102, 126, 234, 0.08) 0%, rgba(240, 147, 251, 0.08) 100%);
                        border: 2px solid #667eea;
                        border-radius: 16px;
                        padding: 32px;
                        text-align: center;
                        margin: 32px 0;
                        box-shadow: 0 8px 24px rgba(102, 126, 234, 0.12);
                    }}
                    .otp-label {{
                        font-size: 12px;
                        color: #667eea;
                        font-weight: 600;
                        text-transform: uppercase;
                        letter-spacing: 1.5px;
                        margin-bottom: 12px;
                    }}
                    .otp-code {{
                        font-size: 56px;
                        font-weight: 700;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        background-clip: text;
                        letter-spacing: 12px;
                        font-family: 'Courier New', monospace;
                    }}
                    .warning-box {{
                        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
                        border-left: 4px solid #ef4444;
                        border-radius: 12px;
                        padding: 20px;
                        margin: 24px 0;
                    }}
                    .warning-box strong {{
                        color: #dc2626;
                        font-size: 14px;
                    }}
                    .warning-text {{
                        color: #666;
                        font-size: 13px;
                        margin-top: 8px;
                        line-height: 1.6;
                    }}
                    .footer {{
                        background: linear-gradient(to bottom, #f8f9fa 0%, #e9ecef 100%);
                        padding: 32px 40px;
                        text-align: center;
                        border-top: 1px solid #e5e5e5;
                    }}
                    .footer-logo {{
                        font-size: 32px;
                        margin-bottom: 12px;
                    }}
                    .footer-text {{
                        color: #999;
                        font-size: 12px;
                        line-height: 1.6;
                    }}
                    .footer-brand {{
                        color: #667eea;
                        font-weight: 600;
                        text-decoration: none;
                    }}
                    .feature-icons {{
                        display: flex;
                        justify-content: center;
                        gap: 32px;
                        margin: 32px 0;
                    }}
                    .feature {{
                        text-align: center;
                    }}
                    .feature-icon {{
                        font-size: 28px;
                        margin-bottom: 8px;
                    }}
                    .feature-label {{
                        font-size: 11px;
                        color: #999;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="icon">🤖</div>
                        <h1>Voicebot AI</h1>
                        <div class="header-subtitle">Your Intelligent Voice Companion</div>
                    </div>
                    <div class="content">
                        <div class="greeting">Welcome back! 👋</div>
                        <p class="info">You requested a verification code to access your Voicebot AI account. Enter the code below to complete your sign-in:</p>

                        <div class="otp-box">
                            <div class="otp-label">Verification Code</div>
                            <div class="otp-code">{otp_code}</div>
                        </div>

                        <div class="warning-box">
                            <strong>⏱️ Expires in 10 minutes</strong>
                            <div class="warning-text">This code is valid for 10 minutes. If it expires, you can request a new one.</div>
                        </div>

                        <p class="info" style="margin-bottom: 0;">
                            If you didn't request this code, you can safely ignore this email. Your account remains secure.
                        </p>

                        <div class="feature-icons">
                            <div class="feature">
                                <div class="feature-icon">🎤</div>
                                <div class="feature-label">Voice Messages</div>
                            </div>
                            <div class="feature">
                                <div class="feature-icon">💬</div>
                                <div class="feature-label">Smart Chat</div>
                            </div>
                            <div class="feature">
                                <div class="feature-icon">🔒</div>
                                <div class="feature-label">Secure & Private</div>
                            </div>
                        </div>
                    </div>
                    <div class="footer">
                        <div class="footer-logo">🤖</div>
                        <p class="footer-text">
                            This is an automated message from <span class="footer-brand">Voicebot AI</span><br>
                            Please do not reply to this email.
                        </p>
                        <p class="footer-text" style="margin-top: 16px;">
                            © 2025 Voicebot AI. All rights reserved.
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Plain text fallback
            text_content = f"Your Voicebot verification code is: {otp_code}\n\nThis code will expire in 10 minutes."

            # Sender information - use verified email from settings
            sender = {
                "name": getattr(settings, 'BREVO_SENDER_NAME', 'Voicebot Chat'),
                "email": getattr(settings, 'BREVO_SENDER_EMAIL', 'saifrh.work@gmail.com')
            }

            # Recipient
            to = [{"email": email}]

            # Create email campaign
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=to,
                html_content=html_content,
                text_content=text_content,
                sender=sender,
                subject=subject
            )

            # Send email
            api_response = api_instance.send_transac_email(send_smtp_email)

            logger.info(f"OTP email sent successfully to {email}. Message ID: {api_response.message_id}")

            return (
                True,
                f"Verification code sent to {email}",
                api_response.message_id
            )

        except ApiException as e:
            error_msg = f"Brevo API error: {str(e)}"
            logger.error(error_msg)
            return (False, f"Failed to send email: {str(e)}", None)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return (False, f"Failed to send email: {str(e)}", None)

    @staticmethod
    def get_otp_expiration(minutes=10):
        """Get the expiration time for OTP (default 10 minutes from now)"""
        return timezone.now() + timedelta(minutes=minutes)

    @staticmethod
    def is_otp_expired(expires_at):
        """Check if OTP has expired"""
        return timezone.now() > expires_at

    @staticmethod
    def format_email(email):
        """
        Format and validate email address

        Args:
            email: Raw email input

        Returns:
            Formatted email address (lowercase, trimmed)
        """
        return email.strip().lower()
