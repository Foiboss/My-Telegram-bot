from datetime import timedelta

TOKEN = "enter here your token"
WHITELIST_FILE = "whitelist.json"
DB_PATH = "bot.db"

# antispam config
should_be_antispam_protected = True
message_cooldown = timedelta(seconds = 1)
export_cooldown = timedelta(seconds = 30)
clear_dict_cooldown = timedelta(minutes = 10)