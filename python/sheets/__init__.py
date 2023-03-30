from sheets.i18n import I18n
from sheets.switch import Switch
from sheets.settings import Settings
from sheets.registration import Registration
from sheets.log import LogSheet
from sheets.groups import Groups
from sheets.users import Users
from sheets.report import Report
from sheets.keyboard import Keyboard
from sheets.notifications import Notifications

import asyncio
from telegram.ext import Application
from telegram.constants import ParseMode

from log import Log

async def PerfomNotification(app: Application):
    Log.info("Start performing notification")
    for idx,row in Notifications.as_df.loc[Notifications.selector_to_notify()].iterrows():
        await Users.send_notification_to_all_users(
            app.bot, row.text_markdown, ParseMode.MARKDOWN, row.send_picture, row.state
        )
        if row.state == "":
            await Groups.send_to_all_normal_groups(app.bot, row.text_markdown, ParseMode.MARKDOWN, row.send_picture)
        await Groups.send_to_all_admin_groups(
            app.bot, 
            Settings.notification_admin_groups_template.format(message=row.text_markdown),
            ParseMode.MARKDOWN,
            row.send_picture
        )
        await Notifications.set_done(idx)
    Log.info("Done performing notification")
    await asyncio.sleep(Settings.notifications_update_time)
    app.create_task(PerfomNotification(app))