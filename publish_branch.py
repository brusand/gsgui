from configobj import ConfigObj
from mega import Mega
from smtplib import *
import ssl
from datetime import datetime
home = '/Users/bruno/gyp6band'

import smtplib, ssl
from email.mime.text import MIMEText


class Mail:

    def __init__(self):
        self.port = 465
        self.smtp_server_domain_name = "smtp.gmail.com"
        self.sender_mail = 'gyp6band@gmail.com'
        self.password = 'tqrbcixfspkmrvie'


    def send(self, emails, subject, content):
        ssl_context = ssl.create_default_context()
        service = smtplib.SMTP_SSL(self.smtp_server_domain_name, self.port, context=ssl_context)
        service.login(self.sender_mail, self.password)

        for email in emails:
            msg = MIMEText('Download : ' +  u''+ content + '')
            msg['Subject'] = subject
            msg['From'] = 'gyp6band@gmail.com'
            msg['To'] = 'gyp6band@gmail.com'

            #s = smtplib.SMTP(xxx, 25)
            #s.sendmail(xxx, xxx, msg.as_string())

            result = service.sendmail(self.sender_mail, email, msg.as_string())
            print(result)

        service.quit()

if __name__ == "__main__":
    config = ConfigObj('gsgui.ini')
    mega = Mega()
    m = mega.login('gyp6band@gmail.com', 'Bruno9798$')
    #filename = home + '/dist/' + 'rw.Gyp6Band.dmg'
    filename = home + '/dist/' + 'GS.dmg'
    #filename = home + '/dist/' + 'Gyp6Band'

    toFilname = 'GS' + '-' + config.get('version') + '-' + datetime.now().strftime('%Y%m%d%H%M') + '.dmg'

    os.rename( filename, home + '/dist/' + toFilname)

    print('Uploading ', toFilname)
    m.upload(home + '/dist/' + toFilname)
    # Use it in get_link function
    fileid =  m.find(toFilname)
    link = m.get_link(fileid)
    # It will print the link
    print('link', link)
    print('send link')
    mails = ['gyp6band@gmail.com']
    subject = 'GS' + '-' + gyp6BandConfig.get('version')
    content = link

    mail = Mail()
    mail.send(mails, subject, content)
    print('link sent')