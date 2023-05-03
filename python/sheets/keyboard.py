import pandas as pd
from sheets.sheet import AbstractSheetAdapter

from telegram import ReplyKeyboardMarkup

from sheets.i18n import I18n
from sheets.settings import Settings

class KeyboardAdapterClass(AbstractSheetAdapter):
    def __init__(self) -> None:
        super().__init__('keyboard', 'keyboard', initialize_as_df=True)
    
    async def _pre_async_init(self):
        self.sheet_name = I18n.keyboard
        self.REGISTER_FUNCTION = I18n.register
        self.update_sleep_time = Settings.keyboard_update_time
        self.retry_sleep_time  = self.update_sleep_time // 2
    
    async def _get_df(self) -> pd.DataFrame:
        df = pd.DataFrame(await self.wks.get_all_records())
        df = df.drop(index = 0, axis = 0)
        df = df.loc[
            (df.key != "") &
            (df.is_active == I18n.yes)
        ]
        return df
    
    async def _process_df_update(self):
        self.keys = self.as_df.key.values.tolist()
        self.reply_keyboard = ReplyKeyboardMarkup([
            self.keys[idx:idx+2]
            for idx in range(0,len(self.keys),2)
        ] if len(self.keys) > 2 else [[x] for x in self.keys])
        self.registration_keyboard_row = self._get(self.as_df.function == self.REGISTER_FUNCTION)
    
    def get(self, key: str) -> pd.Series:
        return self._get(self.as_df.key == key)

Keyboard = KeyboardAdapterClass()
