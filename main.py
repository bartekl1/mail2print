from imapclient import IMAPClient
from imapclient.exceptions import LoginError
import yaml
import cups

from tempfile import NamedTemporaryFile
from typing import BinaryIO
import logging
import email
import time
import sys
import re
import os

IDLE_TIMEOUT = 10
IDLE_RENEW_INTERVAL = 60 * 5

def get_config() -> dict:
    with open("config.yaml") as file:
        config = yaml.safe_load(file)
    return config if config is not None else {}

def setup_logging(config: dict):
    log_level_name = config.get("logging", {}).get("level", "info")
    log_file = config.get("logging", {}).get("file", None)
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)

    logger = logging.getLogger()
    logger.setLevel(log_level)

    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    if log_file is not None:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

def print_files(files: list[BinaryIO], config: dict):
    logger = logging.getLogger(__name__)

    printer_name = config.get("printer")
    if printer_name is None:
        logger.error("Printer not specified")
        raise Exception("Printer not specified")

    connection = cups.Connection()
    for file in files:
        file_path = file.name
        filename = os.path.split(file_path)[1]
        job_id = connection.printFile(printer_name, file_path, filename, {})
        logger.info(f"Print job sent successfully. Job ID is {job_id}")
        os.remove(file_path)

def process_new_messages(mail: IMAPClient, config: dict):
    logger = logging.getLogger(__name__)

    ids = mail.search("UNSEEN")
    messages = mail.fetch(ids, ["RFC822"])

    for raw_message in messages.values():
        message = email.message_from_bytes(raw_message[b"RFC822"])

        sender = str(message.get("From"))
        sender_email = re.findall("^.* <(.*@.*)>$", sender)[0]
        # subject = message.get("Subject")

        if sender_email in (config.get("allowed_senders") or []) or config.get("allowed_senders") is None:
            logger.info(f"Processing e-mail from {sender_email}")
        else:
            logger.info(f"Ignoring e-mail from {sender_email}")
            continue

        attachment_files = []

        for part in message.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                content = part.get_payload(decode=True).decode()
            elif "attachment" in str(part.get("Content-Disposition")):
                filename = re.findall('^attachment; filename="(.*)"$', str(part.get("Content-Disposition")))[0]
                mimetype = part.get_content_type()
                if mimetype in (config.get("allowed_mimetypes") or []) or config.get("allowed_mimetypes") is None:
                    logger.info(f"Processing attachment {filename}")
                else:
                    logger.info(f"Ignoring attachment {filename}")
                    continue
                
                file = NamedTemporaryFile(mode="w+b", delete=False)
                file.write(part.get_payload(decode=True))
                file.close()
                attachment_files.append(file)
        
        print_files(attachment_files, config)

def main():
    config = get_config()

    setup_logging(config)
    logger = logging.getLogger(__name__)

    while True:
        try:
            logger.info("Connecting to IMAP server...")
            server = IMAPClient(host=config.get("imap", {}).get("server"),
                                port=config.get("imap", {}).get("port", None),
                                ssl=config.get("imap", {}).get("ssl", True))
            server.login(config.get("imap", {}).get("user"), config.get("imap").get("password"))
            logger.info("Connected")
            server.select_folder("INBOX")

            process_new_messages(server, config)
            server.idle()
            idle_started = time.monotonic()

            while True:
                if time.monotonic() - idle_started > IDLE_RENEW_INTERVAL:
                    logger.debug("Renewing IDLE session...")
                    server.idle_done()
                    server.idle()
                    idle_started = time.monotonic()
                    continue

                responses = server.idle_check(timeout=IDLE_TIMEOUT)
                if responses:
                    logger.debug("Server sent response. Processing new e-mails...")
                    server.idle_done()
                    process_new_messages(server, config)
                    server.idle()
                    idle_started = time.monotonic()
                else:
                    logger.debug("Server sent nothing.")

        except KeyboardInterrupt:
            logger.info("Exiting...")
            try:
                server.idle_done()
                server.logout()
            except Exception:
                pass
            break
        except LoginError:
            logger.critical("Invalid credentials")
            break
        except Exception as e:
            logger.error(f"Unhandled exception: {repr(e)}")
            try:
                server.logout()
            except Exception:
                pass
            time.sleep(10)
            continue

if __name__ == "__main__":
    main()
