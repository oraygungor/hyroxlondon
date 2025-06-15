import requests
import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from bs4 import BeautifulSoup

# --- Configuration ---
URL = "https://gb.hyrox.com/checkout/hyrox-london-excel-season-25-26-rzstou"
STATE_FILE = "last_active_tickets.json"

# --- Securely load email credentials from Environment Variables ---
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD') # Use an "App Password" for Gmail
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL')


def get_current_active_tickets():
    """Fetches the current list of active ticket names from the URL."""
    print("Fetching current ticket status from HYROX page...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(URL, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        script_tag = soup.find('script', id='__NEXT_DATA__')
        if not script_tag:
            return None # Indicate an error

        data = json.loads(script_tag.string)
        all_tickets = data['props']['pageProps']['event']['tickets']

        active_ticket_names = set()
        for ticket in all_tickets:
            # Filter out hidden "helper" tickets and only consider active ones
            is_hidden = ticket.get('styleOptions', {}).get('hiddenInSelectionArea', False)
            is_active = ticket.get('active', False)
            if is_active and not is_hidden:
                active_ticket_names.add(ticket.get('name'))
        
        print(f"Found {len(active_ticket_names)} active ticket categories.")
        return active_ticket_names

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return None
    except (KeyError, TypeError):
        print("Error parsing page data. The website structure may have changed.")
        return None

def get_previous_active_tickets():
    """Reads the set of active tickets from the last successful run."""
    try:
        with open(STATE_FILE, 'r') as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        # If the file doesn't exist or is empty, return an empty set
        return set()

def save_current_tickets(ticket_names):
    """Saves the current set of active tickets to the state file."""
    with open(STATE_FILE, 'w') as f:
        json.dump(list(ticket_names), f, indent=2)
    print(f"Updated state file '{STATE_FILE}' with current active tickets.")

def send_notification_email(new_tickets):
    """Sends an email notification about newly available tickets."""
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL]):
        print("Email credentials not set in environment variables. Cannot send email.")
        return

    subject = "New HYROX Tickets Available!"
    body_list = [
        "A new HYROX race category has become active!",
        "\nNewly Detected Tickets:",
        "-----------------------"
    ]
    body_list.extend(f"- {ticket}" for ticket in new_tickets)
    body_list.append(f"\nCheck the site now: {URL}")
    body = "\n".join(body_list)

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL

    print(f"Sending email notification to {RECIPIENT_EMAIL}...")
    try:
        # Using SSL for a secure connection to the SMTP server
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    """Main function to run the monitoring logic."""
    current_tickets = get_current_active_tickets()
    if current_tickets is None:
        print("Could not retrieve current tickets. Exiting.")
        return

    previous_tickets = get_previous_active_tickets()
    
    # Use set difference to find what's new
    newly_active_tickets = current_tickets - previous_tickets

    if newly_active_tickets:
        print(f"!!! New tickets found: {newly_active_tickets} !!!")
        send_notification_email(newly_active_tickets)
    else:
        print("No new active tickets found. All is quiet.")
    
    # Always update the state file with the latest list for the next run
    save_current_tickets(current_tickets)

if __name__ == "__main__":
    main()
