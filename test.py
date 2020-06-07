import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from_email = "ged.firebird@gmail.com"
to_email = "maxkburton@gmail.com"
password = "XR,W=R&N7o3q_@QuWU!vfAbU"

message = MIMEMultipart("alternative")
message["Subject"] = "Scraping Results"
message["From"] = from_email
message["To"] = to_email

text = """\
Attached are the files generated from the scrape of [Restaurant Name]

[Errors/Success]

Time Elapsed: [Time Elapsed]"""
html = """\
<html>
  <body>
    <p>Attached are the files generated from the scrape of [Restaurant Name]
    <br><br>
    [Errors/Success]
    <br><br>
    Time Elapsed: [Time Elapsed]
    </p>
  </body>
</html>
"""

filename = "Raja_PA32AN_menu.json"  # In same directory as script

# Open file in binary mode
with open(filename, "rb") as attachment:
    # Add file as application/octet-stream
    # Email client can usually download this automatically as attachment
    part = MIMEBase("application", "octet-stream")
    part.set_payload(attachment.read())

# Encode file in ASCII characters to send by email
encoders.encode_base64(part)

# Add header as key/value pair to attachment part
part.add_header(
    "Content-Disposition",
    f"attachment; filename= {filename}",
)

# Add attachment to message and convert message to string
message.attach(part)

# Add HTML/plain-text parts to MIMEMultipart message
# The email client will try to render the last part first
message.attach(MIMEText(text, "plain"))
message.attach(MIMEText(html, "html"))

# creates SMTP session 
s = smtplib.SMTP('smtp.gmail.com', 587)

# start TLS for security 
s.starttls()

# password = input("")

# Authentication 
s.login(from_email, password)

# sending the mail 
s.sendmail(from_email, to_email, message.as_string())

# terminating the session 
s.quit()
