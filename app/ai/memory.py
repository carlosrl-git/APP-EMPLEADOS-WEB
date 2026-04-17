last_action = {}

def save_last_action(data):
    global last_action
    last_action = data

def get_last_action():
    return last_action
