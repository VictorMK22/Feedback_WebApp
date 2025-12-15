import vonage
from django.conf import settings

def send_sms(phone_number, message):
    client = vonage.Client(key=settings.VONAGE_API_KEY, secret=settings.VONAGE_API_SECRET)
    sms = vonage.Sms(client)

    response = sms.send_message({
        "from": "VonageAPI",  # Sender ID
        "to": phone_number,
        "text": message,
    })

    if response["messages"][0]["status"] == "0":
        print(f"Message sent successfully to {phone_number}")
        return {"success": True, "response": response}
    else:
        print(f"Message failed with error: {response['messages'][0]['error-text']}")
        return {"success": False, "error": response["messages"][0]["error-text"]}