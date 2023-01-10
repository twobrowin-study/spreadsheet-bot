from os import environ
import json

BotToken = environ.get('BOT_TOKEN')
if BotToken == '' or BotToken == None:
    with open('telegram.txt', 'r') as fp:
        BotToken = fp.read()

SheetsSecret = environ.get('SHEETS_ACC_JSON')
if SheetsSecret == '' or SheetsSecret == None:
    with open('./serviceacc.json', 'r') as fp:
        SheetsSecret = json.load(fp)
else:
    SheetsSecret = json.loads(SheetsSecret)

SheetsLink = environ.get('SHEETS_LINK')
SwitchUpdateTime = int(environ.get('SWITCH_UPDATE_TIME'))
SettingsUpdateTime = int(environ.get('SETTINGS_UPDATE_TIME'))