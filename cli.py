#!/usr/bin/env python3
# cli.py — Local testing. Usage: python cli.py [slack_user_id] [message...]
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from research_digest.session import run_session
from research_digest.state import GDriveStateStore


def main():
    user_id = sys.argv[1] if len(sys.argv) > 1 else "cli_user"
    message  = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Run the research digest."

    store = GDriveStateStore(
        credentials_path=os.environ["GDRIVE_CREDENTIALS_PATH"],
        root_folder_id=os.environ["GDRIVE_ROOT_FOLDER_ID"],
    )

    print("Starting digest for user={}".format(user_id))
    run_session(user_id=user_id, message=message, store=store)


if __name__ == "__main__":
    main()
