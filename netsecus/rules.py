from __future__ import unicode_literals

import hashlib
import logging
import email
import base64
import os
import re
import time

from . import helper


class Mail(object):

    def __init__(self, uid, var, text):
        self.uid = uid
        self.variables = var
        self.text = text
        self.variables["MAILFROM"] = re.findall(r"\<(.*)\>", text["From"])[0]
        self.variables["MAILDATE"] = text["Date"]
        self.variables["MAILRECEIVED"] = text["Received"]


def filter(imapmail, mails, filterCriteria, mailbox="inbox"):
    # see http://tools.ietf.org/html/rfc3501#section-6.4.4 (for search)
    # and http://tools.ietf.org/html/rfc3501#section-6.4.5 (for fetch)
    imapmail.select(mailbox)

    response = helper.imapCommand(imapmail, "search", filterCriteria)
    mails = []

    if response:
        response = response.decode("utf-8").split(" ")
        for uid in response:
            mailInfo, mailText = helper.imapCommand(imapmail, "fetch", uid, "(rfc822)")
            data = email.message_from_string(mailText.decode("utf-8"))
            mails.append(Mail(uid, helper.getConfigValue("variables"), data))
    return mails


def answer(imapmail, mails, subject, text, address="(back)"):
    # see http://tools.ietf.org/html/rfc3501#section-6.4.6 (for store)
    for mail in mails:
        stringToHash = "%s: %s" % (subject, text)
        hashObject = hashlib.sha256()
        hashObject.update(stringToHash.encode("utf-8"))
        subjectHash = hashObject.hexdigest()

        if address == "(back)":
            clientMailAddress = mail.variables["MAILFROM"]
        else:
            clientMailAddress = address

        mail_flags = helper.imapCommand(imapmail, "fetch", mail.uid, "FLAGS")
        if "NETSEC-Answered-" + subjectHash in mail_flags.decode("utf-8"):
            logging.error(
                "Error: Tried to answer to mail (uid %s, addr '%s', Subject '%s') which was already answered." % (
                    mail.uid, clientMailAddress, subject))
        else:
            helper.smtpMail(clientMailAddress, "Content-Type:text/html\nSubject: %s\n\n%s" %
                            (helper.processVariable(mail, subject), helper.processVariable(mail, text)))
            flag(imapmail, [mail], "NETSEC-Answered-" + subjectHash)
    return mails


def move(imapmail, mails, destination):
    # moves the mails from id_list to mailbox destination
    # warning: this alters the UID of the mails!
    imapmail.create(destination)
    for mail in mails:
        # https://tools.ietf.org/html/rfc6851
        helper.imapCommand(imapmail, "MOVE", mail.uid, destination)
    return mails


def flag(imapmail, mails, flag):
    for mail in mails:
        helper.imapCommand(imapmail, "STORE", mail.uid, "+FLAGS", flag)
    return mails


def log(imapmail, mails, msg, lvl="ERROR"):
    if lvl == "DEBUG":
        logging.debug(msg)
    else:
        logging.error(msg)
    return mails


def delete(imapmail, mails):
    flag(imapmail, mails, "\\DELETED")
    imapmail.expunge()


def save(imapmail, mails):
    for mail in mails:
        clientMailAddress = re.findall(r"(.*)\@.*", mail.variables["MAILFROM"])[0].lower()
        attachPath = os.path.join(helper.getConfigValue("settings", "attachment_path"),
                                  helper.escapePath(clientMailAddress))
        timestamp = str(int(time.time()))
        os.mkdirs(attachPath)

        for payloadPart in mail.text.walk():
            if payloadPart.get_filename():
                attachFile = open(os.path.join(attachPath, timestamp + " " +
                                               helper.escapePath(payloadPart.get_filename()), "w"))
            elif payloadPart.get_payload():
                attachFile = open(os.path.join(attachPath, "mailtext.txt"), "a")
            else:
                pass

            dataToWrite = str(payloadPart.get_payload(decode="True"))

            if dataToWrite:
                attachFile.write(dataToWrite)
            attachFile.close()
    return mails
