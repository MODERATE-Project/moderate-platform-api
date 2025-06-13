import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

features = [
    "means",
    "standard deviations",
    "minima",
    "maxima",
    "medians",
    "skews",
    "peak to peak ranges",
    "lower quartiles",
    "upper quartiles",
]
# Order must align with `calc_features`!


def plot_distrib(
    arr_real,
    arr_synth,
    xlabel="electricity consumption [kW]",
    ylabel="frequency of values occuring",
):
    fig = plt.figure(figsize=(7, 5))
    plt.hist(
        arr_real.flatten(),
        bins=100,
        alpha=0.5,
        label="Real",
        color="aqua",
        density=True,
    )
    plt.hist(
        arr_synth.flatten(),
        bins=100,
        alpha=0.5,
        label="Synthetic",
        color="hotpink",
        density=True,
    )
    plt.title("Value distributions", fontweight="bold")
    plt.xlabel("electricity consumption [kW]", fontweight="bold")
    plt.ylabel("density", fontweight="bold")
    plt.legend()
    plt.grid()
    plt.tight_layout()
    return fig


def plot_stat(
    arr_featureReal, arr_featureSynth, ax, title, arr_featureThird=None, descrFontSize=7
):
    # Prepare data arrays and labels
    data_arrays = [arr_featureReal, arr_featureSynth]
    labels = ["train", "synthetic"]

    # Add third array if provided
    if arr_featureThird is not None:
        data_arrays.append(arr_featureThird)
        labels.append("holdout")

    box_dict = ax.boxplot(data_arrays, vert=True)
    ax.set_xticklabels(labels)
    ax.set_title(title, fontweight="bold")
    ax.set_ylabel("value")
    ax.grid()

    # Adjust text positioning based on number of boxes
    num_boxes = len(data_arrays)
    text_offset = 0.15 if num_boxes == 3 else 0.1

    for idx, box in enumerate(box_dict["boxes"]):
        x_pos = idx + 1
        q1 = box.get_path().vertices[0, 1]
        q3 = box.get_path().vertices[2, 1]
        whiskers = [
            line.get_ydata()[1] for line in box_dict["whiskers"][idx * 2 : idx * 2 + 2]
        ]
        medians = box_dict["medians"][idx].get_ydata()[0]
        ax.text(
            x_pos + text_offset,
            q1,
            f"Q1: {q1:.2f}",
            va="center",
            fontsize=descrFontSize,
            color="blue",
        )
        ax.text(
            x_pos + text_offset,
            q3,
            f"Q3: {q3:.2f}",
            va="center",
            fontsize=descrFontSize,
            color="blue",
        )
        ax.text(
            x_pos + text_offset,
            medians,
            f"Med: {medians:.2f}",
            va="center",
            fontsize=descrFontSize,
            color="red",
        )
        ax.text(
            x_pos + text_offset,
            whiskers[0],
            f"Min: {whiskers[0]:.2f}",
            va="center",
            fontsize=descrFontSize,
            color="green",
        )
        ax.text(
            x_pos + text_offset,
            whiskers[1],
            f"Max: {whiskers[1]:.2f}",
            va="center",
            fontsize=descrFontSize,
            color="green",
        )


def plot_stats(arr_featuresReal, arr_featuresSynth, arr_featuresThird=None):
    fig, axes = plt.subplots(nrows=3, ncols=3, figsize=(20, 15.5))
    axes = axes.flatten()
    for idx, ax in enumerate(axes):
        if arr_featuresThird is not None:
            plot_stat(
                arr_featuresReal[idx],
                arr_featuresSynth[idx],
                ax,
                features[idx],
                arr_featuresThird[idx],
            )
        else:
            plot_stat(arr_featuresReal[idx], arr_featuresSynth[idx], ax, features[idx])

    # Update title based on number of datasets
    if arr_featuresThird is not None:
        plt.suptitle(
            "Three-way Comparison of...", ha="center", fontsize=16, fontweight="bold"
        )
    else:
        plt.suptitle("Comparison of...", ha="center", fontsize=16, fontweight="bold")
    plt.tight_layout()
    return fig


def plot_mean_trends(trendReal_dict, trendSynth_dict, trendThird_dict=None):
    trendPlot_dict = {}
    stats = ["mean", "std", "median", "min", "max", "skew"]
    # Order must align with `compute_group_stats`!

    for key in trendReal_dict.keys():
        fig, axs = plt.subplots(2, 3, figsize=(18, 8))
        axs = axs.flatten()
        x = range(1, trendReal_dict[key].shape[0] + 1)

        for idx, stat in enumerate(stats):
            axs[idx].plot(x, trendReal_dict[key][:, idx], label="Real", color="aqua")
            axs[idx].plot(
                x, trendSynth_dict[key][:, idx], label="Synthetic", color="hotpink"
            )
            if trendThird_dict is not None:
                axs[idx].plot(
                    x, trendThird_dict[key][:, idx], label="Holdout", color="green"
                )
            axs[idx].set_title(stat)
            if idx == 0:
                axs[idx].legend()

        fig.supxlabel(key, fontsize=12, fontweight="bold")
        fig.supylabel("value", fontsize=12, fontweight="bold")
        plt.suptitle(
            f"{key.capitalize()}ly trend".replace("Day", "Dai"), fontweight="bold"
        )
        plt.tight_layout()
        trendPlot_dict[f"{key}ly_trend".replace("day", "dai")] = fig
    return trendPlot_dict
