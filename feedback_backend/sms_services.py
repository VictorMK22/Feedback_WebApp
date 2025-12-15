import vonage
import logging
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

class VonageSMSService:
    def __init__(self):
        if not all([
            settings.VONAGE_API_KEY,
            settings.VONAGE_API_SECRET,
            settings.VONAGE_SENDER_ID
        ]):
            raise ValueError("Vonage credentials not properly configured")
        
        self.client = vonage.Client(
            key=settings.VONAGE_API_KEY,
            secret=settings.VONAGE_API_SECRET
        )
        self.sms = vonage.Sms(self.client)
    
    def send_sms(self, phone_number: str, message: str) -> bool:
        """Sends SMS with rate limiting and validation"""
        try:
            # Validate phone number format
            if not self._validate_phone(phone_number):
                raise ValidationError("Invalid phone number format")
            
            # Check rate limit
            if self._is_rate_limited(phone_number):
                logger.warning(f"Rate limit exceeded for {phone_number}")
                return False
            
            # Send message
            response = self.sms.send_message({
                'from': settings.VONAGE_SENDER_ID,
                'to': phone_number,
                'text': message[:1600]  # Truncate to 1600 chars
            })
            
            # Handle response
            if response['messages'][0]['status'] == '0':
                logger.info(f"SMS sent to {phone_number}")
                cache.set(f"sms_sent:{phone_number}", True, timeout=300)  # 5 min rate limit
                return True
            
            error = response['messages'][0]['error-text']
            logger.error(f"Vonage SMS failed: {error}")
            return False
            
        except Exception as e:
            logger.error(f"SMS sending error: {str(e)}")
            return False
    
    def _validate_phone(self, phone_number: str) -> bool:
        """Validates international phone number format"""
        import re
        return bool(re.match(r'^\+[1-9]\d{9,14}$', phone_number))
    
    def _is_rate_limited(self, phone_number: str) -> bool:
        """Checks if phone number is rate limited"""
        return bool(cache.get(f"sms_rate_limit:{phone_number}"))