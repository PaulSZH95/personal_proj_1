# import asyncio
from typing import Union, Optional
from datetime import datetime
from json import dumps, loads

from redis.commands.json.path import Path
from redis import asyncio as aioredis
from redis.commands.search.field import TextField, NumericField, TagField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query

# from ..src import dataclasses as dc
from src import dataclasses as dc


async def redis_db_async(
    host_name: Union[float, str] = "redis",
    port: int = 6379,
    password: Optional[str] = None,
):
    """
    Async wrapper function over aioredis to create database instance

    Args:
        host_name (Union[float, str]): name or IP of redis container
        port (int): exposed port of redis container
        password (Optional[str]): optional password for protected db

    Returns:
        Redis: an instance of aioredis.Redis
    """
    if password:
        redis = await aioredis.Redis.from_url(
            f"redis://{host_name}:{port}",
            max_connections=10,
            password=password,
        )
    else:
        redis = await aioredis.Redis.from_url(
            f"redis://{host_name}:{port}",
            max_connections=10,
        )
    try:
        await redis.ping()
        print("Connected to Redis")
    except Exception as e:
        print("Failed to connect to Redis:", e)

    return redis


async def update_message(
    db: aioredis.Redis,
    uid: str,
    data: str,
    time: datetime,
    queue_name: str = "worker_queue",
    task: dc.Task = None,
) -> None:
    """
    Generates a message and pushes it to a Redis queue

    Args:
        db (aioredis.Redis): An instance of Redis database connector
        uid (str): uuid4
        data (str): either file_path or text_chunk
        time (datetime): datetime of when process was created
        queue_name (str): Defined name for queue data in Redis
        task (dc.Task): name of task, only resume_upload or job_ad_upload
                        allowed

    Returns:
        None
    """
    if db:
        message = {
            "uid": uid,
            "ts": time,
            "task": task.task,
            "data": {"data_info": data},
        }
        message_json = dumps(message)
        print("message dumping ...")
        try:
            await db.lpush(queue_name, message_json)
        except aioredis.RedisError as e:
            print(f"Unable to call redis due to:\n{e}")


async def redis_queue_pop(db: aioredis.Redis, queue_name: str = "worker_queue") -> dict:
    """
    Wrapper for popping top of FILO queue

    Args:
        db (aioredis.Redis): An instance of Redis database connector
        queue_name (str): Defined name for queue data in Redis

    Returns:
        dict: A dictionary of message of bottom
    """
    _, message_json = await db.brpop(queue_name)
    message_json = loads(message_json)
    return message_json


async def redis_save_to_db(
    db,
    uid: str,
    data: str,
    time: datetime,
    task: dc.Task,
    status_code: int,
    status_name: str,
    final_result: str = None,
) -> None:
    """
    Generates a message and pushes it to a Redis queue

    Args:
        db: An instance of Redis database connector
        uid (str): uuid4
        data (str): either file_path or text_chunk
        time (datetime): datetime of when process was created
        task (dc.Task): name of task, only resume_upload or job_ad_upload
                        allowed
        status_code (int): http status code
                      200 - OK
                      202 - For Work in Progress
                      204 - No Content
                      400 - Bad Request
                      500 - Internal Server Error
        status_name (str): corresponding status description to status
        final_result (str): final_result placeholder

    Returns:
        None
    """
    if db:
        message = {
            "message": {
                "uid": uid,
                "ts": time,
                "task": task.task,
                "data": {"data_info": data},
                "status_code": status_code,
                "status_name": status_name,
                "final_result": final_result,
            }
        }
        key = f"message:{uid}"
        # message_json = dumps(message)
        try:
            await db.ft().info()
            print("posting msg on redis_db ...")
            await db.json().set(key, Path.root_path(), message)
        except aioredis.RedisError as e:
            schema = (
                TagField("$.message.uid", as_name="uid"),
                TextField("$.message.ts", as_name="ts"),
                TextField("$.message.task", as_name="task"),
                TextField("$.message.data_info", as_name="data"),
                NumericField("$.message.status", as_name="status_code"),
                TextField("$.message.status_name", as_name="status_name"),
                TextField("$.message.final_result", as_name="final_result"),
            )
            await db.ft().create_index(
                schema,
                definition=IndexDefinition(
                    prefix=["message:"], index_type=IndexType.JSON
                ),
            )
            print(f"creating index as index not found with error\n{e}")
            print("index created and posting message to db ...")
            await db.json().set(key, Path.root_path(), message)


async def update_status(
    db: aioredis.Redis, uid: str, status_code: int, status_name: str, final_result: str
) -> None:
    """
    Asynchronously updates the status of a job in the Redis database.

    Args:
        db (aioredis.Redis): An instance of Redis database connector.
        uid (str): Unique identifier of the job.
        status_code (int): Status code indicating the job's state.
        status_name (str): A descriptive name of the job's current status.
        final_result (str): The final result of the job, if completed.

    Returns:
        None
    """
    key = f"message:{uid}"
    print(f"updating {key} with {status_code},{status_name},{final_result}")
    await db.json().set(key, Path(".message.status_code"), status_code)
    await db.json().set(key, Path(".message.status_name"), status_name)
    await db.json().set(key, Path(".message.final_result"), final_result)


async def requeue(db: aioredis.Redis, queue_name: str, message_json: str) -> None:
    """
    Requeues a message in a Redis queue.

    Args:
        db (aioredis.Redis): An instance of Redis database connector.
        queue_name (str): The name of the Redis queue.
        message_json (str): The message in JSON format to be requeued.

    Returns:
        None
    """
    print("\tProcessing failed - requeuing...")
    await db.lpush(queue_name, message_json)


async def update_failed_status(
    redis_db: aioredis.Redis, status_name: str, uid: str
) -> None:
    """
    Updates the status of a job as failed in the Redis database.

    Args:
        redis_db (aioredis.Redis): An instance of Redis database connector.
        status_name (str): A descriptive name of the failure status.
        uid (str): Unique identifier of the job.

    Returns:
        None
    """
    status_code = 500
    final_result = None
    await update_status(redis_db, uid, status_code, status_name, final_result)


async def get_job_status(db: aioredis.Redis, uid: str) -> tuple:
    """
    Wrapper function for getting information of uid from rdb

    Args:
        db (aioredis.Redis): redis_db instance of aioredis
        uid (str): stringify id of jobs

    Returns:
        tuple: A tuple containing three elements in the following order:
            - status_name (str): The name of the status of the job.
            - status_code (int or str): status code of job ran internally
            - final_result (str): The final result or output associated with the job.
    """

    key = f"message:{uid}"
    status_name = await db.json().get(key, Path(".message.status_name"))
    status_code = await db.json().get(key, Path(".message.status_code"))
    final_result = await db.json().get(key, Path(".message.final_result"))
    return status_name, status_code, final_result


async def query_all_uids(db: aioredis.Redis) -> list:
    """
    Wrapper function which uses index of rdb to get uids

    Args:
        db (aioredis.Redis): redis_db instance of aioredis

    Returns:
        list: list of uids
    """

    query_str = "*"
    result = await db.ft().search(Query(query_str).return_fields("uid"))
    uids = [doc.uid for doc in result.docs]
    return uids
