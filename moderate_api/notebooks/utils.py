import io
from typing import Optional

import marimo
import requests


def download_file(
    mo: marimo,
    form: marimo.ui.form,
    url_key: str = "url",
    title: str = "Downloading file",
    completion_title: str = "Download complete",
    completion_subtitle: str = "In-memory file",
    max_size_mb: Optional[float] = 100,
) -> io.BytesIO:
    """This function downloads a file using a URL from a Marimo form, showing a progress bar during download.
    The file is downloaded in chunks and stored in memory."""

    mo.stop(form.value is None, mo.callout("Submit the form first", kind="info"))
    url = form.value[url_key]
    response = requests.get(url, stream=True, allow_redirects=True)
    response.raise_for_status()
    total_size = int(response.headers.get("content-length", 0))

    if max_size_mb is not None:
        max_size_bytes = max_size_mb * 1024 * 1024

        if total_size > max_size_bytes:
            mo.stop(
                True,
                mo.callout(
                    f"File size ({total_size / 1024 / 1024:.1f}MB) exceeds maximum allowed size ({max_size_mb}MB)",
                    kind="danger",
                ),
            )

    temp_file = io.BytesIO()
    downloaded_size = 0

    with mo.status.progress_bar(
        title=title,
        subtitle=url,
        total=total_size,
        completion_title=completion_title,
        completion_subtitle=completion_subtitle,
    ) as bar:
        for data in response.iter_content(chunk_size=1024):
            size = len(data)
            downloaded_size += size

            # Check actual downloaded size regardless of content-length header
            if max_size_mb is not None and downloaded_size > max_size_bytes:
                temp_file.close()

                raise RuntimeError(
                    f"Download exceeded maximum allowed size ({max_size_mb}MB)"
                )

            temp_file.write(data)
            bar.update(size)

        temp_file.seek(0)

    return temp_file
