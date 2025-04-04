import smtplib
import os
import requests

from dotenv import load_dotenv
load_dotenv()
URL = "https://7103.api.greenapi.com/waInstance7103140551/sendMessage/"+os.getenv("GREEN_API","default-api-key")

MY_EMAIL = 'volunteen2023@gmail.com'  
EMAIL_HOST = 'smtp.gmail.com'  
PASSWORD = os.getenv("EMAIL_PASSWORD", "default-password")



class NotificationManager:
    def sent_mail(self, msg: str, mail: str):
        with smtplib.SMTP(EMAIL_HOST) as connection:
            connection.starttls()
            connection.login(user=MY_EMAIL, password=PASSWORD)
            connection.sendmail(
                from_addr=MY_EMAIL,
                to_addrs=mail,
                msg=f"Subject:volunteen\n\n{msg}\n".encode("utf-8")
            )
            
    def sent_whatsapp(msg: str, phone: str):
        print("972"+phone[1:]+"@c.us")
        payload = {
        "chatId": "972"+phone[1:]+"@c.us", 
        "message": msg, 
        "linkPreview": True
        }
        headers = {
        'Content-Type': 'application/json'
        }

        response = requests.post(URL, json=payload, headers=headers)

        print(response.text.encode('utf8'))
        
        
    def valid_phone(self, phone: str):
        if len(phone) != 10 or phone[0] != '0':
            return False
        return True

