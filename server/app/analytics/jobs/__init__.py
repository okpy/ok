
def register_job(name, job):
    available_jobs[name] = job

def get_job(name, user, filters):
    if name not in available_jobs:
        return None
    return available_jobs[name].get_job(user, filters)

import sample_job
available_jobs = {
    'sample': sample_job
}
