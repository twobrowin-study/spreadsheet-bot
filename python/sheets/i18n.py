import pandas as pd
from sheets.sheet import AbstractSheetAdapter

class I18nAdapterClass(AbstractSheetAdapter):
    def __init__(self) -> None:
        super().__init__('i18n', 'i18n', initialize_as_df=True)
    
    async def _get_df(self) -> pd.DataFrame:
        return pd.DataFrame(await self.wks.get_all_records())
    
    async def _post_async_init(self) -> None:
        for _,row in self.as_df.iterrows():
            setattr(self, row.key, row.value)
        self.yes_no = [self.yes, self.no]
        self.yes_no_done = [self.yes, self.no, self.done]
        self.yes_no_super = [self.yes, self.no, self.super]
        self.yes_super = [self.yes, self.super]

I18n = I18nAdapterClass()