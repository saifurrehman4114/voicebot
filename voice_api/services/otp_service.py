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

            # HTML email content with nice styling
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 0; }}
                    .container {{ max-width: 600px; margin: 50px auto; background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden; }}
                    .header {{ background: linear-gradient(135deg, #25D366 0%, #128C7E 100%); color: white; padding: 30px; text-align: center; }}
                    .header h1 {{ margin: 0; font-size: 28px; }}
                    .content {{ padding: 40px; }}
                    .otp-box {{ background: #f8f9fa; border: 2px dashed #25D366; border-radius: 10px; padding: 30px; text-align: center; margin: 30px 0; }}
                    .otp-code {{ font-size: 48px; font-weight: bold; color: #128C7E; letter-spacing: 10px; }}
                    .info {{ color: #666; font-size: 14px; line-height: 1.6; }}
                    .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #999; font-size: 12px; }}
                    .icon {{ font-size: 60px; margin-bottom: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="icon">💬</div>
                        <h1>Voicebot Chat</h1>
                    </div>
                    <div class="content">
                        <h2 style="color: #333; margin-top: 0;">Verification Code</h2>
                        <p class="info">You requested a verification code to access your Voicebot Chat account. Use the code below to complete your verification:</p>

                        <div class="otp-box">
                            <div class="otp-code">{otp_code}</div>
                        </div>

                        <p class="info">
                            <strong>This code will expire in 10 minutes.</strong><br><br>
                            If you didn't request this code, please ignore this email.
                        </p>
                    </div>
                    <div class="footer">
                        <p>This is an automated message from Voicebot Chat.<br>Please do not reply to this email.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Plain text fallback
            text_content = f"Your Voicebot verification code is: {otp_code}\n\nThis code will expire in 10 minutes."

            # Sender information
            sender = {
                "name": "Voicebot Chat",
                "email": "7d9ffd006@smtp-brevo.com"
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
