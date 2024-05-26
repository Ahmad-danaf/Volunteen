import smtplib

MY_EMAIL = 'volunteen2023@gmail.com'  
EMAIL_HOST = 'smtp.gmail.com'  
PASSWORD = 'spzsornkikalkbvu'  # spzs ornk ikal kbvu 



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

