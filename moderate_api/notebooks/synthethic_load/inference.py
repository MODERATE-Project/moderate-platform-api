import io

import numpy as np
import pandas as pd
import torch
import zstandard as zstd
from torch import nn, randn


class Generator(nn.Module):
    def __init__(self, model):
        super(Generator, self).__init__()
        self.model = model

    def forward(self, noise):
        output = self.model(noise)
        return output


def invert_min_max_scaler(arr_scaled, arr_min_max, feature_range):
    val_min, val_max = arr_min_max[0], arr_min_max[1]

    arr = (arr_scaled - feature_range[0]) * (val_max - val_min) / (
        feature_range[1] - feature_range[0]
    ) + val_min

    return arr


def revert_reshape_arr(arr):
    arr = arr.T.reshape(-1, arr.shape[0])
    return arr


def generate_profiles(model_input):
    """Generate synthetic profiles from a trained model."""

    # Load the compressed model
    if isinstance(model_input, str):
        with open(model_input, "rb") as file:
            compressed_data = file.read()
    elif isinstance(model_input, io.BytesIO):
        compressed_data = model_input.read()
        model_input.seek(0)  # Reset buffer position
    else:
        raise ValueError(
            "model_input must be either a string path or io.BytesIO object"
        )

    # Decompress the model
    dctx = zstd.ZstdDecompressor()
    with io.BytesIO() as buffer:
        with dctx.stream_reader(io.BytesIO(compressed_data)) as decompressor:
            buffer.write(decompressor.read())
            buffer.seek(0)
            model_state = torch.load(buffer, weights_only=False)

    # Initialize generator
    gen = Generator(model_state["gen_layers"])
    gen.load_state_dict(model_state["gen_state_dict"])

    # Generate synthetic data
    noise = randn(
        model_state["profileCount"],
        model_state["dimNoise"],
        1,
        1,
        device=model_state["device"],
    )

    x_synth = gen(noise)
    x_synth = x_synth.cpu().detach().numpy()

    # Post-process data
    x_synth = invert_min_max_scaler(
        x_synth, model_state["minMax"], model_state["feature_range"]
    )

    x_synth = revert_reshape_arr(x_synth)

    # Add timestamps
    idx = model_state["dfIdx"][: model_state["dfIdx"].get_loc(0)]
    x_synth = x_synth[: len(idx)]
    x_synth = np.append(idx.to_numpy().reshape(-1, 1), x_synth, axis=1)

    df_x_synth = pd.DataFrame(x_synth).set_index(0)

    return df_x_synth
