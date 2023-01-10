from sheets.sheet import AbstractSheetAdapter
from datetime import datetime

from sheets.i18n import I18n

from log import Log

class LogSheetAdapterClass(AbstractSheetAdapter):
    def __init__(self) -> None:
        super().__init__('logs', 'log-sheet', None, False)
    
    async def _pre_async_init(self):
        self.sheet_name = I18n.logs
    
    async def _post_async_init(self):
        self.timestamp_col = await self._find_col_by_data('timestamp')
        self.chat_id_col = await self._find_col_by_data('chat_id')
        self.message_col = await self._find_col_by_data('message')
    
    async def write(self, chat_id: int|str, message: str):
        row = await self._next_available_row()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update = self._prepare_batch_update([
            (row, self.timestamp_col, timestamp),
            (row, self.chat_id_col, chat_id),
            (row, self.message_col, message),
        ])
        await self.wks.batch_update(update)
        Log.info(f"Wrote to {self.name} log database chat_id: {chat_id} message: {message}")

LogSheet = LogSheetAdapterClass()