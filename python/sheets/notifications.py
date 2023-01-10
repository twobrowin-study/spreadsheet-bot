import pandas as pd
from sheets.sheet import AbstractSheetAdapter

from sheets.i18n import I18n
from sheets.settings import Settings

from datetime import datetime

class NotificationsAdapterClass(AbstractSheetAdapter):
    def __init__(self) -> None:
        super().__init__('notifications', 'notifications', None, True)

        self.empty_row_attr = lambda row, content: type(row) == pd.Series and row[content] == '' or type(row) != pd.Series and row == None
        self.selector_to_notify = lambda: (
            (self.as_df.is_active == I18n.yes) &
            (self.as_df.scheldue_date <= datetime.now())
        )
        self.wks_row_pad = 2
        self.selector = lambda idx: self.as_df.index == idx
    
    async def _pre_async_init(self):
        self.sheet_name = I18n.notifications
        self.update_sleep_time = Settings.notifications_update_time
    
    async def _get_df(self) -> pd.DataFrame:
        df = pd.DataFrame(await self.wks.get_all_records())
        df = df.drop(index = 0, axis = 0)
        df = df.loc[
            (df.scheldue_date != "") &
            (df.is_active.isin(I18n.yes_no_done)) &
            (
                ((df.reply_state != "") & (df.is_text_reply.isin(I18n.yes_no))) |
                ((df.reply_state == "") & (df.is_text_reply == ""))
            )
        ]
        df.scheldue_date = df.scheldue_date.apply(lambda s: datetime.strptime(str(s), "%d.%m.%Y %H:%M"))
        return df
    
    async def _process_df_update(self):
        self.reply_to_yes = Settings.notification_reply_to_yes
        self.reply_to_no = Settings.notification_reply_to_no
    
    async def set_done(self, idx: int|str):
        await self._update_record(idx, 'is_active', I18n.done)
    
    def get(self, state: str) -> pd.Series:
        return self._get(self.as_df.reply_state == state)
    
    def get_text_markdown(self, state: str) -> str:
        row = self.get(state)
        if self.empty_row_attr(row, 'text_markdown'):
            return Settings.notification_default_restart_help_text
        return row.text_markdown
    
    def get_reply_answer(self, state: str) -> str:
        row = self.get(state)
        if self.empty_row_attr(row, 'reply_answer'):
            return Settings.notification_default_reply_answer
        return row.reply_answer
    
    def get_reply_state(self, text_markdown: str) -> tuple[str, str]:
        return self._get(self.as_df.text_markdown == text_markdown).reply_state

Notifications = NotificationsAdapterClass()
