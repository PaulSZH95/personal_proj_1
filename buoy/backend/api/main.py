import os
from typing import IO
from uuid import uuid4
import shutil
from datetime import datetime
from tempfile import NamedTemporaryFile
from contextlib import asynccontextmanager


from fastapi import FastAPI, status, UploadFile
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

# from redis_package import redis_wrapper as rw # on docker
from redis_package import redis_wrapper as rw

# from ..src import dataclasses as dc
from src import dataclasses as dc


db_connections = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Fastapi lifespan implementation

    Args:
        app (FastApi): instance of FastApi
    Returns:
        None
    """
    db_connections["redis_db"] = await rw.redis_db_async("redis_db", 6380)
    db_connections["redis_queue"] = await rw.redis_db_async("redis", 6379)
    yield  # Yield control back to FastAPI. The app is now running.
    # Clean up when app is shutting down
    await db_connections.clear()


app = FastAPI(lifespan=lifespan)


@app.post("/text_chunk/")
async def text_chunk(selected_span: dc.JobChunkText) -> str:
    """
    function for parsing selected texts over job portals

    Args:
        selected_span (dc.JobChunkText): selected parts of job portal

    Returns:
        str: cleaned_text
    """
    # TODO: add in the resume parser rather than just cleaning
    task_name = dc.Task(task="job_ad_upload")
    uid = str(uuid4())
    time = datetime.utcnow().isoformat()
    status_code = 202
    status_name = "Queued"
    try:
        await rw.update_message(
            db=db_connections["redis_queue"],
            uid=uid,
            data=selected_span.text_chunk,
            time=time,
            queue_name="worker_queue",
            task=task_name,
        )
        await rw.redis_save_to_db(
            db=db_connections["redis_db"],
            uid=uid,
            data=selected_span.text_chunk,
            time=time,
            task=task_name,
            status_code=status_code,
            status_name=status_name,
            final_result=None,
        )
    except Exception as e:
        print(e)
    return selected_span.text_chunk


@app.post("/resume/")
async def resume_submission(resume: UploadFile):
    """
    function for accepting resume file uploads

    Args:
        resume (UploadFile): files

    Returns:
        None
    """
    allowed_types = [
        "text/xml",
        "text/html",
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    if resume.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, DOCX, HTML allowed",
        )
    file_name = resume.filename
    current_dir = os.path.dirname(__file__)
    list_of_folders = current_dir.split("api")
    if len(list_of_folders) == 2:
        target_dir = os.path.join(list_of_folders[0], "api", "resume_loc")
    else:
        target_dir = current_dir

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    file_size_limit = 1024 * 1024
    real_file_size = 0
    temp: IO = NamedTemporaryFile(delete=False)
    for chunk in resume.file:
        real_file_size += len(chunk)
        if real_file_size > file_size_limit:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds the maximum limit of 1Mb",
            )
        temp.write(chunk)
    temp.close()
    if os.path.isdir(target_dir) and "resume_loc" in target_dir:
        final_file_dest = os.path.join(target_dir, file_name)
        shutil.move(temp.name, final_file_dest)
    else:
        final_file_dest = temp.name
    try:
        task_name = dc.Task(task="resume_upload")
        uid = str(uuid4())
        time = datetime.utcnow().isoformat()
        status_code = 202
        status_name = "Queued"
        await rw.update_message(
            # db,uid,data,time,queue_name,task
            db=db_connections["redis_queue"],
            uid=uid,
            data=final_file_dest,
            time=time,
            queue_name="worker_queue",
            task=task_name,
        )
        await rw.redis_save_to_db(
            db=db_connections["redis_db"],
            uid=uid,
            data=final_file_dest,
            time=time,
            task=task_name,
            status_code=status_code,
            status_name=status_name,
            final_result=None,
        )
        return JSONResponse(
            content={"message": "File uploaded successfully"}, status_code=200
        )
    except HTTPException as e:
        return JSONResponse(content={"message": f"Errors:\n{e}"}, status_code=500)


@app.get("/jobs/")
async def item_lists():
    """
    function for getting list of job uid

    Args:
        None

    Returns:
        None
    """
    uids_list = await rw.query_all_uids(db_connections["redis_db"])
    return JSONResponse(content={"uids": uids_list}, status_code=200)


@app.get("/jobs/{job_uid}")
async def read_item(job_uid: str):
    """
    function for getting job_status

    Args:
        job_uid (str): string uid of job

    Returns:
        None
    """
    status_name, status_code, final_result = await rw.get_job_status(
        db_connections["redis_db"], job_uid
    )
    content_dict = {
        "uid": job_uid,
        "status_code_of_internal_process": status_code,
        "job_status": status_name,
        "result": final_result,
    }

    return JSONResponse(content=content_dict, status_code=200)
