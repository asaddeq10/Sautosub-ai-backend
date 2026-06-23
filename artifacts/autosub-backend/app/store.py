from app.models.job import Job

jobs: dict[str, Job] = {}


def get_job(job_id: str) -> Job | None:
    return jobs.get(job_id)


def set_job(job: Job) -> None:
    jobs[job.job_id] = job


def update_job(job_id: str, **kwargs) -> Job | None:
    job = jobs.get(job_id)
    if job is None:
        return None
    updated = job.model_copy(update=kwargs)
    jobs[job_id] = updated
    return updated
