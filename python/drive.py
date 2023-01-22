import aiohttp
import json
import io
import filetype

from telegram import File
from log import Log

url = "https://www.googleapis.com/upload/drive/v3/files"

async def SaveToDrive(token: str, folder_link: str, file_name: str, get_file: File) -> dict:
    folder_id = folder_link.split('/')[-1].split('?')[0]
    Log.info(f"Start saving file {file_name} to folder id {folder_id}")
    file: File = await get_file()
    
    in_memory = io.BytesIO()
    await file.download_to_memory(in_memory)
    
    in_memory.seek(0)
    extension = filetype.guess_extension(in_memory)

    async with aiohttp.ClientSession() as session:
        metadata = {"name": f"{file_name}.{extension}", "parents": [folder_id]}
        data = aiohttp.FormData()
        data.add_field("metadata", json.dumps(metadata), content_type="application/json; charset=UTF-8")
        
        in_memory.seek(0)
        data.add_field("file", in_memory.read())
        
        headers = {"Authorization": "Bearer " + token}
        params = {"uploadType": "multipart"}
        async with session.post(url, data=data, params=params, headers=headers) as resp:
            Log.info(f"Done saving file {file_name} to folder id {folder_id}")
            in_memory.close()
            return await resp.json()