__author__ = 'Daniel'
import Bot
import random


def random_line(afile):
    line = next(afile)
    for num, aline in enumerate(afile):
        if random.randrange(num + 2):
            continue
        line = aline
    return line


def add(q):
    with open("quotes", mode="a+") as f:
        f.write(q+"\n")


class Quoter(object):
    def __init__(self, ts3conn):
        self.ts3conn = ts3conn
        self.dont_send = []
        for g in ts3conn.servergrouplist():
            if g.get('name', '') in ["Guest", "Admin Server Query"]:
                self.dont_send.append(int(g.get('sgid', 0)))

    def inform(self, evt):
        for g in evt.client_servergroups.split(','):
            if len(g) == 0 or int(g) in self.dont_send:
                return
        with open("quotes") as f:
            quote = ""
            while len(quote) == 0:
                quote = random_line(f)
            Bot.send_msg_to_client(self.ts3conn, evt.client_id, quote)
