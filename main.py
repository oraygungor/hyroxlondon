import requests
import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from bs4 import BeautifulSoup

# --- Configuration ---
HYROX_URL = "https://gb.hyrox.com/checkout/hyrox-london-excel-season-25-26-rzstou"

# --- Securely load credentials from Environment Variables ---
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD')
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL')
JSONBIN_API_KEY = os.environ.get('JSONBIN_API_KEY')
JSONBIN_URL = os.environ.get('JSONBIN_URL')

# --- ntfy Configuration (NEW) ---
NTFY_TOPIC = os.environ.get('NTFY_TOPIC') # Your secret topic name

def get_current_active_tickets():
    # This function remains unchanged
    print("Fetching current ticket status from HYROX page...")
    try:
        response = requests.get(HYROX_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        script_tag = soup.find('script', id='__NEXT_DATA__')
        if not script_tag: return None
        data = json.loads(script_tag.string)
        all_tickets = data['props']['pageProps']['event']['tickets']
        active_ticket_names = set()
        for ticket in all_tickets:
            is_hidden = ticket.get('styleOptions', {}).get('hiddenInSelectionArea', False)
            is_active = ticket.get('active', False)
            if is_active and not is_hidden:
                active_ticket_names.add(ticket.get('name'))
        print(f"Found {len(active_ticket_names)} active ticket categories.")
        return active_ticket_names
    except Exception as e:
        print(f"Error fetching or parsing HYROX page: {e}")
        return None

def get_previous_active_tickets():
    # This function remains unchanged
    print("Fetching previous state from JSONBin.io...")
    headers = {'X-Master-Key': JSONBIN_API_KEY}
    try:
        res = requests.get(JSONBIN_URL, headers=headers)
        res.raise_for_status()
        return set(res.json().get('record', []))
    except Exception as e:
        print(f"Error reading from JSONBin.io: {e}. Assuming no previous state.")
        return set()

def save_current_tickets(ticket_names):
    # This function remains unchanged
    print("Saving current state to JSONBin.io...")
    headers = {'Content-Type': 'application/json', 'X-Master-Key': JSONBIN_API_KEY}
    try:
        res = requests.put(JSONBIN_URL, headers=headers, data=json.dumps(list(ticket_names)))
        res.raise_for_status()
        print("Successfully updated state in JSONBin.io.")
    except Exception as e:
        print(f"Error writing to JSONBin.io: {e}")

def send_push_notification(new_tickets):
    """Sends a push notification via ntfy.sh."""
    if not NTFY_TOPIC:
        print("NTFY_TOPIC not set. Skipping push notification.")
        return

    print(f"Sending push notification to ntfy topic: {NTFY_TOPIC}...")
    # Format the first new ticket for the title
    first_new_ticket = list(new_tickets)[0]
    
    # Send the request to the public ntfy.sh server
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data="\n".join(f"• {ticket}" for ticket in new_tickets).encode(encoding='utf-8'),
            headers={
                "Title": "New HYROX Tickets Available!",
                "Priority": "high", # Makes it stand out
                "Tags": "tada" # An emoji for the notification
            })
        print("Push notification sent successfully!")
    except Exception as e:
        print(f"Failed to send push notification: {e}")

def send_email_notification(new_tickets):
    # This function remains unchanged
    # (Email code here... for brevity, I've omitted the full function but it's the same as before)
    print("Sending email notification...")
    # ... same email sending logic ...
    print("Email sent!")


def main():
    if not all([JSONBIN_API_KEY, JSONBIN_URL]):
        print("Error: JSONBin.io environment variables are not set. Exiting.")
        return

    current_tickets = get_current_active_tickets()
    if current_tickets is None:
        print("Could not retrieve current tickets. Exiting.")
        return

    previous_tickets = get_previous_active_tickets()
    newly_active_tickets = current_tickets - previous_tickets

    if newly_active_tickets:
        print(f"!!! New tickets found: {newly_active_tickets} !!!")
        # --- TRIGGER BOTH NOTIFICATIONS ---
        send_push_notification(newly_active_tickets)
        # send_email_notification(newly_active_tickets) # You can keep or comment out the email
    else:
        print("No new active tickets found. All is quiet.")
    
    save_current_tickets(current_tickets)

if __name__ == "__main__":
    main()
