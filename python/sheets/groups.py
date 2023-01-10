import pandas as pd
from sheets.sheet import AbstractSheetAdapter

from telegram import Message, Update, Chat, Bot
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from sheets.i18n import I18n
from sheets.settings import Settings
from sheets.report import Report

class GroupsAdapterClass(AbstractSheetAdapter):
    def __init__(self) -> None:
        super().__init__('groups', 'groups', None, True)
        self.GroupChatFilter    = self.GroupChatClass(outer_obj=self)
        self.IsRegisteredFilter = self.GroupChatFilter & self.IsRegisteredClass(outer_obj=self)
        self.IsAdminFilter      = self.GroupChatFilter & self.IsAdminClass(outer_obj=self)

        self.uid_col = 'chat_id'
    
    async def _pre_async_init(self):
        self.sheet_name = I18n.groups
        self.update_sleep_time = Settings.groups_update_time
    
    async def _get_df(self) -> pd.DataFrame:
        df = pd.DataFrame(await self.wks.get_all_records())
        df = df.drop(index = 0, axis = 0)
        df = df.loc[
            (df.chat_id != "") &
            (df.is_admin.isin(I18n.yes_no_super)) &
            (df.is_active == I18n.yes)
        ]
        df.chat_id = df.chat_id.apply(str)
        return df
    
    async def send_to_all_normal_groups(self, bot: Bot, message: str, parse_mode: str, send_photo: str = None):
        await self._send_to_all_uids(
            self.as_df.is_admin == I18n.no,
            bot, message, parse_mode, send_photo
        )
    
    async def send_to_all_admin_groups(self, bot: Bot, message: str, parse_mode: str, send_photo: str = None):
        await self._send_to_all_uids(
            self.as_df.is_admin.isin(I18n.yes_super),
            bot, message, parse_mode, send_photo
        )
    
    async def send_to_all_superadmin_groups(self, bot: Bot, message: str, parse_mode: str, send_photo: str = None):
        await self._send_to_all_uids(
            self.as_df.is_admin == I18n.super,
            bot, message, parse_mode, send_photo
        )
    
    class GroupChatClass(AbstractSheetAdapter.AbstractFilter):
        def filter(self, message: Message) -> bool:
            return message.chat.type in [Chat.GROUP, Chat.SUPERGROUP, Chat.CHANNEL]
    
    class IsRegisteredClass(AbstractSheetAdapter.AbstractFilter):
        def filter(self, message: Message) -> bool:
            return self.outer_obj.exists(message.chat_id)
    
    class IsAdminClass(AbstractSheetAdapter.AbstractFilter):
        def filter(self, message: Message) -> bool:
            df = self.outer_obj.as_df
            return not df.loc[
                self.outer_obj.selector(message.chat_id) &
                (df.is_admin.isin(I18n.yes_super))
            ].empty
    
    async def help_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        group = self.as_df.loc[self.selector(update.effective_chat.id)].iloc[0]
        reply = Settings.help_admin_group if group.is_admin else Settings.help_normal_group
        await update.message.reply_markdown(reply)
    
    async def report_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_markdown(Report.markdown)

Groups = GroupsAdapterClass()
