import random
import string

arf = {}

playrandom = 'PLAYRANDOM'
add = 'ADD'
cancel = 'CANCEL'
cancelinvoice = 'CANCELINVOICE'

class TelegramCommand:
    def __init__(self, userid, command, data):
        self.userid = userid
        self.command = command
        self.data = data

def add_command(command: TelegramCommand) -> str:
    key = "".join(random.sample(string.ascii_letters,12))
    arf[key] = command
    return key

def get_command(key: str) -> TelegramCommand:
    if key in arf:
        command = arf[key]
        del arf[key]
        return command
    else:
        return None