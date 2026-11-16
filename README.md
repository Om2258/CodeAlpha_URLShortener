# CodeAlpha URL Shortener

A small Flask and SQLite URL shortener built for CodeAlpha Backend Development Task 1. It creates unique short codes, persists each mapping, and redirects short links to their HTTP/HTTPS destinations. A responsive web form is included.

## Requirements

- Python 3.10+

## Run locally

```bash
cd CodeAlpha_URLShortener
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. The SQLite database is created at `instance/urls.sqlite3`.

To publish stable absolute links from a deployed instance, set `PUBLIC_BASE_URL` to its canonical origin (for example `https://short.example`) and `TRUSTED_HOSTS` to a comma-separated list of accepted hostnames.

## API

### Create a short link

`POST /api/shorten`

```json
{"url":"https://example.com/a/long/path"}
```

Returns `201 Created` with `code`, `original_url`, and `short_url`. Only HTTP and HTTPS URLs are accepted.

### Follow a short link

`GET /s/{code}` returns a `302` redirect. Unknown codes return JSON `404`.

### Inspect a link

`GET /api/links/{code}` returns the stored code, destination, and creation time.

## Tests

```bash
python -m unittest discover -s tests -v
```
