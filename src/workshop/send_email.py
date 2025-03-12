import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(sender_email, receiver_email, subject, body, smtp_server, smtp_port, sender_password):
    try:
        # Create the email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Set up the server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Secure the connection
        
        # Login to the server
        server.login(sender_email, sender_password)
        
        # Send the email
        server.sendmail(sender_email, receiver_email, msg.as_string())
        
        # Quit the server connection
        server.quit()
        
        print("Email sent successfully!")
    
    except Exception as e:
        print(f"Error: {e}")

# # Usage Example:
# sender_email = "gabalepankaj@gmail.com"
# receiver_email = "pankaj.gabale@au.ey.com"
# subject = "Test Email"
# body = "This is a test email sent using Python."
# smtp_server = "smtp.gmail.com"  # For Gmail
# smtp_port = 587  # SMTP port for Gmail
# sender_password = "wqil wwlp laxm ndud"  # Make sure to use an App Password if using Gmail

# send_email(sender_email, receiver_email, subject, body, smtp_server, smtp_port, sender_password)