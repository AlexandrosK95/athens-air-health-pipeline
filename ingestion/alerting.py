import sys
sys.path.append(".")
import time
import smtplib
import os
import pandas as pd
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from storage.database import get_connection
from pathlib import Path
import logging
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SMTP_HOT = "smtp.office365.com"
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
SMTP_USERNAME=os.getenv("SMTP_USERNAME")

HAZARDOUS_THRESHOLD = 4


#def send_email(subject, html_body):
    #if not all([EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER]):
        #logger.warning("Email credentials not found in .env - skipping email.")
        #return False

    #try:
        #msg = MIMEMultipart("alternative")
        #msg["from"] = EMAIL_SENDER
        #msg["subject"] = subject
        #msg["to"] = EMAIL_RECEIVER

        #msg.attach(MIMEText(html_body, "html"))

        #with smtplib.SMTP(SMTP_HOT, SMTP_PORT) as server:
            #server.ehlo()
            #server.starttls
            #server.ehlo()
            #server.login(SMTP_USERNAME, EMAIL_PASSWORD)
            #server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())

        #logging.info(f"Email sent, {subject}")
        #return True

    #except Exception as e:
        #import traceback
        #traceback.print_exc()
        #logging.error(f"Failed to send email, {e}")
        #return False
def send_email(subject, html_body):
    """
    Στέλνει email μέσω Mailtrap API.
    """
    try:
        import mailtrap as mt

        mail = mt.Mail(
            sender=mt.Address(email="from@example.com", name="AQ Pipeline"),
            to=[mt.Address(email="to@example.com")],
            subject=subject,
            html=html_body,
        )

        client = mt.MailtrapClient(token=os.getenv("MAILTRAP_TOKEN"), sandbox=True, inbox_id=int(os.getenv("MAILTRAP_INBOX_ID")))
        client.send(mail)

        logger.info(f"Email sent: {subject}")
        return True

    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Failed to send email: {e}")
        return False

def check_and_send_hazardous_alerts():
    con = get_connection()

    df = con.execute("""
         SELECT 
            dd.name,
            de.driver_id,
            de.latitude,
            de.longitude,
            de.timestamp,
            de.exposure_value,
            de.pollutant
         FROM mart_driver_exposure de
         JOIN dim_drivers dd ON de.driver_id = dd.driver_id
         JOIN mart_aqi_classifications mac ON de.pollutant = mac.pollutant
         WHERE mac.aqi_class IN ('very_poor', 'hazardous')
         ORDER BY de.exposure_value DESC""").df()

    con.close()

    if df.empty:
        logging.warning("No hazardous exposure found - no alert needed.")
        return

    
    rows = ""
    for _, row in df.iterrows():
        rows += f"""
        <tr>
            <td>{row['name']}</td>
            <td>{row['pollutant'].upper()}</td>
            <td>{row['exposure_value']}</td>
            <td>{row['timestamp']}</td>
        </tr>
        """

    html_body = f"""
    <html><body>
    <h2 style = "color:red;"> Hazardous Air Quality Alert!</h2>
    <p> Οι παρακάτω οδηγοί έχουν εκτεθεί σε επικίνδυνα επίπεδα ρύπανσης:</p>
    <table border="1" cellpadding="5">
         <tr>
             <th>Οδηγός</th>
             <th>Ρύπος</th>
             <th>Τιμή</th>
             <th>Ώρα</th>
         </tr>
         {rows}
    </table>
    <p> Παρακαλώ αποφύγετε τις περιοχές υψηλής ρύπανσης!</p>
    </body></html>
    """

    send_email(
        subject = f"⚠️ Hazardous AQ Alert - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        html_body=html_body
    )

    logger.info(f"Hazardous alert sent for {len(df)} records.")



def send_daily_report():
    con = get_connection()

    df = con.execute("""
         SELECT 
            dd.name,
            ROUND(AVG(de.exposure_value), 2) AS avg_exposure,
            ROUND(MAX(de.exposure_value), 2) AS max_exposure,
            de.pollutant,
            COUNT(*)                         AS num_readings
        FROM mart_driver_exposure de
        JOIN dim_drivers dd ON de.driver_id = dd.driver_id
        GROUP BY dd.name, de.pollutant
        ORDER BY dd.name, de.pollutant
    """).df()

    con.close()

    if df.empty:
        logging.warning("No hazardous exposure found - no alert needed.")
        return

    
    rows = ""
    for _, row in df.iterrows():
        rows += f"""
        <tr>
            <td>{row['name']}</td>
            <td>{row['pollutant'].upper()}</td>
            <td>{row['avg_exposure']}</td>
            <td>{row['max_exposure']}</td>
            <td>{row['num_readings']}</td>
        </tr>
        """

    html_body = f"""
    <html><body>
    <h2 style = "color: #2ecc71;"> Daily Exposure Report</h2>
    <p>Ημερομηνία: <b>{datetime.utcnow().strftime('%Y-%m-%d')}<b>/<p>
    <table border="1" cellpadding="5">
         <tr>
             <th>Οδηγός</th>
             <th>Ρύπος</th>
             <th>Μέσος Ρύπος</th>
             <th>Μέγιστος Ρύπος</th>
             <th>Αριθμός Μετρήσεων</th>
         </tr>
         {rows}
    </table>
    </body></html>
    """

    send_email(
        subject = f"Daily Driver Exposure Report - {datetime.utcnow().strftime('%Y-%m-%d')}",
        html_body=html_body
    )

    logger.info(f"Daily report sent for {len(df)} driver-pollutant combinations.")


def send_monthly_report():
    con = get_connection()

    df = con.execute("""
         SELECT 
            de.pollutant,
            ROUND(AVG(de.exposure_value), 2) AS avg_exposure,
            ROUND(MAX(de.exposure_value), 2) AS max_exposure,
            ROUND(MIN(de.exposure_value), 2) AS min_exposure,
            COUNT(DISTINCT de.driver_id)     AS num_drivers,
            COUNT(*)                         AS total_readings
        FROM mart_driver_exposure de
        GROUP BY de.pollutant
        ORDER BY avg_exposure DESC
    """).df()

    con.close()

    if df.empty:
        logging.warning("No hazardous exposure found - no alert needed.")
        return

    
    rows = ""
    for _, row in df.iterrows():
        rows += f"""
        <tr>
            <td>{row['pollutant'].upper()}</td>
            <td>{row['avg_exposure']}</td>
            <td>{row['max_exposure']}</td>
            <td>{row['min_exposure']}</td>
            <td>{row['num_drivers']}</td>
             <td>{row['total_readings']}</td>
        </tr>
        """

    html_body = f"""
    <html><body>
    <h2 style = "color: #2ecc71;"> Daily Exposure Report</h2>
    <p>Ημερομηνία: <b>{datetime.utcnow().strftime('%Y-%m-%d')}<b>/<p>
    <table border="1" cellpadding="5">
         <tr>
             <th>Ρύπος</th>
             <th>Μέσος Ρύπος</th>
             <th>Μέγιστος Ρύπος</th>
             <th>Ελάχιστος Ρύπος</th>
             <th>Αριθμός Οδηγών</th>
             <th>Σύνολο Μετρήσεων</th>
         </tr>
         {rows}
    </table>
    </body></html>
    """

    send_email(
        subject = f"Monthly Driver Exposure Report - {datetime.utcnow().strftime('%Y-%m-%d')}",
        html_body=html_body
    )

    logger.info(f"Monthly report sent for {len(df)} pollutants.")


if __name__ == "__main__":
    print(f"EMAIL_SENDER: {EMAIL_SENDER}")
    print(f"EMAIL_PASSWORD: {EMAIL_PASSWORD}")
    print(f"EMAIL_RECEIVER: {EMAIL_RECEIVER}")
    print(f"SMTP_USERNAME: {SMTP_USERNAME}")
    print(f"MAILTRAP_TOKEN: {os.getenv('MAILTRAP_TOKEN')}")

    print("Testing alerting system...")

    print("\n1. Checking for hazardous alerts...")
    check_and_send_hazardous_alerts()
    time.sleep(10)

    print("\n2. Sending daily report...")
    send_daily_report()
    time.sleep(10)

    print("\n3. Sending monthly report...")
    send_monthly_report()

    print("\nDone!")