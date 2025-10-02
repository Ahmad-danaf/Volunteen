import smtplib
import os
import requests
import random

from django.core.cache import cache
from dotenv import load_dotenv
load_dotenv()
URL = "https://7103.api.greenapi.com/waInstance7103140551/sendMessage/"+os.getenv("GREEN_API","default-api-key")

MY_EMAIL = 'volunteen2023@gmail.com'  
EMAIL_HOST = 'smtp.gmail.com'  
PASSWORD = os.getenv("EMAIL_PASSWORD", "default-password")



class NotificationManager:

    @staticmethod
    def sent_mail(msg: str, mail: str):
        with smtplib.SMTP(EMAIL_HOST) as connection:
            connection.starttls()
            connection.login(user=MY_EMAIL, password=PASSWORD)
            connection.sendmail(
                from_addr=MY_EMAIL,
                to_addrs=mail,
                msg=f"Subject:volunteen\n\n{msg}\n".encode("utf-8")
            )

    @staticmethod
    def sent_whatsapp(msg: str, phone: str):
        payload = {
        "chatId": "972"+phone[1:]+"@c.us", 
        "message": msg, 
        "linkPreview": True
        }
        headers = {
        'Content-Type': 'application/json'
        }

        response = requests.post(URL, json=payload, headers=headers)
     
    @staticmethod   
    def sent_to_log_group_whatsapp(msg: str):
        payload = {
            "chatId": "120363418761716629@g.us", 
            "message": msg,
            "linkPreview": True
            }
        headers = {
            'Content-Type': 'application/json'
            }
        response = requests.post(URL, json=payload, headers=headers)


    @staticmethod
    def valid_phone(phone: str):
        return len(phone) == 10 and phone[0] == '0'
    
    
    @staticmethod
    def _generate_code(length: int = 6) -> str:
        """Generate a numeric code (default: 6 digits)."""
        return ''.join(str(random.randint(0, 9)) for _ in range(length))

    @staticmethod
    def send_verification_code(phone: str, expire_seconds: int = 300) -> None:
        """
        Generate + send a verification code via WhatsApp.
        Stores it in Django cache for `expire_seconds` (default: 5 min).
        """
        code = NotificationManager._generate_code()
        cache.set(f"phone_verif:{phone}", code, timeout=expire_seconds)
        NotificationManager.sent_whatsapp(
            f"👋 קוד האימות שלך ל-Volunteen הוא: {code}\n"
            f"הקוד תקף ל-{expire_seconds // 60} דקות.",
            phone
        )

    @staticmethod
    def verify_code(phone: str, code: str) -> bool:
        """
        Check if the provided code matches the cached one.
        """
        stored = cache.get(f"phone_verif:{phone}")
        return stored is not None and stored == code
