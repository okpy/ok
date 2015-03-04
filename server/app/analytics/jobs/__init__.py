from app.analytics import Job

def register_job(name, job):
    available_jobs[name] = job

def get_job(name, user, filters):
    if name not in available_jobs:
        return None
    job_instance = available_jobs[name]
    return Job(job_instance.KIND,
               user,
               job_instance.mapper,
               job_instance.reducer,
               filters=filters)

import sample_job
available_jobs = {
    'sample': sample_job
}
