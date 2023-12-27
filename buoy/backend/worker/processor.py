import asyncio
from json import dumps
import gc
import tracemalloc

from src import txt_parse_w_spacy_mnli as tpt_spacy
from redis_package import redis_wrapper as rw
from src import io


async def job_ad_process_text(message_json):
    text_chunk = message_json["data"]["data_info"]
    text_chunk = io.clean_and_format_text(text_chunk)
    list_of_info = tpt_spacy.mega_job(text_chunk)
    final_result = "<sep>".join(list_of_info)
    status_name = "job_ad processed"
    return final_result, status_name, message_json["uid"]


async def resume_process_text(message_json):
    file_path = message_json["data"]["data_info"]
    resume = io.file_parsing_by_type(
        io.get_mime_type(file_path),
        file_path,
    )
    resume = io.clean_and_format_text(resume)
    list_of_info = tpt_spacy.mega_job(resume)
    final_result = "<sep>".join(list_of_info)
    status_name = "resume processed"
    return final_result, status_name, message_json["uid"]


async def update_task_if_sucess(message_json, redis_db, async_func):
    final_result, status_name, uid = await async_func(message_json)
    if final_result:
        print(final_result, status_name, uid)
        await rw.update_status(
            redis_db,
            uid,
            200,
            status_name,
            final_result,
        )
    else:
        await rw.requeue(redis_db, "worker_queue", message_json)
    del final_result, status_name, uid
    gc.collect()


async def error_handling(e, message_json, redis_db, queue_name):
    status_name = f"resume_parsing failed due to {e}"
    await rw.update_failed_status(redis_db, status_name, message_json["uid"])
    message_json = dumps(message_json)
    await rw.requeue(redis_db, queue_name, message_json)
    del message_json
    gc.collect()


async def corrupt_data_handling(redis_db, queue_name, message_json):
    status_name = "failed job due to missing data field, data is corrupt"
    await rw.update_failed_status(redis_db, status_name, message_json["uid"])
    message_json = dumps(message_json)
    await rw.requeue(redis_db, queue_name, message_json)
    del message_json
    gc.collect()


async def process_info(redis_conn, redis_db, queue_name="worker_queue"):
    message_json = await rw.redis_queue_pop(redis_conn, queue_name)
    if not message_json:
        await asyncio.sleep(1)
    task = message_json["task"]
    match task:
        case "job_ad_upload":
            print("hit joh_ad_routine")
            try:
                await update_task_if_sucess(message_json, redis_db, job_ad_process_text)
            except Exception as e:
                await error_handling(e, message_json, redis_db, queue_name)
        case "resume_upload":
            print("hit resume_routine")
            try:
                await update_task_if_sucess(message_json, redis_db, resume_process_text)
            except Exception as e:
                await error_handling(e, message_json, redis_db, queue_name)
        case _:
            print("hit corrupt_ad_routine")
            if task is None:
                await corrupt_data_handling(redis_db, queue_name, message_json)


async def main():
    tracemalloc.start()
    queue_name = "worker_queue"
    redis_conn = await rw.redis_db_async("redis", 6379)
    redis_db = await rw.redis_db_async("redis_db", 6380)

    try:
        while True:
            await process_info(redis_conn, redis_db, queue_name)
            await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        # Cancel all running tasks
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

        # Cancel all tasks
        for task in tasks:
            task.cancel()

        # Await task cancellation
        await asyncio.gather(*tasks, return_exceptions=True)

        # Close Redis connections
        await redis_db.close()
        await redis_conn.close()

        # Memory snapshot and print top stats
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("lineno")
        print("[Top 10]")
        for stat in top_stats[:10]:
            print(stat)

        print("Shutting down gracefully...")


if __name__ == "__main__":
    asyncio.run(main())
