import pandas as pd
from sheets.sheet import AbstractSheetAdapter

from sheets.i18n import I18n
from sheets.settings import Settings

class ReportAdapterClass(AbstractSheetAdapter):
    def __init__(self) -> None:
        super().__init__('report', 'report', initialize_as_df=True)
    
    async def _pre_async_init(self):
        self.sheet_name = I18n.report
        self.update_sleep_time = Settings.report_update_time
        self.retry_sleep_time  = self.update_sleep_time // 2
    
    async def _get_df(self) -> pd.DataFrame:
        df = pd.DataFrame(await self.wks.get_all_records())
        df = df.drop(index = 0, axis = 0)
        df = df.loc[
            (df.title != "") &
            (df.value != "")
        ]
        return df
    
    async def _process_df_update(self):
        self.markdown = "\n".join([
            f"{row.title}: `{row.value}`"
            for _,row in self.as_df.iterrows()
        ])

        self.send_every_x_active_users = Settings.report_send_every_x_active_users
        self.currently_active_users_template = Settings.report_currently_active_users_template

Report = ReportAdapterClass()
