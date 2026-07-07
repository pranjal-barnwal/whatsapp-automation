"""WhatsApp automation package (``src``) for sending personalized client messages.

Package layout:
  * ``config``      - tweakable settings (paths, country code, delays)
  * ``clients/``    - reading the recipient list (models, phone cleaning, Excel loader)
  * ``messaging/``  - rendering the message template and building WhatsApp links
  * ``sending/``    - Selenium WhatsApp Web automation (selectors + sender)
  * ``reporting/``  - per-run CSV report and resume lookup
  * ``cli``         - command-line interface and run orchestration
"""
