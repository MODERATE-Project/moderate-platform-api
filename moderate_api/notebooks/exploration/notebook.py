import marimo

__generated_with = "0.7.14"
app = marimo.App(width="medium", app_title="DataFrame exploration")


@app.cell
def __(mo):
    mo.md(r"""# Leveraging Marimo DataFrame tools to explore a dataset""")
    return


@app.cell
def __():
    import io
    import os
    import tempfile
    import urllib.parse

    import marimo as mo
    import polars as pl
    import requests

    return io, mo, os, pl, requests, tempfile, urllib


@app.cell
def __(mo):
    mo.md(r"""## Download the dataset""")
    return


@app.cell
def __(mo):
    form = mo.ui.text(full_width=True, placeholder="Paste your dataset URL here").form()
    form  # noqa: B018
    return (form,)


@app.cell
def __(form, io, mo, requests):
    mo.stop(form.value is None, mo.callout("Submit the form first", kind="info"))
    url = form.value
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get("content-length", 0))
    temp_file = io.BytesIO()

    with mo.status.progress_bar(
        title="Downloading dataset",
        subtitle=url,
        total=total_size,
        completion_title="Download complete",
        completion_subtitle="In-memory file",
    ) as bar:
        for data in response.iter_content(chunk_size=1024):
            size = len(data)
            temp_file.write(data)
            bar.update(size)

        temp_file.seek(0)
    return bar, data, response, size, temp_file, total_size, url


@app.cell
def __(mo):
    mo.md(r"""## Display the dataset""")
    return


@app.cell
def __(mo):
    mo.md(
        r"""Next, we try to guess the specific format of the dataset to select the correct DataFrame reader function."""
    )
    return


@app.cell
def __(os, pl, url, urllib):
    def guess_reader_function():
        try:
            parsed_url = urllib.parse.urlparse(url)
            filename = parsed_url.path.split("/")[-1]
            file_extension = os.path.splitext(filename)[1]
        except Exception:
            return None

        read_functions = {
            ".csv": pl.read_csv,
            ".xlsx": pl.read_excel,
            ".parquet": pl.read_parquet,
            ".json": pl.read_json,
        }

        return read_functions.get(file_extension, None)

    return (guess_reader_function,)


@app.cell
def __(mo, pl):
    reader_function_dropdown = mo.ui.dropdown(
        options={
            "CSV": pl.read_csv,
            "JSON": pl.read_json,
            "Parquet": pl.read_parquet,
            "Excel": pl.read_excel,
        },
        value=None,
        label="Select the DataFrame reader function",
    )

    reader_function_dropdown  # noqa: B018
    return (reader_function_dropdown,)


@app.cell
def __(guess_reader_function, mo, reader_function_dropdown):
    read_function = reader_function_dropdown.value or guess_reader_function()

    mo.stop(
        read_function is None,
        mo.callout(
            "Couldn't guess the dataset format. Select a DataFrame reader function to continue.",
            kind="warn",
        ),
    )
    return (read_function,)


@app.cell
def __(mo):
    mo.md(r"""### DataFrame represented as a table""")
    return


@app.cell
def __(mo, read_function, temp_file):
    try:
        df = read_function(temp_file)
    except Exception as ex:
        mo.stop(
            True,
            [
                mo.callout(
                    "An error occurred while reading the dataset. Is the selected reader function using the correct format?",
                    kind="warn",
                ),
                ex,
            ],
        )

    df  # noqa: B018
    return (df,)


@app.cell
def __(mo):
    mo.md(r"""### DataFrame data explorer""")
    return


@app.cell
def __(df, mo):
    mo.ui.data_explorer(df)
    return


if __name__ == "__main__":
    app.run()
