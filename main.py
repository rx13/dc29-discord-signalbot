import copy
import os
import random
import re
import requests
import serial
import sys
import time

import logging
logging.basicConfig(
    format="%(asctime)-15s %(levelname)-8s : %(message)s",
    level=logging.WARNING
)
logger = logging.getLogger()


############
#
#   CONFIGURABLES
#

#URL for 
dc29SignalChat = 'https://discord.com/api/v9/channels/872838274610262086/messages'
dc29SignalChatReq = f"{dc29SignalChat}?limit=50"
dc29SignalChatReact = "{dc29SignalChat}/{messageID}/reactions/%F0%9F%91%8D/%40me"

#NOTE: REPLACE THIS WITH YOUR USER
DISCORD_USER = os.environ.get("DISCORD_USER") # your username
BADGE_CHANNEL = os.environ.get("BADGE_SERIAL_PORT") #/dev/tty# or COM#

if not DISCORD_USER or not BADGE_CHANNEL:
    raise("Env variables for DISCORD_USER or BADGE_SERIAL_PORT should be set")

########### 
#
#   MAIN
#

# KEEP TRACK OF USERS WE ALREADY HAVE, prevent dupes
PROCESSED_REQ_BUFFER = []
PROCESSED_REPLY_BUFFER = []

if os.path.exists("requests.txt"):
    with open("requests.txt", "r") as f:
        for line in f:
            PROCESSED_REQ_BUFFER.append(line.strip())

if os.path.exists("replies.txt"):
    with open("replies.txt", "r") as f:
        for line in f:
            PROCESSED_REPLY_BUFFER.append(line.strip())

LAST_MESSAGE_ID = 0
BADGE_REQ_TOKEN = None

# load sensitive from environment
discordXSuperProperties = os.environ.get("DISCORD_XSUPER")
discordAuthorization = os.environ.get("DISCORD_AUTHORIZATION")

if not discordXSuperProperties or not discordAuthorization:
    raise Exception("Must include environment variables with client auth")

# assume prefix of syn/req
messageReqRegex = re.compile("((req|syn|signal)[-.!: ]*[0-9a-zA-Z]{32}|^.*[^res]*[-: ]*[0-9a-zA-Z]{32}.*$)", re.IGNORECASE)
# assume the initial key is a response to a request
messageReplyRegex = re.compile("^((resp|res)[-: ]*)?[^a-zA-Z0-9]*[a-zA-Z0-9]{32}[^a-zA-Z0-9]*", re.IGNORECASE)
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

jsonReqReply = {
    "content":":thumbsup:",
    "nonce":"<OVERWRITE>",
    "tts": False,
    "message_reference":{
        "guild_id":"708208267699945503",
        "channel_id":"872838274610262086",
        "message_id":"<OVERWRITE>"
        }
    }

def getMessages(sesh):
    res = sesh.get(dc29SignalChatReq)
    if res.ok:
        return res
    else:
        logger.fatal(res.text)
        raise Exception("Failed to auth, update XSuper and Authorization and try again")


def sendMessage(sesh, payload):
    res = sesh.post(dc29SignalChat, json=payload)
    if res.ok:
        return True
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
        if message["author"]["username"] == DISCORD_USER:
            continue
        if messageReqRegex.search(message["content"]):
            if "mentions" in message and len([mention for mention in message["mentions"] if mention["username"] != DISCORD_USER]) > 0:
                continue
            match = messageReqRegex.search(message["content"])[0]
            reqKey = keyMatchRegex.search(match)[0]
            user = message["author"]["username"]
            user = user.encode('unicode-escape').decode('utf-8', "ignore")
            if reqKey != None and user not in PROCESSED_REQ_BUFFER:
                reqs[user] = {
                    "token": reqKey,
                    "messageId": message["id"]
                }
            lastReqID = message["id"]
    return reqs, lastReqID


def getReplies(messages):
    replies = {}
    for message in messages:
        if message["author"]["username"] == DISCORD_USER:
            continue
        inMentions = False
        # we assume any reply with us as a mention is a REQ REPLY
        mentioned = [mention for mention in message["mentions"] if mention["username"] == DISCORD_USER]
        if mentioned:
            if messageReplyRegex.search(message["content"]):
                replymatch = messageReplyRegex.search(message["content"])[0]
                responseKey = keyMatchRegex.search(replymatch)[0]
                user = message["author"]["username"]
                user = user.encode('unicode-escape').decode('utf-8', "ignore")
                if responseKey != None and user not in PROCESSED_REPLY_BUFFER:
                    replies[user] = {
                        "token": responseKey,
                        "messageId": message["id"]
                    }
    return replies

def getBadgeOutput(lastcmd=b""):
    output = b""
    line = badge.read_all()
    output += line
    time.sleep(0.25)
    while not line.endswith(b"\x00") or badge.out_waiting > 0:
        line = badge.read_all()
        output += line
        if line == b"":
            if lastcmd.strip() == b"":
                break
    return output.decode('utf-8')

def sendBadgeCommand(cmd):
    if not isinstance(cmd, bytes):
        cmd = cmd.encode('utf-8')
    badge.write(cmd)
    badge.flush()
    return getBadgeOutput(cmd)

def badgeGetRequestToken():
    response = sendBadgeCommand("4")
    reqKey = keyMatchRegex.search(response)
    while not reqKey:
        logger.warning(f"failed to grab reqKey from '{response}', trying again")
        time.sleep(.25)
        reqKey = badgeGetRequestToken()
    return reqKey[0]

def badgeSubmitToken(token):
    response = sendBadgeCommand("5")
    response += sendBadgeCommand(token + "\r\n")
    response += sendBadgeCommand("\r\n")
    resKey = keyMatchRegex.search(response.replace(token, ""))
    if not resKey and not "Invalid Input" in response and not "not for your badge" in response:
        logger.warning(f"Successfully processed {token}")
    elif not resKey and ("Badge successfully connected" in response or "Already connected to this badge" in response):
        logger.warning(f"Successfully processed {token}")
    elif resKey:
        logger.warning(f"Generated reply key: {resKey[0]}")
    else:
        if "not for your badge" in response:
            logger.info("Not a request token")
            return None
        logger.error(f"Request failed for token: {token} -- {response}")
    return resKey

def generateReqResponse(messageId):
    response = copy.deepcopy(jsonReqReply)
    response["nonce"] = random.randint(100000000000000000,999999999999999999)
    response["message_reference"]["message_id"] = messageId
    return response

if __name__ == "__main__":
    sesh = requests.Session()
    sesh.headers = headers

    requestFile = open("requests.txt", "a+")
    replyFile = open("replies.txt", "a+")

    badge = serial.Serial(BADGE_CHANNEL)
    getBadgeOutput()
    sendBadgeCommand("n\r\n") # send 'N' just in case someone is on reset screen

    BADGE_REQ_TOKEN = badgeGetRequestToken()
    logger.warning(f"Using badge REQ TOKEN: {BADGE_REQ_TOKEN}")

    if "--interactive" in sys.argv:
        try:
            while True:
                cmd = input("cmd: ")
                if cmd == "5":
                    cmd = input("Enter reply/request token: ")
                    print(badgeSubmitToken(cmd))
                else:
                    print(sendBadgeCommand(cmd))
        except KeyboardInterrupt:
            badge.close()
    else:
        try:
            iters = 0
            while True:
                iters += 1
                if iters > 60:
                    iters = 0
                    postOpenReq = generateReqResponse(0)
                    del(postOpenReq["message_reference"])
                    postOpenReq["content"] = f"req: {BADGE_REQ_TOKEN}"
                    sendMessage(sesh, postOpenReq)
                    time.sleep(1)

                logger.info("Checking for new requests/replies...")
                res = getMessages(sesh)
                responseJson = res.json()

                LAST_MESSAGE_ID = getLastMessageIndex(responseJson)
                requests, lastReqID = getReqs(responseJson[LAST_MESSAGE_ID:])
                replies = getReplies(responseJson[LAST_MESSAGE_ID:])

                if lastReqID != LAST_MESSAGE_ID:
                    LAST_MESSAGE_ID = lastReqID        
                
                for user,req in requests.items():
                    logger.info(f"Processing SIGNAL REQ from {user}")
                    replyToken = badgeSubmitToken(req["token"])
                    if not replyToken:    
                        continue
                    discordResponse = generateReqResponse(req["messageId"])
                    discordResponse["content"] = f"res: {replyToken[0]} \r\nREQ: {BADGE_REQ_TOKEN}"
                    sendMessage(sesh, discordResponse)
                    time.sleep(3)
                    PROCESSED_REQ_BUFFER.append(user)
                    requestFile.write(user + "\n")

                for user,reply in replies.items():
                    logger.info(f"Processing SIGNAL REPLY from {user}")
                    replyToken = badgeSubmitToken(reply["token"])
                    discordResponse = generateReqResponse(reply["messageId"])
                    sesh.put(dc29SignalChatReact.format(dc29SignalChat=dc29SignalChat, messageID=reply["messageId"]))
                    time.sleep(3)
                    PROCESSED_REQ_BUFFER.append(user)
                    replyFile.write(user + "\n")

                time.sleep(random.randint(35,57))
        except KeyboardInterrupt:
            requestFile.close()
            replyFile.close()