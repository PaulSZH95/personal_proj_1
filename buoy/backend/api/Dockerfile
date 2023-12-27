FROM python:3.12.1-slim-bullseye
RUN apt-get update && apt-get install -y git && pip install --upgrade pip
WORKDIR /app
COPY ./backend/api/requirements.txt /app/api/requirements.txt
RUN pip install -r /app/api/requirements.txt
COPY ./backend/api/main.py /app/api/main.py
COPY ./backend/redis_package /app/redis_package
COPY ./backend/src/api_init_file.py /app/src/__init__.py
COPY ./backend/src/dataclasses.py /app/src/dataclasses.py
COPY ./backend/src/io.py /app/src/io.py
VOLUME /app/api/resume_loc
RUN useradd -m -u 2222 coder && chown -R coder /app
USER coder
EXPOSE 80
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "80"]