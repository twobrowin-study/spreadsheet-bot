from telegram import InlineKeyboardMarkup,InlineKeyboardButton
import pandas as pd
from sheets.sheet import AbstractSheetAdapter

from sheets.i18n import I18n
from sheets.settings import Settings

from datetime import datetime

class NotificationsAdapterClass(AbstractSheetAdapter):
    CALLBACK_SET_STATE_PREFIX   = 'user_notification_set_state_'
    CALLBACK_SET_STATE_TEMPLATE = 'user_notification_set_state_{state}'
    CALLBACK_SET_STATE_PATTERN  = 'user_notification_set_state_*'

    CALLBACK_ANSWER_PREFIX    = 'user_notification_answer_'
    CALLBACK_ANSWER_TEMPLATE  = 'user_notification_answer_{state}_{answer}'
    CALLBACK_ANSWER_PATTERN   = 'user_notification_answer_*'
    CALLBACK_ANSWER_SEPARATOR = '_'

    def __init__(self) -> None:
        super().__init__('notifications', 'notifications', initialize_as_df=True)

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

        df.button_text   = df.button_text.apply(lambda x: x.split('\n'))
        df.button_answer = df.button_answer.apply(lambda x: x.split('\n'))
        
        df = df.loc[
            (df.scheldue_date != "") &
            (df.is_active.isin(I18n.yes_no_done)) &
            (df.text_markdown != "") &
            (
                (
                    (df.state == "")
                ) | (
                    (df.state != "") &
                    (df.button_text.apply(lambda x: len(x))   == 1) &
                    (df.button_answer.apply(lambda x: len(x)) == 2)
                ) | (
                    (df.state != "") &
                    (df.button_text.apply(lambda x: len(x)) == df.button_answer.apply(lambda x: len(x)))
                )
            )
        ]
        df.scheldue_date = df.scheldue_date.apply(lambda s: datetime.strptime(str(s), "%d.%m.%Y %H:%M"))
        return df
    
    async def _process_df_update(self):
        self.states = self.as_df.state.values
    
    async def set_done(self, idx: int|str):
        await self._update_record(idx, 'is_active', I18n.done)
    
    def get(self, state: str) -> pd.Series:
        return self._get(self.as_df.state == state)
    
    def get_text_markdown(self, state: str) -> str:
        return self.get(state).text_markdown
    
    def get_button_answer(self, state: str, answer_idx: int = None) -> str|tuple[str,str]:
        row = self.get(state)
        if len(row.button_text) == 1:
            return row.button_answer[0]
        if len(row.button_text) > 1 and answer_idx in range(len(row.button_text)):
            return row.button_answer[answer_idx], row.button_text[answer_idx]
        return None

    def get_keyboard(self, state: str) -> InlineKeyboardMarkup|None:
        button_text = self.get(state).button_text
        if len(button_text) == 1:
            return InlineKeyboardMarkup([
                [InlineKeyboardButton(button_text[0],
                    callback_data=self.CALLBACK_SET_STATE_TEMPLATE.format(state=state)
                )]
            ])
        if len(button_text) > 1:
            return InlineKeyboardMarkup([
                [InlineKeyboardButton(button_text[idx],
                    callback_data=self.CALLBACK_ANSWER_TEMPLATE.format(state=state, answer=idx)
                )]
                for idx in range(len(button_text))
            ])
        return None

Notifications = NotificationsAdapterClass()
