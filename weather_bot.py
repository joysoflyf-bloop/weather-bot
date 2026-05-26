import requests
import smtplib
import os
from email.mime.text import MIMEText
from datetime import datetime

sender_email = os.getenv('GMAIL_ADDRESS')
sender_password = os.getenv('GMAIL_PASSWORD')

# 1. FETCH WEATHER (Open-Meteo, no API key needed)
def get_weather(latitude, longitude):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,weather_code,wind_speed_10m"
    response = requests.get(url)
    return response.json()

# 2. PARSE WEATHER DATA
def format_weather_message(weather_data):
    current = weather_data['current']
    temp = current['temperature_2m']
    wind = current['wind_speed_10m']
    
    message = f"""
Good morning!

Today's weather:
- Temperature: {temp}°F
- Wind: {wind} mph
- Time: {datetime.now().strftime('%A, %B %d, %Y')}

Have a great day!
"""
    return message

# 3. SEND EMAIL
def send_email(recipient_email, subject, body):
    sender_email = "your_email@gmail.com"
    sender_password = "your_app_password"  # See Step 3 below
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
    
    print("Email sent!")

# 4. MAIN
if __name__ == "__main__":
    # Your location (Minneapolis: 44.9778, -93.2650)
    latitude = 44.9778
    longitude = -93.2650
    
    weather = get_weather(latitude, longitude)
    message = format_weather_message(weather)
    send_email("nanisandy2@gmail.com", "Your daily weather", message)
