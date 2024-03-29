from telegram.ext import Application
import asyncio
import gspread_asyncio
from gspread import utils
import pandas as pd

from telegram import (
    Bot,
    InlineKeyboardMarkup,
    Document
)
from telegram.ext.filters import MessageFilter

from google.oauth2.service_account import Credentials 

from settings import SheetsSecret, SheetsLink
from drive import SaveToDrive

from log import Log

def get_creds():
    creds = Credentials.from_service_account_info(SheetsSecret)
    scoped = creds.with_scopes([
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ])
    return scoped

agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)

class AbstractSheetAdapter():
    def __init__(self, sheet_name: str, name: str, update_sleep_time: int = None, retry_sleep_time: int = None, initialize_as_df: bool = False) -> None:
        self.sheet_name = sheet_name
        self.name = name
        self.update_sleep_time = update_sleep_time if update_sleep_time is not None else 3600
        self.retry_sleep_time = retry_sleep_time if retry_sleep_time is not None else update_sleep_time
        self.initialize_as_df = initialize_as_df

        self.wks_row_pad = 1
        self.wks_col_pad = 1
        self.uid_col     = 'uid'
        
        self.wks_row  = lambda uid: self.as_df.loc[self.selector(uid)].index.values[0] + self.wks_row_pad
        self.wks_col  = lambda key: self.as_df.columns.get_loc(key) + self.wks_col_pad
        self.selector = lambda uid: (self.as_df[self.uid_col] == str(uid))
        self.exists   = lambda uid: not self.as_df.loc[self.selector(uid)].empty

        self.mutex = []
        self.whole_mutex = False
    
    async def async_init(self):
        await self._pre_async_init()
        await self._connect()
        if self.initialize_as_df:
            self.as_df = await self._get_df()
            Log.info(f"Initialized {self.name} as df")
            Log.debug(f"\n\n{self.as_df}\n\n")
        else:
            self.as_df = None
            Log.info(f"Initialized {self.name} as sheet")
        await self._post_async_init()
    
    async def _connect(self):
        self.agc = await agcm.authorize()
        self.sh = await self.agc.open_by_url(SheetsLink)
        self.wks = await self.sh.worksheet(self.sheet_name)
        Log.debug(f"(Re) Connected to {self.name} sheet")
    
    async def _pre_async_init(self):
        pass
    
    async def _post_async_init(self):
        await self._process_df_update()

    async def _get_df(self) -> pd.DataFrame:
        pass
    
    async def update(self, app: Application) -> None:
        await self._pre_update()
        await asyncio.sleep(self.update_sleep_time)
        
        Log.info(f"Prepared to update whole df {self.name}")
        while len(self.mutex) > 0:
            Log.info(f"Halted whole df update at {self.name} with mutex {self.mutex}")
            await asyncio.sleep(self.retry_sleep_time)
        app.create_task(self.update(app))
        self.whole_mutex = True
        
        await self._connect()
        self.as_df = await self._get_df()
        self.whole_mutex = False

        Log.info(f"Updated whole df {self.name}")
        Log.debug(f"\n\n{self.as_df}\n\n")
        await self._post_update()
    
    async def _pre_update(self):
        pass

    async def _post_update(self):
        await self._process_df_update()
    
    async def _process_df_update(self):
        pass
    
    async def _next_available_row(self) -> str:
        str_list = list(filter(None, await self.wks.col_values(1)))
        return str(len(str_list)+1)
    
    async def _find_col_by_data(self, data) -> int:
        cell = await self.wks.find(data)
        return cell.col
    
    def _prepare_batch_update(self, rowcols: list[tuple[str|int]]) -> list[str]:
        return [{
            'range': utils.rowcol_to_a1(x[0], x[1]),
            'values': [[x[2]]],
        } for x in rowcols ]
    
    async def _update_record(self, uid: str|int, key: str, value: str):
        selector = self.selector(uid)
        if self.as_df.loc[selector].empty:
            return
        self.as_df.loc[selector, key] = value
        wks_row = self.wks_row(uid)
        wks_col = self.wks_col(key)
        
        Log.info(f"Prepeared to update single record in {self.name} with {self.uid_col} {uid} write to {key} collumn")
        while self.whole_mutex:
            Log.info(f"Halted single update record in {self.name} with {self.uid_col} {uid} write to {key} collumn with whole mutex")
            await asyncio.sleep(self.retry_sleep_time)
        
        self.mutex.append(uid)
        await self.wks.update_cell(wks_row, wks_col, value)
        del self.mutex[self.mutex.index(uid)]
        
        Log.info(f"Done update single record in {self.name} with {self.uid_col} {uid} write to {key} collumn")
        Log.debug(f"Current mutext at {self.name} is {self.mutex}")
    
    async def _batch_update_or_create_record(self, uid: str|int, save_to = None, save_as = None, app: Application = None, **record_params):
        exists = self.exists(uid)
        record_action = 'update' if exists else 'create'
        collumns = record_params.keys()
        
        Log.info(f"Prepeared to batch update {record_action} record in {self.name} with {self.uid_col} {uid} and {collumns} collumns")
        while self.whole_mutex:
            Log.info(f"Halted to batch update {record_action} record in {self.name} with {self.uid_col} {uid} and {collumns} collumns with whole mutex")
            await asyncio.sleep(self.retry_sleep_time)
        self.mutex.append(uid)

        get_file = None
        for key,val in record_params.items():
            if type(val) in [list, tuple]:
                record_params[key] = val[-1].to_json()
                get_file = val[-1].get_file
            if type(val) == Document:
                record_params[key] = val.to_json()
                get_file = val.get_file
        
        if not exists:
            record_params[self.uid_col] = str(uid)
            tmp_df = pd.DataFrame(record_params, columns=self.as_df.columns, index=[0]).fillna('')
            if self.as_df.empty:
                self.as_df = tmp_df
            else:
                self.as_df = pd.concat([self.as_df, tmp_df], ignore_index=True)
        else:
            for key, value in record_params.items():
                self.as_df.loc[self.selector(uid), key] = value

        wks_row = self.wks_row(uid)
        wks_update = self._prepare_batch_update([
            (wks_row, self.wks_col(key), value)
            for key, value in record_params.items()
        ])
        
        await self.wks.batch_update(wks_update)
        if get_file != None and save_to != None and save_as != None and app != None:
            app.create_task(SaveToDrive(self.agc.gc.auth.token, save_to, save_as, get_file))
        
        del self.mutex[self.mutex.index(uid)]
        Log.info(f"Done batch update {record_action} record in {self.name} with {self.uid_col} {uid} and {collumns} collumns")
        Log.debug(f"Current mutext at {self.name} is {self.mutex}")
    
    def _get(self, selector, iloc = 0) -> pd.Series:
        row = self.as_df.loc[selector]
        if row.empty:
            return None
        return row.iloc[iloc]

    async def _send_to_all_uids(self, selector, bot: Bot, message: str, parse_mode: str, 
        send_photo: str = None, reply_markup: InlineKeyboardMarkup = None
    ):
        if send_photo == None or send_photo == '':
            for uid in self.as_df.loc[selector][self.uid_col].to_list():
                try:
                    await bot.send_message(chat_id=uid, text=message, parse_mode=parse_mode, reply_markup=reply_markup)
                except Exception:
                    Log.info(f"Error while sending message to id {uid}")
            return
        for uid in self.as_df.loc[selector][self.uid_col].to_list():
            try:
                await bot.send_photo(chat_id=uid, photo=send_photo, caption=message, parse_mode=parse_mode, reply_markup=reply_markup)
            except Exception:
                Log.info(f"Error while sending photo to id {uid}")
    
    class AbstractFilter(MessageFilter):
        def __init__(self, name: str = None, data_filter: bool = False, outer_obj = None):
            super().__init__(name, data_filter)
            self.outer_obj = outer_obj