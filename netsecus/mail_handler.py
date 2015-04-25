from __future__ import unicode_literals

import imaplib
import logging
import time

from . import helper
from . import rules


def mainloop(config):
    helper.patch_imaplib()

    imapmail = loginIMAP(
        config("mail.imap_server"),
        config("mail.address"),
        config("mail.password"))

    imapmail._command("CAPABILITY")
    if "UTF8" in imapmail.readline().decode("utf-8"):
        imapmail.readline()  # "OK" from "CAPABILITY" command
        imapmail._command("ENABLE", "UTF8")
        imapmail.readline()  # "* ENABLED" from "ENABLE"
        imapmail.readline()  # "OK" from "ENABLE" command
        imapmail._command("ENABLE", "UTF8=ACCEPT")
        imapmail.readline()  # "* ENABLED" from "ENABLE"
        imapmail.readline()  # "OK" from "ENABLE" command
        logging.debug("Server supports UTF8")

    imapmail._command("IDLE")

    if "idling" in imapmail.readline().decode("utf-8"):
        logging.debug("Server supports IDLE.")
        firstRun = True
        while True:
            if firstRun or "EXISTS" in imapmail.readline().decode("utf-8"):
                imapmail._command("DONE")
                imapmail.readline()
                ruleLoop(config, imapmail)
                imapmail._command("IDLE")
                logging.debug("Entering IDLE state.")
            firstRun = False
    else:
        logging.debug("Server lacks support for IDLE... Falling back to delay.")
        while True:
            try:
                ruleLoop(config, imapmail)
                time.sleep(config("mail.delay"))
            except KeyboardInterrupt:
                logoutIMAP(imapmail)
                raise


def ruleLoop(config, imapmail):
    for rule in config("rules"):
        processRule(config, imapmail, rule)


def processRule(config, imapmail, rule):
    logging.debug("**** rule: '%s'" % rule["title"])

    mails = []

    for step in rule["steps"]:
        logging.debug("* exec: %s" % step[0])
        mails = getattr(rules, step[0])(config, imapmail, mails, *step[1:])

        if not mails:
            logging.debug("*  ret no mails")
            break
        logging.debug("*  ret %d mail(s)" % len(mails))
    logging.debug("**** done: '%s'" % rule["title"])


def loginIMAP(server, address, password):
    if not address or not password:
        err = "IMAP login information incomplete. (Missing address or password)"
        logging.error(err)
        raise ValueError(err)
    else:
        imapmail = imaplib.IMAP4_SSL(server)
        imapmail.login(address, password)
        logging.debug("IMAP login (%s on %s)" % (address, server))
    return imapmail


def logoutIMAP(imapmail):
    imapmail.close()
    imapmail.logout()
    logging.debug("IMAP logout")