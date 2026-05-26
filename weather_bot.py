import requests
import smtplib
import os
from email.mime.text import MIMEText
from datetime import datetime
import pytz
from anthropic import Anthropic

# System prompt for Claude
SYSTEM_PROMPT = """You are a friendly morning weather assistant.

Your job: Transform raw weather data into a personalized daily weather email.

Rules:
1. Be concise and helpful (2-3 sentences about weather + 1 actionable tip)
2. Choose emojis based on ACTUAL conditions (cold=❄️, hot=🔥, rainy=🌧️, sunny=☀️, windy=💨, pollen=🌾)
3. Give ONE specific, actionable tip based on the weather
4. Use the user's name if provided
5. Warm, encouraging, friendly tone (not robotic or overly formal)
6. Format clearly with simple section breaks (---)
7. Total length: keep to 150-200 words max

Do NOT:
- Use more than 4-5 emojis total
- Make up weather data
- Include disclaimers or caveats
- Ask questions back to user
- Be overly dramatic

Remember: This is a morning message to help someone prepare their day."""

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

def create_prompt_for_claude(weather_data, pollen_data, user_name="there"):
    """Convert raw API data into a detailed prompt for Claude"""
    current_weather = weather_data['current']
    daily_weather = weather_data['daily']
    
    temp = current_weather['temperature_2m']
    wind = current_weather['wind_speed_10m']
    current_uv = current_weather['uv_index']
    max_uv = daily_weather['uv_index_max'][0]
    
    # Safely extract pollen data
    tree_pollen = "unknown"
    grass_pollen = "unknown"
    weed_pollen = "unknown"
    
    if 'current' in pollen_data:
        current_pollen = pollen_data['current']
        tree_pollen = current_pollen.get('tree_pollen', 'unknown')
        grass_pollen = current_pollen.get('grass_pollen', 'unknown')
        weed_pollen = current_pollen.get('weed_pollen', 'unknown')
    
    # Get current time in CST for context
    cst = pytz.timezone('America/Chicago')
    now_cst = datetime.now(cst)
    day_of_week = now_cst.strftime('%A')
    
    prompt = f"""Generate a personalized morning weather email for {user_name}.

Current weather in Eden Prairie, Minnesota ({day_of_week}):
- Temperature: {temp}°F
- Wind Speed: {wind} mph
- Current UV Index: {current_uv}
- Peak UV Today: {max_uv}
- Tree Pollen Level: {tree_pollen}
- Grass Pollen Level: {grass_pollen}
- Weed Pollen Level: {weed_pollen}

Based on these conditions:
1. Give {user_name} a personalized greeting
2. Describe the weather briefly and what it means for their day
3. Pick ONE specific, actionable tip (e.g., "Bring an umbrella", "Use sunscreen", "Wear layers", "Keep windows closed if allergies")
4. End with encouragement for the day

Be authentic and helpful, not generic."""
    
    return prompt

def generate_weather_message(weather_data, pollen_data, user_name="there", api_key=None):
    """Use Claude to generate the weather message"""
    try:
        # Pass api_key explicitly to Anthropic client
        client = Anthropic(api_key=api_key)
        
        prompt = create_prompt_for_claude(weather_data, pollen_data, user_name)
        
        print("Calling Claude API to generate message...")
        message = client.messages.create(
            model="claude-opus-4-1-20250805",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        generated_message = message.content[0].text
        print(f"✓ Claude generated message successfully ({len(generated_message)} characters)")
        return generated_message
        
    except Exception as e:
        print(f"✗ Claude API error: {e}")
        raise

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
    claude_api_key = os.getenv('CLAUDE_API_KEY', '').strip()
    
    # Validate all secrets are present
    if not sender_email:
        raise ValueError("ERROR: GMAIL_ADDRESS is not set in GitHub secrets")
    if not sender_password:
        raise ValueError("ERROR: GMAIL_PASSWORD is not set in GitHub secrets")
    if not recipient_emails_str:
        raise ValueError("ERROR: RECIPIENT_EMAILS is not set in GitHub secrets")
    if not claude_api_key:
        raise ValueError("ERROR: CLAUDE_API_KEY is not set in GitHub secrets")
    
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
    print("Step 1: Fetching weather and pollen data for Eden Prairie, MN...")
    weather, pollen = get_weather_and_pollen(44.8194, -93.4891)
    
    print("Step 2: Generating personalized message with Claude AI...")
    message = generate_weather_message(weather, pollen, user_name=user_name, api_key=claude_api_key)
    
    print("Step 3: Sending email...")
    send_email(sender_email, sender_password, recipient_emails, "☀️ Your Daily Weather Report", message)
    
    print("\n✓ Weather bot completed successfully!")
    print("\n--- Message Preview ---")
    print(message)
    print("--- End Preview ---")
