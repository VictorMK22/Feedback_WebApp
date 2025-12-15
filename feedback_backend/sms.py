import vonage
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class VonageSMS:
    def __init__(self):
        self.client = vonage.Client(
            key=settings.VONAGE_API_KEY,
            secret=settings.VONAGE_API_SECRET
        )
        self.sms = vonage.Sms(self.client)
    
    def send_sms(self, phone_number, message):
        try:
            response = self.sms.send_message({
                'from': settings.VONAGE_SENDER_ID,
                'to': phone_number,
                'text': message
            })
            
            if response['messages'][0]['status'] == '0':
                logger.info(f"SMS sent to {phone_number}")
                return True
            else:
                error = response['messages'][0]['error-text']
                logger.error(f"Vonage SMS failed: {error}")
                return False
                
        except Exception as e:
            logger.error(f"Vonage API error: {str(e)}")
            return False