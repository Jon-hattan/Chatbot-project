"""
Instagram message sender for Instagram Messaging API.

Handles sending messages via Instagram Graph API (Meta).
"""

import requests
from typing import Dict, Any, Optional, List


class InstagramSender:
    """
    Handles sending messages via Instagram Graph API.

    Supports:
    - Text messages
    - Images (via URL)
    - Quick replies
    - Generic templates
    """

    GRAPH_API_VERSION = "v21.0"
    BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    def __init__(self, page_id: str, access_token: str):
        """
        Initialize Instagram sender.

        Args:
            page_id: Instagram Page ID
            access_token: Page Access Token (long-lived recommended)
        """
        self.page_id = page_id
        self.access_token = access_token
        self.messages_url = f"{self.BASE_URL}/{page_id}/messages"

    def send_text_message(self, recipient_id: str, text: str) -> bool:
        """
        Send a text message to a user.

        Args:
            recipient_id: IGSID (Instagram Scoped ID) of recipient
            text: Message text (max 1000 characters)

        Returns:
            True if successful, False otherwise
        """
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text},
            "access_token": self.access_token
        }

        try:
            response = requests.post(self.messages_url, json=payload, timeout=10)
            response.raise_for_status()

            message_id = response.json().get("message_id")
            print(f"✅ Text message sent to {recipient_id} (ID: {message_id})")
            return True

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to send text message to {recipient_id}: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"   Response: {e.response.text}")
            return False

    def send_image(self, recipient_id: str, image_url: str, caption: str = "") -> bool:
        """
        Send an image to a user via URL.

        Args:
            recipient_id: IGSID of recipient
            image_url: Publicly accessible URL of image
            caption: Optional caption text

        Returns:
            True if successful, False otherwise

        Note:
            Instagram doesn't support direct file uploads in messages.
            Image must be hosted at a publicly accessible HTTPS URL.
        """
        payload = {
            "recipient": {"id": recipient_id},
            "message": {
                "attachment": {
                    "type": "image",
                    "payload": {
                        "url": image_url,
                        "is_reusable": True
                    }
                }
            },
            "access_token": self.access_token
        }

        # Add caption if provided (sent as separate text message after image)
        # Note: Instagram API doesn't support captions in image attachments
        # We send caption as a separate message

        try:
            response = requests.post(self.messages_url, json=payload, timeout=10)
            response.raise_for_status()

            message_id = response.json().get("message_id")
            print(f"✅ Image sent to {recipient_id} (ID: {message_id})")

            # Send caption as separate message if provided
            if caption:
                self.send_text_message(recipient_id, caption)

            return True

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to send image to {recipient_id}: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"   Response: {e.response.text}")
            return False

    def send_quick_replies(
        self,
        recipient_id: str,
        text: str,
        quick_replies: List[Dict[str, str]]
    ) -> bool:
        """
        Send a message with quick reply buttons.

        Args:
            recipient_id: IGSID of recipient
            text: Message text
            quick_replies: List of quick reply options (max 13)
                Format: [{"title": "Option 1", "payload": "PAYLOAD_1"}, ...]

        Returns:
            True if successful, False otherwise

        Example:
            send_quick_replies(
                "123456789",
                "Choose a class type:",
                [
                    {"title": "Kids Class", "payload": "KIDS"},
                    {"title": "Teens Class", "payload": "TEENS"}
                ]
            )
        """
        formatted_replies = [
            {
                "content_type": "text",
                "title": reply["title"][:20],  # Max 20 characters
                "payload": reply.get("payload", reply["title"])[:1000]  # Max 1000
            }
            for reply in quick_replies[:13]  # Max 13 quick replies
        ]

        payload = {
            "recipient": {"id": recipient_id},
            "message": {
                "text": text,
                "quick_replies": formatted_replies
            },
            "access_token": self.access_token
        }

        try:
            response = requests.post(self.messages_url, json=payload, timeout=10)
            response.raise_for_status()

            message_id = response.json().get("message_id")
            print(f"✅ Quick replies sent to {recipient_id} (ID: {message_id})")
            return True

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to send quick replies to {recipient_id}: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"   Response: {e.response.text}")
            return False

    def send_template(
        self,
        recipient_id: str,
        template_type: str,
        elements: List[Dict[str, Any]]
    ) -> bool:
        """
        Send a template message (e.g., generic template with cards).

        Args:
            recipient_id: IGSID of recipient
            template_type: Type of template (e.g., "generic", "button")
            elements: List of template elements (cards)

        Returns:
            True if successful, False otherwise

        Example:
            send_template(
                "123456789",
                "generic",
                [
                    {
                        "title": "Kids Beatbox Class",
                        "image_url": "https://example.com/kids.jpg",
                        "subtitle": "Ages 4-12 | $40/class",
                        "buttons": [
                            {"type": "postback", "title": "Book Now", "payload": "BOOK_KIDS"}
                        ]
                    }
                ]
            )
        """
        payload = {
            "recipient": {"id": recipient_id},
            "message": {
                "attachment": {
                    "type": "template",
                    "payload": {
                        "template_type": template_type,
                        "elements": elements
                    }
                }
            },
            "access_token": self.access_token
        }

        try:
            response = requests.post(self.messages_url, json=payload, timeout=10)
            response.raise_for_status()

            message_id = response.json().get("message_id")
            print(f"✅ Template sent to {recipient_id} (ID: {message_id})")
            return True

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to send template to {recipient_id}: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"   Response: {e.response.text}")
            return False

    def get_user_info(self, igsid: str) -> Dict[str, Any]:
        """
        Get user profile information.

        Args:
            igsid: Instagram Scoped ID

        Returns:
            User info dict with name, username, profile_pic
            Defaults to basic info if API call fails
        """
        url = f"{self.BASE_URL}/{igsid}"

        params = {
            "fields": "name,username,profile_pic",
            "access_token": self.access_token
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get user info for {igsid}: {e}")
            # Return default info if API call fails
            return {
                "name": "User",
                "username": f"ig_{igsid[:8]}",
                "id": igsid
            }

    async def send_photo(self, recipient_id: str, photo_path: str, caption: str = ""):
        """
        Send a photo file to user.

        Args:
            recipient_id: IGSID of recipient
            photo_path: Local path to photo file
            caption: Optional caption text

        Note:
            Instagram API requires images to be hosted at a publicly accessible URL.
            This method is a placeholder - you need to:
            1. Upload the file to a hosting service (S3, ImgBB, etc.)
            2. Get the public HTTPS URL
            3. Use send_image() with that URL

        For now, we just send a text message as fallback.
        """
        print(f"⚠️ Instagram requires images to be hosted at public URLs")
        print(f"   Sending caption as text message instead")

        # Send caption as text message
        if caption:
            await self.send_text_message(recipient_id, caption)
        else:
            await self.send_text_message(
                recipient_id,
                "🎉 Thank you for booking! Our team will contact you for confirmation."
            )
