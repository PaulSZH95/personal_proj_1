FROM pytorch/pytorch:latest
WORKDIR /app
COPY ./backend/worker/requirements.txt /app/worker/requirements.txt
RUN apt-get update && apt-get install -y git nano && pip install --upgrade pip
RUN pip install -r /app/worker/requirements.txt
RUN python -m spacy download en_core_web_lg
COPY ./backend/src/worker_init_file.py /app/src/__init__.py
COPY ./backend/src/io.py /app/src/io.py
COPY ./backend/src/dataclasses.py /app/src/dataclasses.py
COPY ./backend/src/txt_parse_w_spacy_mnli.py /app/src/txt_parse_w_spacy_mnli.py
COPY ./backend/worker/processor.py /app/worker/processor.py
COPY ./backend/redis_package /app/redis_package
VOLUME /app/api/resume_loc
RUN useradd -m -u 2222 coder && chown -R coder /app
USER coder
EXPOSE 8888
CMD ["python", "-m","worker.processor"]