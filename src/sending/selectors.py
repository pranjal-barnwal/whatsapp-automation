"""XPath selectors for the WhatsApp Web UI.

WhatsApp occasionally changes its web client's HTML. When sends start failing
because an element can't be found, this is the one small place to update.
"""

# The blue "Send" button next to the message box.
SEND_BUTTON = "//button[@aria-label='Send' or @data-testid='send']"

# The editable message input box.
MESSAGE_BOX = (
    "//div[@contenteditable='true'][@data-tab='10' or @aria-label][@role='textbox']"
)

# Dialog shown when a phone number is invalid / not on WhatsApp.
INVALID_DIALOG = (
    "//*[contains(text(), 'Phone number shared via url is invalid') or "
    "contains(text(), 'phone number shared via url is invalid') or "
    "contains(text(), \"isn't on WhatsApp\") or "
    "contains(text(), 'is not on WhatsApp')]"
)

# The "OK" button that dismisses the invalid-number dialog.
INVALID_OK_BUTTON = "//div[@role='button']//div[text()='OK'] | //button[text()='OK']"

# QR code canvas shown on the login screen.
QR_CANVAS = "//canvas[@aria-label='Scan me!' or @role='img']"

# Any element that only appears once a chat is open and ready.
CHAT_READY = "//footer//div[@contenteditable='true']"

# The little "pending" clock icon shown before a message leaves the device.
PENDING_CLOCK = "//span[@data-icon='msg-time']"

# Elements that only exist once the user is logged in (chat/search pane).
LOGGED_IN = [
    "//div[@id='side']",
    "//div[@contenteditable='true'][@data-tab='3']",
]
