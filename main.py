import os
import re
import requests
import serial
import time

import logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

#URL for 
dc29SignalChat = 'https://discord.com/api/v9/channels/872838274610262086/messages?limit=50'

#NOTE: REPLACE THIS WITH YOUR USER
DISCORD_USER = "rx13"
BADGE_CHANNEL = "COM3" #/dev/tty# or COM#

# KEEP TRACK OF USERS WE ALREADY HAVE, prevent dupes
PROCESSED_REQ_BUFFER = []
PROCESSED_REPLY_BUFFER = []
LAST_MESSAGE_ID = 0

# load sensitive from environment
discordXSuperProperties = os.environ.get("DISCORD_XSUPER")
discordAuthorization = os.environ.get("DISCORD_AUTHORIZATION")

# assume prefix of syn/req
messageReqRegex = re.compile("(req|syn)[: ]+[0-9a-zA-Z]{32}", re.IGNORECASE)
# assume the initial key is a response to a request
messageReplyRegex = re.compile("^[^a-zA-Z0-9]*[a-zA-Z0-9]{32}[^a-zA-Z0-9]*")
# key extraction regex
keyMatchRegex = re.compile("[a-zA-Z0-9]{32}")

# Req: 
headers = {
        "authority": 'discord.com',
        "sec-ch-ua": '"Chromium";v="92", " Not A;Brand";v="99", "Google Chrome";v="92"',
        "x-super-properties": discordXSuperProperties,
        "authorization": discordAuthorization,
        "accept-language": 'en-US',
        "sec-ch-ua-mobile": '?0',
        "user-agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        "accept": '*/*',
        "sec-fetch-site": 'same-origin',
        "sec-fetch-mode": 'cors',
        "sec-fetch-dest": 'empty',
        "referer": 'https://discord.com/channels/708208267699945503/872838274610262086',
        "dnt": '1',
        "sec-gpc": '1',
    }

def getMessages(sesh):
    res = sesh.get(dc29SignalChat)
    if res.ok:
        return res
    else:
        logger.fatal(res.text)
        raise Exception("Failed to auth, update XSuper and Authorization and try again")


def getLastMessageIndex(responseJson):
    lastMessageIndex = 0
    for i in range(len(responseJson)):
        message = responseJson[i]
        if message["id"] == LAST_MESSAGE_ID:
            lastMessageIndex = i
            break
    return lastMessageIndex


def getReqs(messages):
    lastReqID = 0
    reqs = {}
    for message in messages:
        if messageReqRegex.search(message["content"]):
            match = messageReqRegex.search(message["content"])[0]
            reqKey = keyMatchRegex.search(match)[0]
            user = message["author"]["id"]
            if reqKey != None and user not in PROCESSED_REQ_BUFFER:
                reqs[user] = reqKey
            lastReqID = message["id"]
    return reqs, lastReqID


def getReplies(messages):
    replies = {}
    for message in messages:
        inMentions = False
        mentioned = [mention for mention in message["mentions"] if mention["username"] == DISCORD_USER]
        if mentioned:
            if messageReplyRegex.search(message["content"]):
                replymatch = messageReplyRegex.search(message["content"])[0]
                responseKey = keyMatchRegex.search(replymatch)[0]
                user = message["author"]["id"]
                if responseKey != None and user not in PROCESSED_REPLY_BUFFER:
                    replies[user] = responseKey
    return replies

if __name__ == "__main__":
    sesh = requests.Session()
    sesh.headers = headers

    badge = serial.Serial(BADGE_CHANNEL)

    logger.info(sesh.headers)

    while True:
        res = getMessages(sesh)
        responseJson = res.json()

        LAST_MESSAGE_ID = getLastMessageIndex(responseJson)
        requests, lastReqID = getReqs(responseJson[LAST_MESSAGE_ID:])
        replies = getReplies(responseJson[LAST_MESSAGE_ID:])

        if lastReqID != LAST_MESSAGE_ID:
            LAST_MESSAGE_ID = lastReqID
        
        
        for user,reqKey in requests.items():
            PROCESSED_REQ_BUFFER.append(user)

        time.sleep(15)
