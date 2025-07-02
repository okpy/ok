# 5/2/25 okpy.org Outage

## Context

On May 2 2025, okpy.org went down. This document describes the root cause of the issue and how we resolved it.

The document first contains a concise description of the issue and the patch.

For future reference, we then go into a more leisurely discussion of the thought process and learnings gained through the debugging process.

## Executive Summary

### Issue

```
  File "/usr/local/lib/python3.5/site-packages/gunicorn/sock.py", line 44, in set_options
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
OSError: [Errno 95] Not supported"
```

1. We have GKE autoupgrade enabled, and the node OS base image underwent a minor upgrade on 5/2.
2. This new image no longer supports the socket option `SO_REUSEPORT`
3. Based on the [this issue](https://github.com/amazonlinux/amazon-linux-2023/issues/901), Gunicorn 19.7.1 does not correctly detect this; `hasattr(socket, 'SO_REUSEPORT')` incorrectly returns `True`, so Gunicorn will attempt to use a socket that doesn't exist. An uncaught `OSError` then occurs.
4. Based on snippets from Gunicorn [19.7.1](https://github.com/benoitc/gunicorn/blob/19.7.1/gunicorn/sock.py#L42) and Gunicorn [19.8.0+](https://github.com/benoitc/gunicorn/blob/19.8.0/gunicorn/sock.py#L42-L43), We see that newer versions have the check `if self.conf.reuse_port`, which prevents Gunicorn from trying to use the socket unless explicitly instructed to do so (which this codebase doesn't).

### Fix
- Gunicorn: 19.7.1 -> 19.8.0, Python: 3.5 -> 3.7
- Rationale: Gunicorn 19.8.0 is the [minimal version](https://github.com/benoitc/gunicorn/blob/19.8.0/gunicorn/sock.py#L42) that implements the additional safeguard. Python 3.7 is the minimal version that [supports](https://pypi.org/project/gunicorn/19.8.0/) Gunicorn 19.8.0

### Visible changes
- Okpy v3.9.01 -> v3.9.02

## Debugging Process (WIP)

### How do we get ahold of Okpy?

### What do the logs say?

### Why now? What changed?

### Candidate problems

### Solving the problem

### How do we get CircleCI to work?

### How do we pass the CircleCI tests?

### How do we deploy the change?
