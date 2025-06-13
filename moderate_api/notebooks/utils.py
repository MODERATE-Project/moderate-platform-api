import io
import zipfile
from typing import Any, Optional, Union

import requests


def download_file(
    mo: Any,  # marimo module
    form: Any,  # marimo.ui.form - using Any to avoid module type issues
    url_key: str = "url",
    title: str = "Downloading file",
    completion_title: str = "Download complete",
    completion_subtitle: str = "In-memory file",
    max_size_mb: Optional[float] = 100,
    decompress_zip: bool = False,
) -> Union[io.BytesIO, dict[str, io.BytesIO]]:
    """This function downloads a file using a URL from a Marimo form, showing a progress bar during download.
    The file is downloaded in chunks and stored in memory.

    Supports both batch forms (where form.value is a dict) and individual forms (where form.value is a string).

    When decompress_zip=True:
    - If the file is not a ZIP: returns the original file as io.BytesIO
    - If the file is a ZIP with one file: returns that file as io.BytesIO (for convenience)
    - If the file is a ZIP with multiple files: returns dict mapping filenames to io.BytesIO objects
    """

    mo.stop(form.value is None, mo.callout("Submit the form first", kind="info"))

    # Handle both batch forms (dict) and individual forms (string)
    if isinstance(form.value, dict):
        url = form.value[url_key]
    else:
        # Individual form - form.value is directly the URL string
        url = form.value

    # Ensure url is a string
    if not isinstance(url, str):
        raise ValueError(f"Expected URL to be a string, got {type(url)}")

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

    if decompress_zip:
        # Check if the file is a ZIP by trying to read it as one
        try:
            with zipfile.ZipFile(temp_file, "r") as zip_file:
                # It's a valid ZIP file, extract all files
                extracted_files = {}

                for file_info in zip_file.infolist():
                    # Skip directories
                    if file_info.is_dir():
                        continue

                    # Extract file content
                    file_content = zip_file.read(file_info.filename)
                    extracted_files[file_info.filename] = io.BytesIO(file_content)

                temp_file.close()  # Close the original ZIP file

                if extracted_files:
                    # If there's only one file, return it directly for convenience
                    if len(extracted_files) == 1:
                        return next(iter(extracted_files.values()))
                    else:
                        # Multiple files, return the dictionary
                        return extracted_files
                else:
                    # ZIP was empty or contained only directories
                    mo.stop(
                        True,
                        mo.callout(
                            "ZIP file contains no extractable files", kind="warning"
                        ),
                    )

        except zipfile.BadZipFile:
            # Not a ZIP file, return the original file
            temp_file.seek(0)
            return temp_file

    return temp_file
