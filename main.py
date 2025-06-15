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

# --- JSONBin.io Configuration (from Environment Variables) ---
JSONBIN_API_KEY = os.environ.get('JSONBIN_API_KEY')
JSONBIN_URL = os.environ.get('JSONBIN_URL') # e.g., "https://api.jsonbin.io/v3/b/YOUR_BIN_ID"


def get_current_active_tickets():
    """Fetches the current list of active ticket names from the URL."""
    print("Fetching current ticket status from HYROX page...")
    try:
        response = requests.get(HYROX_URL)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        script_tag = soup.find('script', id='__NEXT_DATA__')
        if not script_tag:
            return None

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
    """Reads the set of active tickets from the JSONBin.io cloud."""
    print("Fetching previous state from JSONBin.io...")
    headers = {
        'X-Master-Key': JSONBIN_API_KEY
    }
    try:
        res = requests.get(JSONBIN_URL, headers=headers)
        res.raise_for_status()
        # The actual record is nested under 'record'
        return set(res.json().get('record', []))
    except Exception as e:
        print(f"Error reading from JSONBin.io: {e}. Assuming no previous state.")
        return set()

def save_current_tickets(ticket_names):
    """Saves the current set of active tickets to the JSONBin.io cloud."""
    print("Saving current state to JSONBin.io...")
    headers = {
      'Content-Type': 'application/json',
      'X-Master-Key': JSONBIN_API_KEY
    }
    try:
        # We must convert the set to a list to be JSON serializable
        res = requests.put(JSONBIN_URL, headers=headers, data=json.dumps(list(ticket_names)))
        res.raise_for_status()
        print("Successfully updated state in JSONBin.io.")
    except Exception as e:
        print(f"Error writing to JSONBin.io: {e}")

def send_notification_email(new_tickets):
    """Sends an email notification about newly available tickets."""
    # (This function remains unchanged)
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL]):
        print("Email credentials not set. Cannot send email.")
        return
    subject = "New HYROX Tickets Available!"
    body = "\n".join([
        "A new HYROX race category has become active!",
        "\nNewly Detected Tickets:", "-----------------------"
    ] + [f"- {ticket}" for ticket in new_tickets] + [f"\nCheck the site now: {HYROX_URL}"])
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    print(f"Sending email notification to {RECIPIENT_EMAIL}...")
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

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
        send_notification_email(newly_active_tickets)
    else:
        print("No new active tickets found. All is quiet.")
    
    save_current_tickets(current_tickets)

if __name__ == "__main__":
    main()
