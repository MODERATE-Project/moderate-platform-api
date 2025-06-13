import marimo

__generated_with = "0.13.9"
app = marimo.App(width="medium", app_title="Synthetic Load Profile Generator")


@app.cell
def _():
    import marimo as mo

    default_model_url = "https://github.com/MODERATE-Project/Synthetic-Load-Profiles/releases/download/example-model-v2/trained-sample-model-v2.pt.zst"
    default_test_data_url = "https://github.com/MODERATE-Project/Synthetic-Load-Profiles/releases/download/example-model-v2/test-data.csv.zip"
    default_train_data_url = "https://github.com/MODERATE-Project/Synthetic-Load-Profiles/releases/download/example-model-v2/train-data.csv.zip"

    # Pre-trained model file form
    model_form = mo.ui.text(
        kind="url",
        full_width=True,
        label="URL to the trained model file, compressed using ZSTD, as produced by the training script in the repository",
        value=default_model_url,
    ).form(label="Pre-trained Model")

    # Test data file form
    test_data_form = mo.ui.text(
        kind="url",
        full_width=True,
        label="URL to the test data file (CSV format)",
        value=default_test_data_url,
    ).form(label="Test Data")

    # Train data file form
    train_data_form = mo.ui.text(
        kind="url",
        full_width=True,
        label="URL to the train data file (CSV format)",
        value=default_train_data_url,
    ).form(label="Train Data")

    return mo, model_form, test_data_form, train_data_form


@app.cell
def _(mo):
    mo.md(
        r"""
    # Synthetic Load Profile Generator

    ## Introduction

    **Repository:** [MODERATE-Project/Synthetic-Load-Profiles](https://github.com/MODERATE-Project/Synthetic-Load-Profiles)

    This notebook demonstrates the use of a Generative Adversarial Network (GAN) designed to generate synthetic electricity load profiles. The model learns from historical electricity consumption data to create realistic synthetic profiles, which can be useful for:

    - Energy analysis and forecasting
    - Grid simulations and planning
    - Privacy-preserving data sharing
    - Research and development

    ### Training Methods

    The original repository provides two methods for training the model:

    1. **Marimo notebook**: User-friendly interface for uploading data and configuring settings
    2. **Python script**: Advanced customization and support for larger datasets

    ### About This Notebook

    This notebook focuses on **inference using a pre-trained model** rather than training. It demonstrates how to generate synthetic load profiles using a model trained on publicly available open data.

    **Required files:**
    - Pre-trained model (compressed with ZSTD)
    - Test data (CSV format)
    - Training data (CSV format)

    > **Note:** To train your own model and fine-tune it for your specific needs, please refer to the original repository.
    """
    )
    return


@app.cell
def _(mo, model_form, test_data_form, train_data_form):
    mo.vstack(
        [
            mo.md("## File Configuration"),
            mo.md("Please provide URLs for all three required files:"),
            model_form,
            test_data_form,
            train_data_form,
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    ## Synthetic Load Profile Generation

    Once all three files are provided, the system will:

    1. **Load and decompress** the pre-trained model using Zstandard compression (zstd)
    2. **Initialize** the neural network with the loaded model state
    3. **Generate** synthetic data by feeding random noise through the generator
    4. **Visualize** comparisons between real and synthetic data

    The generation process creates realistic load profiles that maintain the statistical properties of the original training data while providing privacy-preserving synthetic alternatives.
    """
    )
    return


@app.cell
def _(mo, model_form, test_data_form, train_data_form):
    from moderate_api.notebooks.utils import download_file

    # Check that all three forms have been submitted
    mo.stop(
        model_form.value is None or not model_form.value,
        mo.callout("Please submit the pre-trained model form", kind="info"),
    )

    mo.stop(
        test_data_form.value is None or not test_data_form.value,
        mo.callout("Please submit the test data form", kind="info"),
    )

    mo.stop(
        train_data_form.value is None or not train_data_form.value,
        mo.callout("Please submit the train data form", kind="info"),
    )

    model_file = download_file(
        mo, model_form, title="Downloading model file", max_size_mb=200
    )

    test_data_file = download_file(
        mo,
        test_data_form,
        title="Downloading test data",
        max_size_mb=50,
        decompress_zip=True,
    )

    train_data_file = download_file(
        mo,
        train_data_form,
        title="Downloading train data",
        max_size_mb=50,
        decompress_zip=True,
    )

    mo.md("**Status:** All files downloaded successfully!")

    return model_file, test_data_file, train_data_file


@app.cell
def _(mo):
    import warnings

    import numpy as np
    import pandas as pd

    warnings.filterwarnings("ignore")

    from moderate_api.notebooks.synthethic_load.model.main import (
        generate_data_from_saved_model,
    )
    from moderate_api.notebooks.synthethic_load.model.plot import (
        plot_distrib,
        plot_mean_trends,
        plot_stats,
    )
    from moderate_api.notebooks.synthethic_load.model.utils import (
        calc_features,
        compute_trends,
    )

    mo.md(
        "**Status:** All imports successful! Matplotlib plots will be displayed using marimo's interactive plotting."
    )

    return (
        calc_features,
        compute_trends,
        generate_data_from_saved_model,
        np,
        pd,
        plot_distrib,
        plot_mean_trends,
        plot_stats,
    )


@app.cell
def _(mo, pd, test_data_file, train_data_file):
    train_data = pd.read_csv(train_data_file, index_col=0)
    train_data.index = pd.to_datetime(train_data.index)
    test_data = pd.read_csv(test_data_file, index_col=0)
    test_data.index = pd.to_datetime(test_data.index)

    mo.md(
        f"""
        ## Training Data Overview

        ### Dataset Characteristics
        - **Shape:** {train_data.shape[0]:,} time steps × {train_data.shape[1]:,} profiles
        - **Date Range:** {train_data.index.min().strftime('%Y-%m-%d')} to {train_data.index.max().strftime('%Y-%m-%d')}
        - **Time Steps per Day:** {len(train_data) // 368:,}

        ### Statistical Summary
        | Metric | Value |
        |--------|-------|
        | **Minimum** | {train_data.min().min():.4f} |
        | **Maximum** | {train_data.max().max():.4f} |
        | **Mean** | {train_data.mean().mean():.4f} |
        | **Standard Deviation** | {train_data.std().mean():.4f} |
        """
    )

    return test_data, train_data


@app.cell
def _(generate_data_from_saved_model, mo, model_file, np, pd, train_data):
    print("Loading pre-trained model and generating synthetic data...")

    # Generate synthetic data using the pre-trained model
    # We'll generate the same number of profiles as in our training set
    n_profiles = train_data.shape[1]
    print(f"Generating {n_profiles:,} synthetic profiles...")

    # This function loads the model and generates synthetic data
    synthetic_data_array_with_stamps = generate_data_from_saved_model(
        model_file, n_profiles=n_profiles
    )

    print("Synthetic data generation completed successfully!")
    print(f"Generated data shape: {synthetic_data_array_with_stamps.shape}")
    print(
        f"Number of profiles: {synthetic_data_array_with_stamps.shape[1] - 1:,}"
    )  # -1 because first column is timestamps

    # Extract the actual data (remove timestamp column)
    synthetic_data_array = synthetic_data_array_with_stamps[:, 1:].astype(np.float32)
    print(f"Synthetic values shape: {synthetic_data_array.shape}")

    # Convert to DataFrame for easier handling
    synthetic_df = pd.DataFrame(
        synthetic_data_array,
        index=train_data.index[: len(synthetic_data_array)],
        columns=[f"synthetic_{i}" for i in range(synthetic_data_array.shape[1])],
    )

    mo.md(
        f"""
        ## Synthetic Data Generation Results

        ### Generation Summary
        - **Profiles Generated:** {n_profiles:,}
        - **Time Steps:** {synthetic_data_array.shape[0]:,}
        - **Total Data Points:** {synthetic_data_array.size:,}

        ### Statistical Comparison
        | Metric | Training Data | Synthetic Data |
        |--------|---------------|----------------|
        | **Minimum** | {train_data.min().min():.4f} | {synthetic_df.min().min():.4f} |
        | **Maximum** | {train_data.max().max():.4f} | {synthetic_df.max().max():.4f} |
        | **Mean** | {train_data.mean().mean():.4f} | {synthetic_df.mean().mean():.4f} |
        | **Standard Deviation** | {train_data.std().mean():.4f} | {synthetic_df.std().mean():.4f} |

        **Status:** Model loaded and synthetic data generated successfully!
        """
    )

    return (synthetic_data_array,)


@app.cell
def _(calc_features, mo, np, synthetic_data_array, test_data, train_data):
    print("Calculating features for visualization and comparison...")

    # Convert data to numpy arrays for our plotting functions
    real_data_array = train_data.values.astype(np.float32)
    holdout_data_array = test_data.values.astype(np.float32)

    # Calculate features for both datasets (needed for plotting)
    real_features = calc_features(real_data_array, axis=0)
    synthetic_features = calc_features(synthetic_data_array, axis=0)
    holdout_features = calc_features(holdout_data_array, axis=0)

    mo.md(
        f"""
        ## Feature Analysis Preparation

        ### Feature Extraction Summary
        | Dataset | Feature Shape | Description |
        |---------|---------------|-------------|
        | **Training Data** | {real_features.shape} | Statistical features from real load profiles |
        | **Synthetic Data** | {synthetic_features.shape} | Statistical features from generated profiles |
        | **Holdout Data** | {holdout_features.shape} | Statistical features from test set |

        Features calculated include statistical measures that capture the essential characteristics of load profiles for comparison and validation.
        """
    )

    return (
        holdout_data_array,
        holdout_features,
        real_data_array,
        real_features,
        synthetic_features,
    )


@app.cell
def _(mo, plot_distrib, real_data_array, synthetic_data_array):
    print("Creating value distribution comparison: Training vs Synthetic data...")
    fig_distrib_synth = plot_distrib(real_data_array, synthetic_data_array)

    mo.vstack(
        [
            mo.md("## Distribution Analysis: Training vs Synthetic Data"),
            mo.md(
                "This plot compares the value distributions between the original training data and the generated synthetic data. Similar distributions indicate that the GAN has successfully learned the underlying patterns."
            ),
            mo.mpl.interactive(fig_distrib_synth),
        ]
    )
    return


@app.cell
def _(holdout_data_array, mo, plot_distrib, real_data_array):
    print("Creating value distribution comparison: Training vs Holdout data...")
    fig_distrib_holdout = plot_distrib(real_data_array, holdout_data_array)

    mo.vstack(
        [
            mo.md("## Distribution Analysis: Training vs Holdout Data"),
            mo.md(
                "This plot compares the value distributions between the training data and the holdout (test) data. This serves as a baseline comparison to understand the natural variation in the dataset."
            ),
            mo.mpl.interactive(fig_distrib_holdout),
        ]
    )
    return


@app.cell
def _(holdout_features, mo, plot_stats, real_features, synthetic_features):
    print("Creating statistical features comparison across all datasets...")
    fig_stats = plot_stats(real_features, synthetic_features, holdout_features)

    mo.vstack(
        [
            mo.md("## Statistical Features Comparison"),
            mo.md(
                "This visualization compares key statistical features across training, synthetic, and holdout datasets. The analysis helps validate whether the synthetic data maintains the statistical properties of the original data."
            ),
            mo.mpl.interactive(fig_stats),
        ]
    )
    return


@app.cell
def _(
    compute_trends,
    holdout_data_array,
    mo,
    plot_mean_trends,
    real_data_array,
    synthetic_data_array,
    train_data,
):
    print("Computing temporal trends for all datasets...")
    arr_dt = train_data.index
    trend_synth_dict = compute_trends(synthetic_data_array, arr_dt)
    trend_real_dict = compute_trends(real_data_array, arr_dt)
    trend_holdout_dict = compute_trends(holdout_data_array, arr_dt)

    print("Creating temporal trend comparison plots...")
    trend_plot_dict = plot_mean_trends(
        trend_real_dict, trend_synth_dict, trend_holdout_dict
    )

    mo.vstack(
        [
            mo.md("## Temporal Trend Analysis"),
            mo.md(
                """
        The following plots analyze temporal patterns in the data across different time scales:

        - **Daily patterns**: How load varies throughout the day
        - **Weekly patterns**: Differences between weekdays and weekends
        - **Seasonal patterns**: Long-term variations over months

        These comparisons help validate that the synthetic data captures not just statistical properties but also temporal dependencies present in real load profiles.
        """
            ),
            *[mo.mpl.interactive(plot) for plot in trend_plot_dict.values()],
        ]
    )
    return


if __name__ == "__main__":
    app.run()
