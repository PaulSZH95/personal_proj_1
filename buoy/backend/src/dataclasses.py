from pydantic import BaseModel, field_validator


class JobChunkText(BaseModel):
    # this text_chunk will be the key for request json
    # so you need send {"text_chunk": "selected span"}
    text_chunk: str


class Task(BaseModel):
    task: str

    @field_validator("task")
    def validate_field_name(cls, value):
        allowed_values = ["resume_upload", "job_ad_upload"]
        if value not in allowed_values:
            raise ValueError(f"Field value must be one of {allowed_values}")
        return value
