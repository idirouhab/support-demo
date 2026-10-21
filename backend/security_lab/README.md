# Security plugin lab

Added September 7, 2026 to exercise security-plugin detection. This standalone
FastAPI application deliberately contains SQL injection (CWE-89). It is not
registered in `app.main:app` and uses only two synthetic tickets in a fresh
in-memory database for each request.

Scan `backend/security_lab/app.py` explicitly, including intentional demo code
in the scan scope. The expected finding traces the untrusted `q` HTTP query
parameter through string interpolation into `database.execute(query)`.
An attacker can bypass the `is_private = 0` filter and read the private demo
ticket. A scanner that excludes test fixtures or intentional vulnerabilities
may omit this finding; that alone does not demonstrate a detection failure.

Run from the repository root:

```sh
cd backend
.venv/bin/python -m uvicorn security_lab.app:app --host 127.0.0.1 --port 8001
```

Ordinary search returns no private tickets; injected search returns both rows:

```sh
curl --get http://127.0.0.1:8001/api/tickets/search --data-urlencode 'q=Private'
curl --get http://127.0.0.1:8001/api/tickets/search --data-urlencode "q=' OR 1=1 -- "
```

Verify from `backend/` with `.venv/bin/python -m pytest`. The lab tests cover
ordinary filtering, reproduce the injection, and check that the main app returns
404 for the lab route. The injection test intentionally expects vulnerable
behavior; it is not a security regression test asserting that the flaw is fixed.

Keep this app local with synthetic data. Do not deploy it or wire it into the
support app. To practice remediation after the scan, parameterize the SQL query
and change the injection test to expect no private ticket. No fix or release is
part of this exercise.
