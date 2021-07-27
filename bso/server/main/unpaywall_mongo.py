import json
import os
import pymongo
import random
import time

from typing import Union

from bso.server.main.logger import get_logger
from bso.server.main.utils_swift import upload_object

client = None
logger = get_logger(__name__)
PV_MOUNT = '/upw_data/'


def exception_handler(func):
    def inner_function(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exception:
            logger.error(f'{func.__name__} raises an error through decorator "exception_handler".')
            logger.error(exception)
            return None
    return inner_function


@exception_handler
def get_client() -> Union[pymongo.MongoClient, None]:
    global client
    if client is None:
        client = pymongo.MongoClient('mongodb://mongo:27017/', connectTimeoutMS=60000)
    return client


@exception_handler
def get_database(database: str = 'unpaywall') -> Union[pymongo.database.Databse, None]:
    _client = get_client()
    db = _client[database]
    return db


@exception_handler
def get_collection(collection_name: str) -> Union[pymongo.collection.Collection, None]:
    db = get_database()
    collection = db[collection_name]
    return collection


def drop_collection(collection_name: str) -> None:
    logger.debug(f'Dropping {collection_name}')
    collection = get_collection(collection_name=collection_name)
    collection.drop()


def clean(res: dict, coll: str) -> dict:
    if res:
        if '_id' in res:
            del res['_id']
        res['asof'] = coll
    return res


def get_doi(doi, collection_name: str) -> dict:
    collection = get_collection(collection_name=collection_name)
    for i in range(0, 5):
        while True:
            try:
                if isinstance(doi, str):
                    res = collection.find_one({'doi': doi})
                    res = clean(res, collection_name)
                elif isinstance(doi, list):
                    res = [e for e in collection.find({'doi': {'$in': doi}})]
                    for ix, e in enumerate(res):
                        res[ix] = clean(e, collection_name)
                return res
            except:
                time.sleep(60)
                continue
            break
    res = {}
    logger.error(f'Error while searching for doi {doi} into Mongo')
    return res


def get_doi_full(dois: list) -> dict:
    logger.debug(f'Getting doi info for {len(dois)} dois')
    db = get_database()
    res = {}
    for d in dois:
        res[d] = {}
    for i in range(0, 5):
        while True:
            try:
                collections = db.list_collection_names()
            except:
                time.sleep(60)
                continue
            break
    for collection in collections:
        if collection in ['pubmed']:
            continue
        current_list = get_doi(dois, collection)
        for e in current_list:
            d = e['doi']
            asof = e['asof']
            del e['asof']
            if asof != 'global':
                del e['doi']
            res[d].update({asof: e})
    return res


def aggregate(coll: str, pipeline: str, output: str) -> str:
    db = get_database()
    logger.debug(f'Aggregate {pipeline}')
    pipeline_type = type(pipeline)
    logger.debug(f'Pipeline_type = {pipeline_type}')
    if isinstance(pipeline, str):
        pipeline = json.loads(pipeline.replace("'", '"'))
    pipeline_type = type(pipeline)
    logger.debug(f'Pipeline_type = {pipeline_type}')
    rdm = random.randint(1, 10000)
    results_col = f'results_{output}_{rdm}'
    pipeline.append({"$out": results_col})
    logger.debug(pipeline)
    db[coll].aggregate(pipeline, allowDiskUse=True)
    output_json = f'{PV_MOUNT}{results_col}'
    export_cmd = f"mongoexport --forceTableScan --uri mongodb://mongo:27017/unpaywall -c {results_col}  " \
                 f"--out={output_json}"
    os.system(export_cmd)
    db[results_col].drop()
    res = upload_object('tmp', output_json)
    os.remove(output_json)
    return res
