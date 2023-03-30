import pandas as pd
from sheets.sheet import AbstractSheetAdapter

from telegram import Update
from telegram.constants import MessageEntityType

from settings import SettingsUpdateTime

from sheets.i18n import I18n

class SettingsAdapterClass(AbstractSheetAdapter):
    def __init__(self) -> None:
        super().__init__('settings', 'settings', SettingsUpdateTime, None, True)
    
    async def _pre_async_init(self):
        self.sheet_name = I18n.settings
    
    async def _get_df(self) -> pd.DataFrame:
        return pd.DataFrame(await self.wks.get_all_records())
    
    async def _process_df_update(self):
        for _,row in self.as_df.iterrows():
            setattr(self, row.key, row.value)
        
    def user_template_from_update(self, update: Update) -> str:
        for entity in update.message.entities:
            if entity.type == MessageEntityType.BOT_COMMAND:
                command = update.message.parse_entity(entity)[1:].split('@')[0]
                if command == 'start':
                    command = 'restart'
                return getattr(self, f"{command}_user_template")

Settings = SettingsAdapterClass()