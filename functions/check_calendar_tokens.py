# check validity of stored tokens
# if not present, create token file

import logging
import os.path

from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# If modifying these scopes, delete the file token.json.
SCOPES: list[str] = ["https://www.googleapis.com/auth/calendar"]

logger = logging.getLogger(__name__)


def check_calendar_tokens() -> Credentials:
    """Return valid Google Calendar credentials, refreshing or re-authorising as needed."""
    logger.info("Checking tokens...")
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists(path="token.json"):
        creds = Credentials.from_authorized_user_file(filename="token.json", scopes=SCOPES)
        logger.info("Tokens exist")
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        logger.info("No valid tokens available, creating new ones")
        refreshed = False
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Creds refreshed.")
                refreshed = True
            except RefreshError as e:
                logger.error("Failed to refresh non-valid tokens.")
                logger.error(e)
                logger.error("Deleting tokens and trying to restart authorization flow...")
                os.remove("token.json")
        if not refreshed:
            flow = (InstalledAppFlow.from_client_secrets_file(
                client_secrets_file="credentials.json",
                scopes=SCOPES
            ))
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
            logger.info("Tokens created")
    else:
        logger.info("Available tokens are valid")
    logger.info("")
    return creds