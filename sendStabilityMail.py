import smtplib
from ast import literal_eval
from email.message import EmailMessage



def send_mail(body_text):
    with open("mail.config", "r") as f:
        s = f.read()
        config = literal_eval(s)

    msg = EmailMessage()
    msg["Subject"] = "#stability testing report"
    msg["From"] = config["sender"]
    msg["To"] = "trigger@applet.ifttt.com"
    msg.set_content(str(body_text))

    mailserver = smtplib.SMTP(config["mailserver_host"],config["mailserver_port"])
    mailserver.ehlo()
    mailserver.starttls()
    mailserver.ehlo()
    mailserver.login(config["sender"], config["mailserver_app_password"])

    mailserver.send_message(msg)

    mailserver.quit()

if __name__ == "__main__":
    send_mail("three dashes on line is fine---\ntext after dashes")
    send_mail("three dashes on line by themselves removes all trailing message\n---\nunless you see this text after dashes")