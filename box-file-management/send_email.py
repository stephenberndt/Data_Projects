# -*- coding: utf-8 -*-

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from configparser import ConfigParser

parser = ConfigParser()
parser.read('config.ini')

class EmailClient(object):
    def __init__(self, from_address, password):

        self.server = smtplib.SMTP(parser.get('Analytics Gmail', 'server'), 587)
        self.server.starttls()
        self.server.login(from_address, password)
        self.from_address = from_address
        print('logging in to email server for ' + self.from_address)

    def send_email(self, to_address, subject, body, attach_file=None):
        self.msg = MIMEMultipart()
        self.msg['From'] = self.from_address
        self.msg['To'] = to_address
        self.msg['Subject'] = subject
        body = body
        self.msg.attach(MIMEText(body, 'plain'))

        if attach_file is not None:
            filename = os.path.basename(attach_file)
            attachment = open(attach_file, "rb")
            part = MIMEBase('application', 'octet-stream')
            part.set_payload((attachment).read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', "attachment; filename= {}".format(filename))
            print('attaching ' + filename + ' to message')
            self.msg.attach(part)

        text = self.msg.as_string()
        print('sending \'' + subject + '\'')
        self.server.sendmail(self.from_address, to_address, text)
        self.server.quit()
        print('message sent to ' + to_address)


if __name__ == '__main__':
    # Sample execution
    from_address = parser.get('Analytics Gmail', 'username')
    pwd = parser.get('Analytics Gmail', 'password')
    ec = EmailClient(from_address, pwd)
    ec.send_email(to_address='stephen_berndt@discovery.com', subject="Greetings from Python", body=";)", attach_file='test.py')
