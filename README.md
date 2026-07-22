# mail2print

Python script to automatically print files sent by an email.

## About

Script receives emails using IMAP IDLE protocol and sends the attachments to a printer using CUPS.

## Requirements

- Linux system with CUPS installed and configured
- Printer added to CUPS
- Email account with IMAP access enabled
- Python (3.11 or higher, older versions may work but are not tested)
- Systemd (for running the script as a service)
- Git (optional, for cloning the repository)

## Installation

1. Clone the repository.

```bash
git clone https://github.com/bartekl1/mail2print.git
cd mail2print
```

2. Create Python virtual environment.

```bash
python3 -m venv .venv
```

3. Install dependencies.

```bash
.venv/bin/pip install -r requirements.txt
```

> [!TIP]
> It may be required to install `libcups2-dev` package before installing dependencies, otherwise `pycups` may fail to install. \
> On Debian based distributions, you can install it with: `sudo apt install libcups2-dev`.

4. Copy the example configuration file and edit it.

```bash
cp config.example.yaml config.yaml
nano config.yaml
```

> [!NOTE]
> View the comments in [the configuration file](config.example.yaml) for more information about available options.

5. Create a systemd service file to run the script as a service.

```bash
sudo cp mail2print.service /etc/systemd/system/mail2print.service
```

> [!NOTE]
> You need to change `<PATH_TO_DIRECTORY>` and `<USERNAME>` in the service file to match your setup.

6. Reload systemd and enable the service.

```bash
sudo systemctl daemon-reload
sudo systemctl enable mail2print.service
sudo systemctl start mail2print.service
```
