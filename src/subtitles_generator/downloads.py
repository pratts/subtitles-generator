"""
Models are downloaded by the libraries on first use, each with its own progress bar named after a file
(model.bin, f7e0c4bc.safetensors). Say what is downloaded before it starts, so a first run does not look stuck.
"""
import os

# transformers loads a model that only has pytorch_model.bin (the Japanese aligner), then downloads a
# converted copy (1.3 GB) in a background thread that keeps the run going after it is done; it is never used
os.environ.setdefault("DISABLE_SAFETENSORS_CONVERSION", "true")


def announce(what: str, cached: bool):
    if not cached:
        print(f"⬇️ Downloading {what} (first run only)...")


def hf_cached(repo_id: str) -> bool:
    """Whether a Hugging Face model is in the local cache (HF_HOME)."""
    from huggingface_hub import snapshot_download
    from huggingface_hub.errors import LocalEntryNotFoundError

    try:
        snapshot_download(repo_id, local_files_only=True)
        return True
    except LocalEntryNotFoundError:
        return False


def torch_hub_cached(filename: str) -> bool:
    """Whether a file downloaded with torch.hub (torchaudio's aligners) is in its cache (TORCH_HOME)."""
    import torch

    return os.path.exists(os.path.join(torch.hub.get_dir(), "checkpoints", os.path.basename(filename)))
