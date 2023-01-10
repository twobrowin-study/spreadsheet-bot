import traceback
import html
import json

from telegram import Update, Chat
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from log import Log
from sheets import (
    LogSheet,
    Groups,
    Users
)

from errors import BotShouldBeInactive

async def ErrorHandlerFun(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if type(context.error) == BotShouldBeInactive:
        Log.error(msg="Exception Bot should be inactive", exc_info=context.error)
        exit(1)

    Log.error(msg="Exception while handling an update:", exc_info=context.error)

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f"An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    await Groups.send_to_all_superadmin_groups(context.bot, message, ParseMode.HTML)

async def ChatMemberHandlerFun(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    Log.debug(f"Chat member event \n{update.my_chat_member}\n")
    if update.effective_chat.type in [Chat.GROUP, Chat.SUPERGROUP, Chat.CHANNEL]:
        Log.info((
            f"{update.my_chat_member.new_chat_member['status'].title()} event in "
            f"{update.effective_chat.type} with title {update.effective_chat.title} id {update.effective_chat.id}"
        ))
        
        await LogSheet.write(update.effective_chat.id,(
            f"{update.my_chat_member.new_chat_member['status'].title()} {update.effective_chat.type} "
            f"with title {update.effective_chat.title}"
        ))
        return
    
    elif update.effective_chat.type == Chat.PRIVATE:
        if update.my_chat_member.new_chat_member['status'] == update.my_chat_member.new_chat_member.BANNED:
            await Users.banned(update.effective_chat.id)
            Log.info(f"I was banned by private user {update.effective_chat.id}")
            await LogSheet.write(update.effective_chat.id, "Banned by private user")
            return
        
        elif update.my_chat_member.new_chat_member['status'] == update.my_chat_member.new_chat_member.MEMBER:
            await Users.unbanned(update.effective_chat.id)
            Log.info(f"I was unbanned by private user {update.effective_chat.id}")
            await LogSheet.write(update.effective_chat.id, "Unbanned by private user")
            return
    Log.info(f"Other chat member event in {update.effective_chat.type} {update.effective_chat.id}")