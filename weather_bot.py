import requests
import smtplib
import os
from email.mime.text import MIMEText
from datetime import datetime
import pytz

def get_weather_and_pollen(latitude, longitude):
    """Fetch weather + UV + pollen from Open-Meteo (all free)"""
    # Weather + UV index
    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,weather_code,wind_speed_10m,uv_index&daily=uv_index_max"
    weather_response = requests.get(weather_url)
    weather_data = weather_response.json()
    
    # Pollen data (US only, from Open-Meteo)
    pollen_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={latitude}&longitude={longitude}&current=tree_pollen,grass_pollen,weed_pollen"
    pollen_response = requests.get(pollen_url)
    pollen_data = pollen_response.json()
    
    return weather_data, pollen_data

def get_uv_index_level(uv_index):
    """Convert UV index number to risk level"""
    if uv_index < 3:
        return "Low ☀️"
    elif uv_index < 6:
        return "Moderate ⚠️"
    elif uv_index < 8:
        return "High 🔴"
    elif uv_index < 11:
        return "Very High 🔴🔴"
    else:
        return "Extreme 🔴🔴🔴"

def get_pollen_level(pollen_count):
    """Convert pollen count to level"""
    if pollen_count is None or pollen_count < 10:
        return "Low 👍"
    elif pollen_count < 50:
        return "Moderate 😐"
    elif pollen_count < 200:
        return "High 😷"
    else:
        return "Very High 🤧"

def format_weather_message(weather_data, pollen_data, user_name="there"):
    """Format weather data with personalization"""
    current_weather = weather_data['current']
    daily_weather = weather_data['daily']
    
    temp = current_weather['temperature_2m']
    wind = current_weather['wind_speed_10m']
    current_uv = current_weather['uv_index']
    max_uv = daily_weather['uv_index_max'][0]
    
    # Pollen data - safely extract from API response
    tree_pollen = None
    grass_pollen = None
    weed_pollen = None
    
    if 'current' in pollen_data:
        current_pollen = pollen_data['current']
        tree_pollen = current_pollen.get('tree_pollen')
        grass_pollen = current_pollen.get('grass_pollen')
        weed_pollen = current_pollen.get('weed_pollen')
    
    # Temperature-based greeting
    if temp < 20:
        greeting = f"Brr, it's cold out there, {user_name}!"
    elif temp < 40:
        greeting = f"Good morning, {user_name}! Bundle up!"
    elif temp < 60:
        greeting = f"Good morning, {user_name}! Nice day ahead!"
    else:
        greeting = f"Good morning, {user_name}! Looks warm today!"
    
    # Get current time in CST
    cst = pytz.timezone('America/Chicago')
    now_cst = datetime.now(cst)
    time_str = now_cst.strftime('%A, %B %d, %Y at %I:%M %p %Z')
    
    # Build pollen section
    pollen_section = ""
    if tree_pollen is not None or grass_pollen is not None or weed_pollen is not None:
        pollen_section = f"""
🌾 POLLEN LEVELS
   Tree Pollen: {get_pollen_level(tree_pollen)}
   Grass Pollen: {get_pollen_level(grass_pollen)}
   Weed Pollen: {get_pollen_level(weed_pollen)}
   💡 Tip: Keep windows closed if pollen is High"""
    else:
        pollen_section = """
🌾 POLLEN LEVELS
   (Data unavailable - check local pollen counts)"""
    
    # Build message
    message = f"""{greeting}

═══════════════════════════════════
📍 EDEN PRAIRIE, MINNESOTA WEATHER
═══════════════════════════════════

🌡️  CURRENT CONDITIONS
   Temperature: {temp}°F
   Wind Speed: {wind} mph
   
☀️  UV INDEX
   Current: {current_uv} ({get_uv_index_level(current_uv)})
   Today's Max: {max_uv}
   💡 Tip: Apply sunscreen if UV is High or higher
   {pollen_section}

═══════════════════════════════════
Updated: {time_str}

Have a great day! 🌤️"""
    return message

def send_email(sender_email, sender_password, recipient_emails, subject, body):
    """Send email via Gmail SMTP to one or more recipients"""
    try:
        # Convert single email to list if needed
        if isinstance(recipient_emails, str):
            recipient_emails = [recipient_emails]
        
        # Remove empty emails and strip whitespace
        recipient_emails = [e.strip() for e in recipient_emails if e.strip()]
        
        if not recipient_emails:
            raise ValueError("No valid recipient emails provided")
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = ', '.join(recipient_emails)
        
        print(f"Connecting to Gmail...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            print(f"Logging in as {sender_email}...")
            server.login(sender_email, sender_password)
            print(f"Sending to {len(recipient_emails)} recipient(s)...")
            server.sendmail(sender_email, recipient_emails, msg.as_string())
        
        print(f"✓ Email sent successfully to: {', '.join(recipient_emails)}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"✗ Gmail login failed. Check your app password.")
        print(f"  Error: {e}")
        raise
    except Exception as e:
        print(f"✗ Email sending failed: {e}")
        raise

if __name__ == "__main__":
    # Get secrets from environment
    sender_email = os.getenv('GMAIL_ADDRESS', '').strip()
    sender_password = os.getenv('GMAIL_PASSWORD', '').strip()
    recipient_emails_str = os.getenv('RECIPIENT_EMAILS', '').strip()
    user_name = os.getenv('USER_NAME', 'there').strip()
    
    # Validate
    if not sender_email:
        raise ValueError("ERROR: GMAIL_ADDRESS is not set in GitHub secrets")
    if not sender_password:
        raise ValueError("ERROR: GMAIL_PASSWORD is not set in GitHub secrets")
    if not recipient_emails_str:
        raise ValueError("ERROR: RECIPIENT_EMAILS is not set in GitHub secrets")
    
    # Parse multiple emails (comma or semicolon separated)
    recipient_emails = [e.strip() for e in recipient_emails_str.replace(';', ',').split(',')]
    recipient_emails = [e for e in recipient_emails if e]  # Remove empty strings
    
    print(f"Configuration loaded:")
    print(f"  Sender: {sender_email}")
    print(f"  Recipients ({len(recipient_emails)}): {', '.join(recipient_emails)}")
    print(f"  User name: {user_name}")
    print()
    
    # Run the bot
    # Eden Prairie, Minnesota coordinates: 44.8194, -93.4891
    print("Fetching weather and pollen data for Eden Prairie, MN...")
    weather, pollen = get_weather_and_pollen(44.8194, -93.4891)
    
    print("Formatting message...")
    message = format_weather_message(weather, pollen, user_name=user_name)
    
    print("Sending email...")
    send_email(sender_email, sender_password, recipient_emails, "☀️ Your Daily Weather Report", message)
    
    print("\n✓ Weather bot completed successfully!")
