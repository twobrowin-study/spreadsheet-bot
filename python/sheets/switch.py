import pandas as pd
from sheets.sheet import AbstractSheetAdapter

from settings import SwitchUpdateTime

from sheets.i18n import I18n

from errors import BotShouldBeInactive

class SwitchAdapterClass(AbstractSheetAdapter):
    def __init__(self) -> None:
        super().__init__('switch', 'switch', SwitchUpdateTime, None, True)
    
    async def _pre_async_init(self):
        self.sheet_name = I18n.switch
    
    async def _get_df(self) -> pd.DataFrame:
        df = pd.DataFrame(await self.wks.get_all_records())
        df = df.drop(index = 0, axis = 0)
        df = df.loc[
            (df.bot_active.isin(I18n.yes_no)) &
            (df.user_registration_open.isin(I18n.yes_no))
        ]
        if df.empty:
            raise BaseException("Switch sheet is in bad condition")
        return df
    
    async def _process_df_update(self):
        for _,row in self.as_df.iterrows():
            for column in self.as_df.columns:
                setattr(self, column, row[column] == I18n.yes)
            break
        if not self.bot_active:
            raise BotShouldBeInactive()

Switch = SwitchAdapterClass()