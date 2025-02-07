import marimo

__generated_with = "0.11.0"
app = marimo.App(width="medium", app_title="Synthetic Load Profile Generator")


@app.cell
def _():
    import marimo as mo

    default_model_url = "https://github.com/MODERATE-Project/Synthetic-Load-Profiles/releases/download/example-model/trained-sample-model.pt.zst"

    model_url = mo.ui.text(
        kind="url",
        full_width=True,
        label="URL to the trained model file, compressed using ZSTD, as produced by the training script in the repository",
        value=default_model_url,
    )

    model_file_form = (
        mo.md(
            """
            {url}
            """
        )
        .batch(url=model_url)
        .form()
    )

    return default_model_url, mo, model_file_form, model_url


@app.cell
def _(mo):
    mo.md(
        r"""
        # Synthetic Load Profile GAN

        ## Introduction

        🧑‍💻 [**Link to the original repository: MODERATE-Project/Synthetic-Load-Profiles**](https://github.com/MODERATE-Project/Synthetic-Load-Profiles)

        Here, MODERATE presents a Generative Adversarial Network (GAN) designed to generate synthetic electricity load profiles. 
        The model learns from historical electricity consumption data to create synthetic profiles, which can be useful for energy analysis, 
        grid simulations, and privacy-preserving data sharing. The repository provides two methods for training the model:

        1. Marimo notebook: Provides a user-friendly interface for uploading data and configuring settings.
        2. Python script: Allows for more customization and supports larger datasets.

        The present notebook does not demonstrate GAN training but provides a simple example of inference using a pre-trained model 
        trained on publicly available open data. 
        To train your own model and fine-tune it to your needs, please refer to the original repository.
        """
    )
    return


@app.cell
def _(mo, model_file_form):
    mo.vstack([mo.md(f"## Upload a pre-trained model"), model_file_form])
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Generate synthetic load profiles

        The model will be loaded and decompressed using Zstandard compression (zstd). 
        Then, a neural network with the loaded model state will generate synthetic data by feeding random noise through the generator.
        """
    )
    return


@app.cell
def _(mo, model_file_form):
    from moderate_api.notebooks.synthethic_load.inference import generate_profiles
    from moderate_api.notebooks.utils import download_file

    mo.stop(
        model_file_form is None or not model_file_form.value,
        mo.callout("Please upload a model file", kind="info"),
    )

    temp_file = download_file(mo, model_file_form)
    df_synth = generate_profiles(temp_file)
    df_synth

    return df_synth


if __name__ == "__main__":
    app.run()
