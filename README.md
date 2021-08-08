# dc29-discord-signalbot
A python discord client interaction emulator for the DC29 badge code channel

## Prep

### Open Developer mode    
Open the developer mode for your browser
* chrome - `CTRL + SHIFT + j`
* Firefox - `CTRL + SHIFT + i`

in Developer tools for that window, click the "NETWORK" tab.

### Login to Discord on the browser
Before you start this script, login to discord.gg in your browser.
Open the web-app version of discord.
Navigate to the DefCon server.

### Find request to 'messages' endpoint in Developer Tools window
In the developer tools NETWORK tab, hit the "DO NOT ENTER" / "Trash Can" icon (depdending on browser) to clear the network history log.

now hard-refresh the discord window (CTRL + SHIFT + R)

In the network tab you're going to see a lot of data. Find one of the URL path entries that looks like `messages?limit=##`

Select the entry, and look at HEADERS on the right. Scroll down to "REQUEST HEADERS".

### Collect TWO headers from request to 'messages' endpoint
You need TWO headers:
* `x-super-properties`
* `authorization`

These will be set as DISCORD_AUTHORIZATION and DISCORD_XSUPER in your environment respectively.

### Set environment variables
set these in your environment you're running the script from:
* Linux - `export DISCORD_AUTHORIZATION=<authorization header data>`
* Windows - `set DISCORD_AUTHORIZATION=<authorization header data>`

        set DISCORD_AUTHORIZATION=abcd1234abcd1234abcd.12345.abcd1234abcd1234
        set DISCORD_XSUPER=eby-some-long.string.of-text
        set DISCORD_USER=yourUserName
        set BADGE_SERIAL_PORT=yourSerialPortCom3Tty

### Note your com/tty port for the USB Serial connection
Grab your COM# or /dev/tty number for your badge (whatever you're using to connect via Putty, etc)
* example: COM2 or /dev/tty2 or /dev/serial0 (etc)

## Usage

Now you're ready to install the required packages.

!!! **NOTICE** !!! - Terms of service with Discord are not _straight forward_. This could potentially cause discord to warn/flag/suspend your account if you abuse the API interfaces.

### Setup

    # from within this directory

    python3 -m venv .
    . bin/activate 
    
    # windows: \Scripts\Activate.bat
    # or powershell -Ex bypass \Scripts\Activate.ps1

    pip install -r requirements.txt

You will need to edit `main.py`.
* Replace DISCORD_USER username with your username
* Replace BADGE_CHANNEL with your com/tty device name
### Run

    # for testing/etc
    python3 main.py --interactive

    # to run live
    python3 main.py