import pandas as pd
from sheets.sheet import AbstractSheetAdapter

from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup

from sheets.i18n import I18n
from sheets.settings import Settings

class RegistrationAdapterClass(AbstractSheetAdapter):
    def __init__(self) -> None:
        super().__init__('registration', 'registration', initialize_as_df=True)
    
    async def _pre_async_init(self):
        self.sheet_name = I18n.registration
        self.update_sleep_time = Settings.registration_update_time
    
    async def _get_df(self) -> pd.DataFrame:
        df = pd.DataFrame(await self.wks.get_all_records())
        df = df.drop(index = 0, axis = 0)
        df = df.loc[
            (df.state != "") &
            (df.question != "") &
            (df.is_main_question.isin(I18n.yes_no))
        ]
        df.is_main_question = df.is_main_question.apply(lambda x: x == I18n.yes)
        return df
    
    async def _process_df_update(self):
        main_selector = self.as_df.is_main_question == True
        self.first = self._get(main_selector)
        
        self.states = self.as_df.state.values
        self.main_states = self.as_df.loc[main_selector].state.values

        self.last_state = self.states[-1]
        self.last_main_state = self.main_states[-1]

        self.is_document_state = lambda state: self.get(state).document_link not in ["", None]

    def _get(self, selector, iloc=0) -> pd.Series:
        curr = super()._get(selector, iloc)
        if type(curr) != pd.Series and curr == None:
            return None
        if curr.reply_keyboard == '':
            curr.reply_keyboard = ReplyKeyboardRemove()
        else:
            reply_text = curr.reply_keyboard.split("\n")
            curr.reply_keyboard = ReplyKeyboardMarkup([
                reply_text[idx:idx+2]
                for idx in range(0,len(reply_text),2)
            ])
        return curr
    
    def get(self, state: str) -> pd.Series:
        return self._get(self.as_df.state == state)
    
    def get_next(self, prev_state: str) -> pd.Series:
        prev_selector = (self.as_df.state == prev_state)
        next_index = self.as_df.loc[prev_selector].index[0] + 1
        return self._get(self.as_df.index == next_index)
    
    def __contains__(self, state: str):
        return state in self.states

Registration = RegistrationAdapterClass()
