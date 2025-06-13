import io
from typing import Union

import numpy as np
import torch
import torch.nn as nn
import zstandard as zstd

from moderate_api.notebooks.synthethic_load.model.data_manip import (
    invert_min_max_scaler,
    revert_reshape_arr,
)

# Global constants
FEATURE_RANGE = (-1, 1)


class Generator(nn.Module):
    def __init__(self, model):
        super(Generator, self).__init__()
        # Handle both list of layers and already constructed Sequential
        if isinstance(model, (list, tuple)):
            self.model = nn.Sequential(*model)
        else:
            self.model = model

    def forward(self, noise):
        return self.model(noise)


def generate_data_from_saved_model(
    modelStatePath: Union[str, io.BytesIO], n_profiles=None
):
    """
    Generate synthetic data from a saved model.

    Args:
        modelStatePath: Path to the saved model file (str) or BytesIO object with model data
        n_profiles: Number of profiles to generate (optional)

    Returns:
        numpy.ndarray: Generated synthetic data
    """
    try:
        # Determine the appropriate device and map_location
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        map_location = None if torch.cuda.is_available() else "cpu"

        # Handle different input types
        if isinstance(modelStatePath, str):
            # File path - load directly
            modelState = torch.load(
                modelStatePath, weights_only=False, map_location=map_location
            )
        elif isinstance(modelStatePath, io.BytesIO):
            # BytesIO object - handle potential ZSTD compression
            modelStatePath.seek(0)
            raw_data = modelStatePath.read()
            modelStatePath.seek(0)  # Reset for potential reuse

            # Try ZSTD decompression first
            try:
                dctx = zstd.ZstdDecompressor()
                decompressed_data = dctx.decompress(raw_data)
                with io.BytesIO(decompressed_data) as buffer:
                    modelState = torch.load(
                        buffer, weights_only=False, map_location=map_location
                    )
                print("✅ Successfully decompressed ZSTD model file")
            except Exception:
                # If ZSTD fails, try direct loading
                try:
                    with io.BytesIO(raw_data) as buffer:
                        modelState = torch.load(
                            buffer, weights_only=False, map_location=map_location
                        )
                    print("✅ Loaded uncompressed model file")
                except Exception as e:
                    raise ValueError(f"Failed to load model from BytesIO: {e}")
        else:
            raise ValueError(
                "modelStatePath must be either a string path or io.BytesIO object"
            )

        print(f"Successfully loaded model")
        print(f"📋 Available keys in model state: {list(modelState.keys())}")

        # Try to use the complete saved generator model if available
        if "generator" in modelState:
            print("🔄 Using complete saved generator model")
            Gen = modelState["generator"].to(device)
        elif "gen_model" in modelState:
            print("🔄 Using complete saved gen_model")
            Gen = modelState["gen_model"].to(device)
        else:
            # Fallback to reconstructing from layers and state dict
            print("🔄 Reconstructing generator from layers and state dict")

            # Try different approaches to handle architecture mismatches
            try:
                # First attempt: standard reconstruction
                Gen = Generator(modelState["gen_layers"]).to(device)
                missing_keys, unexpected_keys = Gen.load_state_dict(
                    modelState["gen_state_dict"], strict=False
                )

                if missing_keys:
                    print(
                        f"⚠️  Missing keys ({len(missing_keys)}): {missing_keys[:3]}..."
                    )
                if unexpected_keys:
                    print(
                        f"⚠️  Unexpected keys ({len(unexpected_keys)}): {unexpected_keys[:3]}..."
                    )

                # Check if too many keys are missing (indicating major architecture mismatch)
                if len(missing_keys) > len(unexpected_keys) * 2:
                    raise Exception("Too many missing keys - architecture mismatch")

                print("✅ Model state loaded (with strict=False)")

            except Exception as e:
                print(f"❌ Standard reconstruction failed: {e}")
                print("🔄 Trying alternative approach...")

                # Alternative: Create a minimal generator that can handle the state dict
                try:
                    # Create a simple sequential model from the saved layers
                    if hasattr(modelState["gen_layers"], "children"):
                        # If gen_layers is already a Sequential model
                        Gen = Generator(modelState["gen_layers"]).to(device)
                    else:
                        # If gen_layers is a list/OrderedDict, convert it
                        Gen = Generator(
                            list(modelState["gen_layers"].values())
                            if hasattr(modelState["gen_layers"], "values")
                            else modelState["gen_layers"]
                        ).to(device)

                    # Try to load state dict again
                    Gen.load_state_dict(modelState["gen_state_dict"], strict=False)
                    print("✅ Alternative model loading successful")

                except Exception as e2:
                    print(f"❌ Alternative approach also failed: {e2}")
                    raise Exception(
                        f"Could not load model - tried multiple approaches. Original error: {e}"
                    )

        # Use n_profiles if specified, otherwise use the original profileCount
        profile_count = (
            n_profiles if n_profiles is not None else modelState["profileCount"]
        )

        # Generate data in smaller batches to save memory
        batch_size = 32  # Adjust this based on your available memory
        num_batches = (profile_count + batch_size - 1) // batch_size
        xSynth_list = []

        with torch.no_grad():  # No need to track gradients during generation
            for i in range(num_batches):
                start_idx = i * batch_size
                end_idx = min((i + 1) * batch_size, profile_count)
                current_batch_size = end_idx - start_idx

                noise = torch.randn(
                    current_batch_size, modelState["dimNoise"], 1, 1, device=device
                )
                xSynth_batch = Gen(noise)
                xSynth_batch = xSynth_batch.cpu().numpy()  # Move to CPU immediately
                xSynth_list.append(xSynth_batch)

                # Free memory
                if device.type == "cuda":
                    torch.cuda.empty_cache()

        # Combine batches
        xSynth = np.vstack(xSynth_list)
        xSynth = invert_min_max_scaler(xSynth, modelState["minMax"], FEATURE_RANGE)
        xSynth = revert_reshape_arr(xSynth)
        idx = modelState["dfIdx"][: modelState["dfIdx"].get_loc("#####0")]
        xSynth = xSynth[: len(idx)]
        xSynth = np.append(idx.to_numpy().reshape(-1, 1), xSynth, axis=1)
        return xSynth
    except Exception as e:
        print(f"Error loading model: {e}")
        raise
