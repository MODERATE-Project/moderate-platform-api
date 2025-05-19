import marimo

__generated_with = "0.13.9"
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

    return mo, model_file_form


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
    import pandas as pd

    from moderate_api.notebooks.synthethic_load.inference import generate_profiles
    from moderate_api.notebooks.utils import download_file

    mo.stop(
        model_file_form is None or not model_file_form.value,
        mo.callout("Please upload a model file", kind="info"),
    )

    temp_file = download_file(mo, model_file_form)
    df_synth = generate_profiles(temp_file)

    # Convert index to datetime
    df_synth.index = pd.to_datetime(df_synth.index, format="%d.%m.%Y %H:%M")

    # Remove index name for better display in Marimo
    df_synth.index.name = None

    # Convert columns to strings
    df_synth.columns = [str(col) for col in df_synth.columns]
    df_synth

    return df_synth


@app.cell
def _(df_synth, mo):
    columns = [str(col) for col in df_synth.columns]
    default_value = [columns[0]] if columns else []
    options_dict = dict((col, col) for col in columns)

    profile_selector = mo.ui.multiselect(
        options=options_dict,
        value=default_value,
        label="Select load profiles to plot",
        full_width=True,
        max_selections=10,
    )

    profile_selector
    return profile_selector


@app.cell
def _(df_synth, mo, profile_selector):
    import plotly.graph_objects as go

    selected_cols = profile_selector.value
    fig = go.Figure()

    for col in selected_cols:
        fig.add_trace(
            go.Scatter(x=df_synth.index, y=df_synth[col], mode="lines", name=col)
        )

    fig.update_layout(
        title=f"Synthetic Load Profiles: {', '.join(selected_cols)}",
        xaxis_title="Time",
        yaxis_title="Load",
        height=500,
        showlegend=True,
    )

    plot = mo.ui.plotly(fig)
    plot

    return


if __name__ == "__main__":
    app.run()
