import datetime
import os
import re
import shutil

import requests

from bso.server.main.logger import get_logger
from bso.server.main.utils_swift import upload_object

PV_MOUNT = '/upw_data/'
logger = get_logger(__name__)


def get_filename_from_cd(cd: str):
    """ Get filename from content-disposition """
    if not cd:
        return None
    fname = re.findall('filename=(.+)', cd)
    if len(fname) == 0:
        return None
    return fname[0]


def download_file(url: str, upload_to_object_storage: bool = True, destination: str = None) -> str:
    os.system(f'mkdir -p {PV_MOUNT}')
    start = datetime.datetime.now()
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        try:
            local_filename = get_filename_from_cd(r.headers.get('content-disposition')).replace('"', '')
        except:
            local_filename = url.split('/')[-1]
        logger.debug(f'start downloading {local_filename} at {start}')
        local_filename = f'{PV_MOUNT}{local_filename}'
        if destination:
            local_filename = destination
        with open(local_filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f, length=16 * 1024 * 1024)
    end = datetime.datetime.now()
    delta = end - start
    logger.debug(f'end download in {delta}')
    if upload_to_object_storage:
        upload_object('unpaywall', local_filename)
    return f'{local_filename}'
