# Complete inspected upstream function bodies

These are source evidence, not executable production changes or proof of live availability.

## annotate_celltype_with_panhumanpy (reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/genomics.py:600-795)

```python
def annotate_celltype_with_panhumanpy(
    adata_path,
    feature_names_col=None,
    refine=True,
    umap=True,
    output_dir="./output",
):
    """Perform hierarchical cell type annotation using panhumanpy and Azimuth Neural Network.

    This function implements the panhumanpy workflow for cell type annotation using the
    Azimuth Neural Network, providing hierarchical cell type labels with confidence scores.

    Parameters
    ----------
    adata_path : str
        Path to the AnnData file containing scRNA-seq data
    feature_names_col : str, optional
        Column name in adata.var containing gene names (default: None, uses index)
    refine : bool, optional
        Whether to perform label refinement for consistent granularity (default: True)
    umap : bool, optional
        Whether to generate ANN embeddings and UMAP (default: True)
    output_dir : str, optional
        Directory to save results (default: "./output")

    Returns
    -------
    str
        Research log summarizing the analysis steps and results

    Notes
    -----
    Performance is not ensured for diseased and/or non-human cells.
    """
    import json
    import shutil
    import subprocess
    import tempfile

    def conda_env_exists(env_name):
        try:
            result = subprocess.run(["conda", "env", "list"], capture_output=True, text=True, check=True)
            return any(env_name in line.split() for line in result.stdout.splitlines())
        except Exception:
            return False

    def create_panhumanpy_env(env_name):
        # Create env and install panhumanpy
        subprocess.run(["conda", "create", "-y", "-n", env_name, "python=3.10"], check=True)
        # Install panhumanpy in the new env
        subprocess.run(
            ["conda", "run", "-n", env_name, "pip", "install", "git+https://github.com/satijalab/panhumanpy.git"],
            check=True,
        )

    PANHUMANPY_ENV = "panhumanpy_env"

    # 1. Check/create panhumanpy_env
    if not conda_env_exists(PANHUMANPY_ENV):
        create_panhumanpy_env(PANHUMANPY_ENV)

    # 2. Write a temp script to run in the panhumanpy_env
    temp_dir = tempfile.mkdtemp()
    script_path = os.path.join(temp_dir, "run_panhumanpy.py")
    result_path = os.path.join(temp_dir, "result.json")
    with open(script_path, "w") as f:
        f.write(
            f"""
import os
import sys
import json
import numpy as np
import scanpy as sc
import pandas as pd
try:
    import panhumanpy as ph
except ImportError as e:
    with open(r'{result_path}', 'w') as out:
        out.write(json.dumps({{"error": str(e)}}))
    sys.exit(1)

adata_path = r'''{adata_path}'''
feature_names_col = {repr(feature_names_col)}
refine = {refine}
umap = {umap}
output_dir = r'''{output_dir}'''
log = []
try:
    os.makedirs(output_dir, exist_ok=True)
    log.append("# Performing cell type annotation with Panhuman Azimuth")
    log.append(f"Loading object from: {{adata_path}}")
    adata = sc.read_h5ad(adata_path)
    log.append(f"✓ Successfully loaded object with {{adata.n_obs}} cells and {{adata.n_vars}} genes")
    if feature_names_col is None:
        log.append("Using gene names from adata.var.index")
    else:
        log.append(f"Using gene names from column: {{feature_names_col}}")
        if feature_names_col not in adata.var.columns:
            log.append(f"⚠ Warning: Column '{{feature_names_col}}' not found in adata.var")
            log.append(f"Available columns: {{list(adata.var.columns)}}")
            log.append("Falling back to index")
            feature_names_col = None
    if feature_names_col is None:
        azimuth = ph.AzimuthNN(adata)
    else:
        azimuth = ph.AzimuthNN(adata, feature_names_col=feature_names_col)
    cell_metadata = azimuth.cells_meta
    log.append("✓ Successfully annotated all cells")
    if umap:
        log.append("## Generating ANN embeddings")
        try:
            embeddings = azimuth.azimuth_embed()
        except Exception as e:
            log.append(f"✗ Error generating embeddings: {{str(e)}}")
            with open(r'{result_path}', 'w') as out:
                out.write(json.dumps({{"log": log}}))
            sys.exit(0)
        log.append("## Calculating UMAP")
        try:
            azimuth.azimuth_umap()
            log.append("✓ Generated UMAP of ANN embeddings")
        except Exception as e:
            log.append(f"✗ Error generating UMAP: {{str(e)}}")
            with open(r'{result_path}', 'w') as out:
                out.write(json.dumps({{"log": log}}))
            sys.exit(0)
    else:
        log.append("## Skipping embeddings and UMAP generation")
        embeddings = None
        umap = None
    if refine:
        log.append("## Performing label refinement")
        try:
            azimuth.azimuth_refine()
            cell_metadata = azimuth.cells_meta
            refined_columns = [col for col in cell_metadata.columns if col.startswith("azimuth_")]
            log.append(f"✓ Applied label refinement, results are in columns: {{refined_columns}}")
        except Exception as e:
            log.append(f"✗ Error during label refinement: {{str(e)}}")
    log.append("## Saving results")
    try:
        metadata_file = f"{output_dir}/annotated_cell_metadata.csv"
        cell_metadata.to_csv(metadata_file)
        log.append(f"✓ Saved cell metadata to: {{metadata_file}}")
        if umap and embeddings is not None:
            embeddings_file = f"{output_dir}/ann_embeddings.npy"
            np.save(embeddings_file, embeddings)
            log.append(f"✓ Saved embeddings to: {{embeddings_file}}")
            umap_file = f"{output_dir}/ann_umap.npy"
            np.save(umap_file, umap)
            log.append(f"✓ Saved UMAP to: {{umap_file}}")
        else:
            log.append("Skipped saving embeddings and UMAP (umap=False)")
        annotated_save_path = f"{output_dir}/annotated_obj.h5ad"
        azimuth.pack_adata(save_path=annotated_save_path)
        log.append(f"✓ Saved annotated object to: {{annotated_save_path}}")
    except Exception as e:
        log.append(f"✗ Error saving results: {{str(e)}}")
        with open(r'{result_path}', 'w') as out:
            out.write(json.dumps({{"log": log}}))
        sys.exit(0)
    log.append(f"- All results saved to: {output_dir}")
    with open(r'{result_path}', 'w') as out:
        out.write(json.dumps({{"log": log}}))
except Exception as e:
    with open(r'{result_path}', 'w') as out:
        out.write(json.dumps({{"error": str(e)}}))
    sys.exit(1)
"""
        )

    # 3. Run the script in the panhumanpy_env
    try:
        run_cmd = ["conda", "run", "-n", PANHUMANPY_ENV, "python", script_path]
        subprocess.run(run_cmd, check=True)
    except subprocess.CalledProcessError as e:
        shutil.rmtree(temp_dir)
        return f"Error running panhumanpy in conda env: {e}"

    # 4. Read the result
    try:
        with open(result_path) as f:
            result = json.load(f)
        if "log" in result:
            log = result["log"]
        elif "error" in result:
            log = [f"Error: {result['error']}"]
        else:
            log = ["Unknown error running panhumanpy script."]
    except Exception as e:
        log = [f"Error reading result: {e}"]

    # 5. Clean up temp files
    shutil.rmtree(temp_dir)

    return "\n".join(log)
```

## create_scvi_embeddings_scRNA (reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/genomics.py:801-839)

```python
def create_scvi_embeddings_scRNA(adata_filename, batch_key, label_key, data_dir):
    # Import scvi-tools correctly - the package name is still 'scvi' when installed
    try:
        import scvi
    except ImportError:
        return "Please install scvi-tools: pip install scvi-tools"

    steps = []
    steps.append(f"Loading AnnData from {data_dir}/{adata_filename}")
    adata = sc.read_h5ad(f"{data_dir}/{adata_filename}")

    steps.append(f"Setting up AnnData for scVI with batch key: {batch_key}")
    scvi.model.SCVI.setup_anndata(adata, batch_key=batch_key)

    steps.append("Creating and training scVI model")
    model = scvi.model.SCVI(adata)
    model.train()

    steps.append("Generating latent representation using scVI")
    adata.obsm["X_scVI"] = model.get_latent_representation()

    steps.append(f"Creating scANVI model with label key: {label_key}")
    lvae = scvi.model.SCANVI.from_scvi_model(
        model,
        adata=adata,
        labels_key=label_key,
        unlabeled_category="Unknown",
    )
    steps.append("Training scANVI model")
    lvae.train()

    steps.append("Generating latent representation using scANVI")
    adata.obsm["X_scANVI"] = lvae.get_latent_representation(adata)

    output_filename = f"{data_dir}/scvi_emb_data.h5ad"
    adata.write(output_filename)
    steps.append(f"Saving AnnData with scVI and scANVI embeddings to {output_filename}")

    return "\n".join(steps)
```

## create_harmony_embeddings_scRNA (reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/genomics.py:842-857)

```python
def create_harmony_embeddings_scRNA(adata_filename, batch_key, data_dir):
    # https://pypi.org/project/harmony-pytorch/
    from harmony import harmonize

    steps = []
    steps.append(f"Loading AnnData from {data_dir}/{adata_filename}")
    adata = sc.read_h5ad(f"{data_dir}/{adata_filename}")

    steps.append(f"Running Harmony integration with batch key: {batch_key}")
    adata.obsm["X_harmony"] = harmonize(adata.obsm["X_pca"], adata.obs, batch_key=batch_key)

    output_filename = f"{data_dir}/harmony_emb_data.h5ad"
    steps.append(f"Saving the Harmony embeddings to {output_filename}.")
    adata.write(output_filename)

    return "\n".join(steps)
```

## get_uce_embeddings_scRNA (reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/genomics.py:861-911)

```python
def get_uce_embeddings_scRNA(
    adata_filename,
    data_dir,
    DATA_ROOT="/dfs/project/bioagentos/data/singlecell/",
    custom_args=None,
):
    """The UCE embeddings are usually our default tools to get cell embeddings, we map UCE embeddings to IMA referece dataset and get the cell types for a better understanding.
    The custom_args is a list of strings that will be passed as command line arguments to the UCE script,
    like ["--adata_path", adata_file, "--dir", output_dir]. The default value is None.
    """
    import sys

    steps = []

    try:
        from eval_single_anndata import main, parse_args_uce

        steps.append("Successfully imported UCE main function")
    except Exception:
        steps.append("Please install the UCE package first. Follow https://github.com/snap-stanford/UCE.git.")
        return "\n".join(steps)

    from accelerate import Accelerator

    _base_name = os.path.basename(adata_filename).split(".")[0]
    adata_file_proc = f"{data_dir}/{_base_name}_uce_adata.h5ad"
    if os.path.exists(adata_file_proc):
        steps.append(f"{adata_file_proc} already exists, skipping. The UCE embeddings are stored as adata.obs['X_uce']")
        return "\n".join(steps)

    uce_dir = f"{DATA_ROOT}/UCE"
    sys.path.append(uce_dir)
    steps.append(f"Added {uce_dir} to sys.path")

    # Prepare and parse arguments
    if custom_args is None:
        custom_args = []
    custom_args.extend(["--adata_path", f"{data_dir}/{adata_filename}", "--dir", f"{data_dir}/uce/"])
    parsed_args = parse_args_uce(custom_args)
    steps.append(f"Parsed arguments: {vars(parsed_args)}")

    # Initialize Accelerator
    accelerator = Accelerator(project_dir=parsed_args.dir)
    steps.append("Initialized Accelerator")

    # Run UCE main function
    main(parsed_args, accelerator)
    steps.append("UCE main function completed successfully.")
    steps.append(f"{adata_file_proc} is saved, the UCE embeddings are stored as adata.obs['X_uce']")

    return "\n".join(steps)
```

## map_to_ima_interpret_scRNA (reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/genomics.py:914-971)

```python
def map_to_ima_interpret_scRNA(adata_filename, data_dir, custom_args=None):
    """Map cell embeddings from the input dataset to the Integrated Megascale Atlas reference dataset using UCE embeddings."""
    from sklearn.neighbors import NearestNeighbors

    steps = []
    steps.append(f"Loading AnnData from {data_dir}/{adata_filename}")
    adata = sc.read_h5ad(f"{data_dir}/{adata_filename}")

    if "X_uce" not in adata.obsm:
        raise ValueError("Error: adata.obsm['X_uce'] not found. Please run get_uce_embeddings() first.")

    steps.append("adata.obs['X_uce'] found. Proceeding with cell type mapping.")

    IMA_adata = sc.read_h5ad(f"{data_dir}/uce_10000_per_dataset_33l_8ep_coarse_ct.h5ad")
    steps.append("Loaded Integrated Megascale Atlas (IMA) reference dataset")

    if adata.obsm["X_uce"].shape[1] != IMA_adata.X.shape[1]:
        raise ValueError("UCE embedding dimensions do not match between datasets.")

    # Create a NearestNeighbors object
    n_neighbors = custom_args.get("n_neighbors", 3)
    metric = custom_args.get("metric", "euclidean")
    nn = NearestNeighbors(n_neighbors=n_neighbors, metric=metric)
    nn.fit(IMA_adata.X)

    # Find the nearest neighbors for each cell in adata
    distances, indices = nn.kneighbors(adata.obsm["X_uce"])

    # Extract cell types of the nearest neighbors
    mapped_cell_types = IMA_adata.obs["coarse_cell_type_yanay"].iloc[indices.flatten()].values

    # from umap import UMAP
    if n_neighbors > 1:
        # Implement majority voting

        def custom_mode(x):
            unique, counts = np.unique(x, return_counts=True)
            return unique[np.argmax(counts)]

        mapped_cell_types = np.apply_along_axis(custom_mode, 1, mapped_cell_types.reshape(-1, n_neighbors))

    # Add mapped cell types and confidence scores to adata
    adata.obs["mapped_cell_type"] = mapped_cell_types
    adata.obs["mapping_confidence"] = 1 / (1 + distances.mean(axis=1))

    steps.append("Mapped cell types based on nearest neighbors in UCE space")
    steps.append("Mapped cell types and confidence scores added to adata.obs")

    # Generate summary statistics
    mapping_summary = adata.obs["mapped_cell_type"].value_counts().to_dict()
    steps.append(f"Mapping summary: {mapping_summary}")

    # Save the updated adata object
    output_filename = f"{data_dir}/adata_with_mapped_celltypes.h5ad"
    adata.write_h5ad(output_filename, compression="gzip")
    steps.append(f"Updated adata saved to {output_filename}")

    return "\n".join(steps)
```

## unsupervised_celltype_transfer_between_scRNA_datasets (reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/genomics.py:18-105)

```python
def unsupervised_celltype_transfer_between_scRNA_datasets(
    path_to_annotated_h5ad: str,
    path_to_not_annotated_h5ad: str,
    ref_labels_key: str,
    query_batch_key: str = None,
    ref_batch_key: str = None,
    CELLTYPIST=False,
    KNN_BBKNN=False,
    KNN_HARMONY=False,
    KNN_SCANORAMA=False,
    KNN_SCVI=False,
    ONCLASS=False,
    Random_Forest=False,
    SCANVI_POPV=True,
    Support_Vector=False,
    XGboost=False,
    n_jobs: int = 1,
    output_folder: str = "./tmp/",
    n_samples_per_label: int = 10,
):
    import os

    import scanpy as sc

    os.environ["PYTHONUTF8"] = "1"
    import popv

    steps = []
    steps.append("Starting unsupervised cell type transfer using popV")

    steps.append(f"Loading reference annotated dataset from: {path_to_annotated_h5ad}")
    ref_adata = sc.read_h5ad(path_to_annotated_h5ad)
    steps.append(f"Reference annotated dataset loaded: {ref_adata.n_obs} cells, {ref_adata.n_vars} genes")

    steps.append(f"Loading not annotated query dataset from: {path_to_not_annotated_h5ad}")
    query_adata = sc.read_h5ad(path_to_not_annotated_h5ad)
    steps.append(f"query dataset loaded: {query_adata.n_obs} cells, {query_adata.n_vars} genes")

    # this is required for scvi/scanvi based classifier
    ref_adata.layers["counts"] = ref_adata.X.copy()
    query_adata.layers["counts"] = query_adata.X.copy()

    popv.settings.n_jobs = n_jobs
    output_folder = output_folder
    os.makedirs(output_folder, exist_ok=True)
    steps.append(f"Created output folder: {output_folder}")

    steps.append("Processing query dataset for annotation with popV")
    adata = popv.preprocessing.Process_Query(
        query_adata,
        ref_adata,
        ref_labels_key=ref_labels_key,
        query_batch_key=query_batch_key,
        ref_batch_key=ref_batch_key,
        save_path_trained_models=output_folder,
        cl_obo_folder=False,
        prediction_mode="retrain",
    ).adata

    # passing arugments this way decreases chance of LLM generation and parsing errors
    flags = {
        "CELLTYPIST": CELLTYPIST,
        "KNN_BBKNN": KNN_BBKNN,
        "KNN_HARMONY": KNN_HARMONY,
        "KNN_SCANORAMA": KNN_SCANORAMA,
        "KNN_SCVI": KNN_SCVI,
        "ONCLASS": ONCLASS,
        "Random_Forest": Random_Forest,
        "SCANVI_POPV": SCANVI_POPV,
        "Support_Vector": Support_Vector,
        "XGboost": XGboost,
    }
    selected_methods = [name for name, val in flags.items() if val]
    if selected_methods:
        steps.append(f"Selected annotation methods: {', '.join(selected_methods)}")
    else:
        steps.append("No annotation methods selected")

    steps.append("Starting annotation with SCANVI_POPV method")
    popv.annotation.annotate_data(
        adata,
        methods=selected_methods,
        save_path=f"{output_folder}/popv_output",
    )

    steps.append(f"Annotation completed. Results saved to: {output_folder}/popv_output/predictions.csv")

    return "\n".join(steps)
```

## generate_embeddings_with_state (reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/genomics.py:2167-2419)

```python
def generate_embeddings_with_state(
    adata_filename,
    data_dir,
    model_folder,
    output_filename=None,
    checkpoint=None,
    embed_key="X_state",
    protein_embeddings=None,
    batch_size=500,
):
    """
    Generate State embeddings for single-cell RNA-seq data using the SE-600M model.

    This function downloads the SE-600M model from Hugging Face, installs required dependencies,
    and generates embeddings for the input AnnData object.

    Parameters:
    -----------
    adata_filename : str
        Name of the input AnnData file (.h5ad format)
    data_dir : str
        Directory containing the input data file
    model_folder : str
        Directory where the SE-600M model will be downloaded and stored
    output_filename : str, optional
        Name of the output file. If None, will use input filename with '_state_embeddings' suffix
    checkpoint : str, optional
        Path to the specific model checkpoint. If None, uses the latest checkpoint in model_folder
    embed_key : str, default="X_state"
        Name of key to store embeddings in the output AnnData object
    protein_embeddings : str, optional
        Path to protein embeddings override (.pt). If omitted, auto-detects in model folder
    batch_size : int, default=500
        Batch size for embedding forward pass. Increase to use more VRAM and speed up embedding

    Returns:
    --------
    str
        Research log summarizing the steps performed and results

    Notes:
    ------
    - Requires 10GB+ GPU memory for model loading
    - Downloads ~25GB model files from Hugging Face
    - Installs git-lfs, uv, and arc-state if not already available
    - Validates input h5ad file format (CSR matrix and gene_name column)
    - Provides real-time streaming output for git clone and embedding generation
    - Includes automatic retry with reduced batch size on failure
    """
    import os
    import subprocess

    # Initialize steps list for logging
    steps = []

    # Set up paths
    input_path = os.path.join(data_dir, adata_filename)
    if output_filename is None:
        base_name = os.path.splitext(adata_filename)[0]
        output_filename = f"{base_name}_state_embeddings.h5ad"

    output_path = os.path.join(data_dir, "output", output_filename)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    steps.append(f"Created output directory: {os.path.dirname(output_path)}")

    # Validate h5ad file format
    steps.append("Validating h5ad file format...")
    try:
        import scanpy as sc

        adata = sc.read_h5ad(input_path)

        import warnings

        if not hasattr(adata.X, "indices"):
            warning_msg = (
                "Input data is not in CSR (Compressed Sparse Row) matrix format. Proceeding, but this may cause issues."
            )
            warnings.warn(warning_msg, stacklevel=2)
            steps.append(f"Warning: {warning_msg}")

        if "gene_name" not in adata.var.columns:
            warning_msg = (
                "'gene_name' column is not present in the var dataframe. Proceeding, but this may cause issues."
            )
            warnings.warn(warning_msg, stacklevel=2)
            steps.append(f"Warning: {warning_msg}")

        steps.append(f"  - Matrix format: {type(adata.X).__name__}")
        steps.append(f"  - Number of cells: {adata.n_obs}")
        steps.append(f"  - Number of genes: {adata.n_vars}")
        steps.append(f"  - Gene names available: {'gene_name' in adata.var.columns}")

    except Exception as e:
        error_msg = f"h5ad file validation failed: {e}"
        steps.append(error_msg)
        raise ValueError(error_msg) from e

    # Check if git-lfs is installed
    steps.append("Checking if git-lfs is installed...")
    try:
        subprocess.run(["git", "lfs", "version"], check=True, capture_output=True)
        steps.append("git-lfs is available")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        error_msg = (
            "git-lfs is not installed or not found in PATH. "
            "Please install git-lfs before running this function.\n"
            "Run the following command with root privileges:\n"
            "sudo apt-get install git-lfs\n"
            "git lfs install"
        )
        steps.append(error_msg)
        raise RuntimeError(error_msg) from e

    steps.append("Downloading SE-600M model...")

    # Check if model weights actually exist (not just the directory)
    model_exists = False
    if os.path.exists(model_folder):
        # Check for SE-600M specific checkpoint files
        checkpoint_indicators = ["se600m_epoch16.ckpt", "se600m_epoch4.ckpt", "model.safetensors", "config.yaml"]
        model_exists = any(os.path.exists(os.path.join(model_folder, indicator)) for indicator in checkpoint_indicators)

    if not model_exists:
        os.makedirs(model_folder, exist_ok=True)
        steps.append(f"Created model directory: {model_folder}")
        try:
            steps.append(f"Cloning SE-600M model to {model_folder}")
            steps.append("This may take a while and final model weights are approx 25GB!...")
            process = subprocess.Popen(
                ["git", "clone", "https://huggingface.co/arcinstitute/SE-600M", model_folder],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            for line in iter(process.stdout.readline, ""):
                line = line.rstrip()
                print(line)
                steps.append(line)

            process.wait()

            if process.returncode != 0:
                raise subprocess.CalledProcessError(
                    process.returncode, ["git", "clone", "https://huggingface.co/arcinstitute/SE-600M", model_folder]
                )
            steps.append("SE-600M model downloaded successfully")
        except subprocess.CalledProcessError as e:
            error_msg = f"Error downloading model: {e}"
            steps.append(error_msg)
            raise
    else:
        steps.append(f"Model already downloaded: {model_folder}")

    steps.append("Generating embeddings...")

    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        current_device = torch.cuda.current_device()
        steps.append(f"✓ GPU detected: {device_name}")
        steps.append(f"✓ GPU memory: {gpu_memory:.1f} GB")
        steps.append(f"✓ Current CUDA device: {current_device}")
        if gpu_memory < 10:
            warning_msg = f"⚠️  WARNING: GPU has only {gpu_memory:.1f} GB memory. SE600 model requires 10GB+ GPU memory."
            steps.append(warning_msg)
    else:
        steps.append("⚠️  WARNING: No GPU detected! This will run on CPU and be very slow.")
        steps.append("⚠️  SE600 model requires 10GB+ GPU memory for optimal performance.")

    cuda_visible = os.environ.get("CUDA_VISIBLE_DEVICES", "Not set")
    steps.append(f"CUDA_VISIBLE_DEVICES: {cuda_visible}")

    steps.append(f"PyTorch CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        steps.append(f"PyTorch CUDA device count: {torch.cuda.device_count()}")
        steps.append(f"PyTorch current device: {torch.cuda.current_device()}")

    steps.append("embedding data can take a while...")
    max_retries = 3
    retries = 0
    last_exception = None

    while retries <= max_retries:
        try:
            cmd = [
                "uv",
                "run",
                "state",
                "emb",
                "transform",
                "--model-folder",
                model_folder,
                "--input",
                input_path,
                "--output",
                output_path,
            ]

            if checkpoint:
                cmd.extend(["--checkpoint", checkpoint])
            if embed_key != "X_state":
                cmd.extend(["--embed-key", embed_key])
            if protein_embeddings:
                cmd.extend(["--protein-embeddings", protein_embeddings])
            if batch_size:
                cmd.extend(["--batch-size", str(batch_size)])

            steps.append(f"Running command: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True
            )

            for line in iter(process.stdout.readline, ""):
                line = line.rstrip()
                print(line)  # Print to console first
                steps.append(line)  # Then add to steps list

            process.wait()

            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd)

            steps.append("Embeddings generated successfully!")
            steps.append("Output Format and Location:")
            steps.append("  Output format: .h5ad (AnnData format)")
            steps.append("  Embeddings stored in: X_state layer (by default)")
            steps.append("  Location: Specified by --output parameter")
            steps.append(f"  In your code: Saved to {output_path}")
            steps.append("")
            return "\n".join(steps)

        except subprocess.CalledProcessError as e:
            error_msg = f"Error generating embeddings (attempt {retries + 1}): {e}"
            steps.append(error_msg)
            last_exception = e
            if batch_size and retries < max_retries:
                batch_size = max(1, batch_size // 2)
                steps.append(f"Retrying with reduced batch size: {batch_size}")
                retries += 1
            else:
                break

    steps.append("Failed to generate embeddings after multiple attempts.")
    if last_exception:
        steps.append(f"Last exception: {last_exception}")
        raise last_exception

    return "\n".join(steps)
```

## generate_transcriptformer_embeddings (reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/genomics.py:2422-2759)

```python
def generate_transcriptformer_embeddings(
    adata_filename: str,
    data_dir: str,
    output_filename: str = None,
    model_type: str = "tf-sapiens",
    checkpoint_path: str = None,
    batch_size: int = 8,
    precision: str = "16-mixed",
    clip_counts: int = 30,
    embedding_layer_index: int = -1,
    num_gpus: int = 1,
    n_data_workers: int = 0,
    gene_col_name: str = "ensembl_id",
    pretrained_embedding: str = None,
    filter_to_vocabs: bool = True,
    use_raw: str = "None",
    emb_type: str = "cell",
    remove_duplicate_genes: bool = False,
    oom_dataloader: bool = False,
) -> str:
    """
    Generate Transcriptformer embeddings for single-cell RNA-seq data.

    Parameters:
    -----------
    adata_filename : str
        Name of the input AnnData file (.h5ad format)
    data_dir : str
        Directory containing the input data file
    output_filename : str, optional
        Name of the output embeddings file. If None, will use input filename with '_transcriptformer_embeddings' suffix
    model_type : str, optional
        Type of transcriptformer model to download and use. Options: "tf-sapiens", "tf-exemplar", "tf-metazoa" (default: "tf-sapiens")
    checkpoint_path : str, optional
        Path to the transcriptformer checkpoint directory. If None, will use "./checkpoints/{model_type}" (default: None)
    batch_size : int, optional
        Batch size for inference (default: 8)
    precision : str, optional
        Precision for inference. Options: "16-mixed", "32" (default: "16-mixed")
    clip_counts : int, optional
        Maximum count value to clip to (default: 30)
    embedding_layer_index : int, optional
        Which layer to extract embeddings from (default: -1, last layer)
    num_gpus : int, optional
        Number of GPUs to use (default: 1)
    n_data_workers : int, optional
        Number of data loading workers (default: 0)
    gene_col_name : str, optional
        Column name in AnnData.var containing gene identifiers (default: "ensembl_id")
    pretrained_embedding : str, optional
        Path to pretrained embeddings for out-of-distribution species (default: None)
    filter_to_vocabs : bool, optional
        Whether to filter genes to only those in the vocabulary (default: True)
    use_raw : str, optional
        Whether to use raw counts from AnnData.raw.X (True), adata.X (False), or auto-detect (None/auto) (default: "None")
    emb_type : str, optional
        Type of embeddings to extract: 'cell' for mean-pooled cell embeddings or 'cge' for contextual gene embeddings (default: "cell")
    remove_duplicate_genes : bool, optional
        Remove duplicate genes if found instead of raising an error (default: False)
    oom_dataloader : bool, optional
        Use map-style out-of-memory DataLoader (DistributedSampler-friendly) (default: False)
    Returns:
    --------
    str
        Path to the generated embeddings file
    """
    import os
    import subprocess

    import pandas as pd
    import scanpy as sc
    import torch

    if checkpoint_path is None:
        checkpoint_path = f"./checkpoints/{model_type}"

    input_path = os.path.join(data_dir, adata_filename)
    if output_filename is None:
        base_name = os.path.splitext(adata_filename)[0]
        output_filename = f"{base_name}_transcriptformer_embeddings.h5ad"

    output_path = os.path.join(data_dir, "output", output_filename)
    temp_data_path = os.path.join(data_dir, "temp_transcriptformer_input.h5ad")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print("Checking GPU availability...")
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        current_device = torch.cuda.current_device()
        print(f"✓ GPU detected: {device_name}")
        print(f"✓ GPU memory: {gpu_memory:.1f} GB")
        print(f"✓ Current CUDA device: {current_device}")
    else:
        print("⚠️  WARNING: No GPU detected! This will run on CPU and be very slow.")
        print("⚠️  Transcriptformer requires GPU for optimal performance.")

    import os

    cuda_visible = os.environ.get("CUDA_VISIBLE_DEVICES", "Not set")
    print(f"CUDA_VISIBLE_DEVICES: {cuda_visible}")

    print(f"PyTorch CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"PyTorch CUDA device count: {torch.cuda.device_count()}")
        print(f"PyTorch current device: {torch.cuda.current_device()}")

    try:
        os.makedirs(checkpoint_path, exist_ok=True)

        def is_model_downloaded(checkpoint_path, model_type):
            """Check if model is already downloaded by looking for key files"""
            required_files = [
                "config.yaml",
                "pytorch_model.bin",
            ]

            for file_name in required_files:
                file_path = os.path.join(checkpoint_path, file_name)
                if not os.path.exists(file_path):
                    return False

            return True

        if is_model_downloaded(checkpoint_path, model_type):
            print(f"✓ Model checkpoints for {model_type} already exist at: {checkpoint_path}")
            print("✓ Skipping download...")
        else:
            print(f"Downloading transcriptformer model checkpoints for {model_type}...")
            print("This may take a while and model checkpoints are several GB!...")
            print(f"Model will be saved to: {checkpoint_path}")

            try:
                process = subprocess.Popen(
                    ["transcriptformer", "download", model_type],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                )

                for line in iter(process.stdout.readline, ""):
                    print(line.rstrip())

                process.wait()

                if process.returncode != 0:
                    raise subprocess.CalledProcessError(
                        process.returncode, ["transcriptformer", "download", model_type]
                    )
                print(f"✓ Model checkpoints for {model_type} downloaded successfully")
            except subprocess.CalledProcessError as e:
                print(f"Error downloading model checkpoints: {e}")
                raise

        print("Loading and preparing AnnData object...")
        try:
            adata = sc.read_h5ad(input_path)
            print(f"✓ Loaded AnnData with {adata.n_obs} cells and {adata.n_vars} genes")

            def check_ensembl_patterns(gene_index):
                patterns = {
                    "human_ensembl": r"^ENSG\d{11}(\.\d+)?$",
                    "mouse_ensembl": r"^ENSMUSG\d{11}(\.\d+)?$",
                    "zebrafish_ensembl": r"^ENSDARG\d{11}(\.\d+)?$",
                    "fly_ensembl": r"^FBgn\d{7}$",
                    "worm_ensembl": r"^WBGene\d{8}$",
                    "yeast_ensembl": r"^Y[A-P][LR]\d{3}[WC]?$",
                    "generic_ensembl": r"^ENS[A-Z]{3}G\d{11}(\.\d+)?$",
                }

                results = {}
                for pattern_name, pattern in patterns.items():
                    matches = gene_index.str.match(pattern, na=False)
                    count = matches.sum()
                    results[pattern_name] = {
                        "count": count,
                        "percentage": (count / len(gene_index)) * 100,
                        "matches": gene_index[matches].tolist()[:5] if count > 0 else [],
                    }

                return results

            print("Analyzing gene index for Ensembl ID patterns...")
            ensembl_analysis = check_ensembl_patterns(adata.var.index)

            for pattern_name, data in ensembl_analysis.items():
                if data["count"] > 0:
                    print(f"✓ {pattern_name}: {data['count']} genes ({data['percentage']:.1f}%)")
                    if data["matches"]:
                        print(f"  Examples: {data['matches']}")

            best_pattern = max(ensembl_analysis.items(), key=lambda x: x[1]["count"])
            if best_pattern[1]["count"] > 0:
                print(f"✓ Best match: {best_pattern[0]} with {best_pattern[1]['count']} genes")
            else:
                print("❌ ERROR: No clear Ensembl ID patterns detected in gene index")
                print(f"  Gene index examples: {adata.var.index[:5].tolist()}")
                print("  This dataset cannot be processed by transcriptformer.")
                print("  Please ensure your data contains valid Ensembl gene IDs.")
                raise ValueError(
                    "No Ensembl ID patterns found in gene index. Cannot proceed with transcriptformer inference."
                )

            if "ensembl_id" not in adata.var.columns:
                if "gene_ids" in adata.var.columns:
                    print("✓ Found 'gene_ids' column, renaming to 'ensembl_id'")
                    adata.var["ensembl_id"] = adata.var["gene_ids"]
                elif best_pattern[1]["count"] > 0:
                    adata.var["ensembl_id"] = adata.var.index
                    print(f"✓ Using gene index as ensembl_id (detected {best_pattern[0]} pattern)")
                else:
                    print("❌ ERROR: No 'ensembl_id' column found and gene index doesn't match Ensembl patterns")
                    print("  This dataset cannot be processed by transcriptformer.")
                    print("  Please ensure your data contains valid Ensembl gene IDs.")
                    raise ValueError("No valid Ensembl gene IDs found. Cannot proceed with transcriptformer inference.")

            if adata.raw is None:
                print("⚠️  Warning: Transcriptformer expects raw (unnormalized) count data in adata.X.")
                if not pd.api.types.is_integer_dtype(adata.X.dtype):
                    print("⚠️  Warning: adata.X does not appear to be unnormalized counts (integer type not detected).")
                adata.raw = adata
                print("✓ Set adata.raw to current adata")

            if remove_duplicate_genes:
                print("Pre-processing: Removing duplicate genes to prevent dimension mismatch...")
                adata.var["ensembl_id_clean"] = adata.var["ensembl_id"].str.split(".").str[0]

                duplicate_mask = adata.var["ensembl_id_clean"].duplicated(keep="first")
                n_duplicates = duplicate_mask.sum()

                if n_duplicates > 0:
                    print(f"Found {n_duplicates} duplicate genes, removing them...")
                    adata = adata[:, ~duplicate_mask].copy()
                    print(f"✓ Removed {n_duplicates} duplicate genes. Remaining: {adata.n_vars} genes")
                else:
                    print("✓ No duplicate genes found")

                adata.var["ensembl_id"] = adata.var["ensembl_id_clean"]
                adata.var.drop("ensembl_id_clean", axis=1, inplace=True)

            adata.write(temp_data_path)
            print(f"✓ Saved prepared AnnData to {temp_data_path}")

        except Exception as e:
            print(f"Error preparing AnnData object: {e}")
            raise

        print("Running transcriptformer inference...")
        print("This may take a while depending on data size and GPU...")
        try:
            cmd = [
                "transcriptformer",
                "inference",
                "--checkpoint-path",
                checkpoint_path,
                "--data-file",
                temp_data_path,
                "--output-path",
                os.path.dirname(output_path),
                "--output-filename",
                os.path.basename(output_path),
                "--batch-size",
                str(batch_size),
                "--gene-col-name",
                gene_col_name,
                "--precision",
                precision,
                "--clip-counts",
                str(clip_counts),
                "--model-type",
                "transcriptformer",
                "--use-raw",
                use_raw,
                "--emb-type",
                emb_type,
                "--num-gpus",
                str(num_gpus),
                "--n-data-workers",
                str(n_data_workers),
            ]

            # Check if assay column exists in obs, if not create it
            if "assay" not in adata.obs.columns:
                print("✓ Creating 'assay' column in obs metadata with 'unknown' values")
                adata.obs["assay"] = "unknown"
                # Save the updated adata with assay column
                adata.write(temp_data_path)
                print(f"✓ Updated AnnData saved to {temp_data_path}")

            if pretrained_embedding is not None:
                cmd.extend(["--pretrained-embedding", pretrained_embedding])

            if filter_to_vocabs:
                cmd.append("--filter-to-vocabs")

            if remove_duplicate_genes:
                cmd.append("--remove-duplicate-genes")

            if oom_dataloader:
                cmd.append("--oom-dataloader")

            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True
            )

            for line in iter(process.stdout.readline, ""):
                print(line.rstrip())

            process.wait()

            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd)

            print("✓ Transcriptformer inference completed successfully")
            print(f"✓ Output saved to: {output_path}")

        except subprocess.CalledProcessError as e:
            print(f"Error running transcriptformer inference: {e}")
            raise

        try:
            if os.path.exists(temp_data_path):
                os.remove(temp_data_path)
                print("✓ Cleaned up temporary files")
        except Exception as e:
            print(f"⚠️  Warning: Could not clean up temporary files: {e}")

        print("✓ Transcriptformer embeddings generated successfully!")
        print("\nOutput Format and Location:")
        print("  Output format: .h5ad (AnnData format)")

        return output_path

    except Exception as e:
        print(f"Fatal error in transcriptformer embedding generation: {e}")
        raise
```

## generate_gene_embeddings_with_ESM_models (reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/genomics.py:314-460)

```python
def generate_gene_embeddings_with_ESM_models(
    ensembl_gene_ids: list[str],
    model_name: str = "esm2_t6_8M_UR50D",
    layer: int = 6,
    save_path: str | None = None,
    batch_size: int = 1,
    max_sequence_length: int = 1024,
) -> str:
    """
    Generate average protein embeddings for a list of Ensembl gene IDs.
    Memory-friendly implementation with rolling averages and small batch processing.
    Embeddings are automatically saved to disk with a default filename if no save_path is provided.

    Args:
        ensembl_gene_ids: List of Ensembl gene IDs (e.g., ["ENSG00000012048", ...])
        model_name: ESM model name to use (default: "esm2_t6_8M_UR50D")
        layer: Which layer to extract embeddings from (default: 6)
        save_path: Optional path to save embeddings as PyTorch dict. If None, uses default filename
                  format: "esm_embeddings_{model_name}_{gene_list}.pt" (default: None)
        batch_size: Number of sequences to process at once (default: 1)
        max_sequence_length: Maximum sequence length to process (default: 1024)

    Returns:
        String containing the steps performed during the embedding generation process
    """
    steps = []
    steps.append(f"Loading ESM model: {model_name}")
    # model loading take a while, once loaded for smaller models generation is relatively fast
    # running bilion model ESM models require FSDP or GPUs with 80 GB of memory
    model, alphabet = esm.pretrained.load_model_and_alphabet(model_name)
    batch_converter = alphabet.get_batch_converter()
    model.eval()

    # Move model to GPU if available
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    steps.append(f"Using device: {device}")

    steps.append("Fetching protein isoform sequences...")
    ensembl_gene_isoforms_map: dict[str, list[str]] = {}
    for ensembl_id in tqdm(ensembl_gene_ids, desc="Fetching sequences"):
        isoform_sequences = _fetch_isoform_sequences(ensembl_id)
        # Filter sequences by length to avoid memory issues
        filtered_sequences = [seq for seq in isoform_sequences if len(seq) <= max_sequence_length]
        if filtered_sequences:
            ensembl_gene_isoforms_map[ensembl_id] = filtered_sequences
        else:
            steps.append(f"  No sequences under {max_sequence_length} residues found for gene {ensembl_id}")

    # Prepare all data for processing
    all_data: list[tuple[str, str]] = []
    for gene, isoform_seqs in ensembl_gene_isoforms_map.items():
        for i, seq in enumerate(isoform_seqs):
            all_data.append((f"{gene}_isoform_{i}", seq))

    steps.append(f"Processing {len(all_data)} sequences in batches of {batch_size}")

    # Rolling average tracking
    gene_embeddings: dict[str, list[torch.Tensor]] = {}
    gene_avg_embedding: dict[str, np.ndarray] = {}

    # Process in small batches to avoid memory issues
    for i in tqdm(range(0, len(all_data), batch_size), desc="Processing ESM embeddings"):
        batch_data = all_data[i : i + batch_size]

        try:
            batch_labels, batch_strs, batch_tokens = batch_converter(batch_data)
            batch_tokens = batch_tokens.to(device)
            batch_lens: torch.Tensor = (batch_tokens != alphabet.padding_idx).sum(1)

            steps.append(f"  Running ESM model on batch {i // batch_size + 1}...")
            with torch.no_grad():
                results = model(batch_tokens, repr_layers=[layer], return_contacts=False)
            token_representations: torch.Tensor = results["representations"][layer]

            # Process each sequence in the batch
            for j, tokens_len in enumerate(batch_lens):
                # Extract gene name from label (remove _isoform_X suffix)
                gene_name = batch_labels[j].split("_isoform_")[0]

                # Get sequence embedding (excluding BOS/EOS tokens)
                sequence_embedding = token_representations[j, 1 : tokens_len - 1].mean(0).detach().cpu()

                # Store embedding for this gene
                if gene_name not in gene_embeddings:
                    gene_embeddings[gene_name] = []
                gene_embeddings[gene_name].append(sequence_embedding)

        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                steps.append(f"  Memory error on batch {i // batch_size + 1}, reducing batch size...")
                # Clear cache and try with smaller batch
                torch.cuda.empty_cache() if torch.cuda.is_available() else None
                # Process this batch one by one
                for single_item in batch_data:
                    try:
                        single_batch_labels, single_batch_strs, single_batch_tokens = batch_converter([single_item])
                        single_batch_tokens = single_batch_tokens.to(device)
                        single_batch_lens: torch.Tensor = (single_batch_tokens != alphabet.padding_idx).sum(1)

                        with torch.no_grad():
                            single_results = model(single_batch_tokens, repr_layers=[layer], return_contacts=False)
                        single_token_representations: torch.Tensor = single_results["representations"][layer]

                        gene_name = single_item[0].split("_isoform_")[0]
                        sequence_embedding = (
                            single_token_representations[0, 1 : single_batch_lens[0] - 1].mean(0).detach().cpu()
                        )

                        if gene_name not in gene_embeddings:
                            gene_embeddings[gene_name] = []
                        gene_embeddings[gene_name].append(sequence_embedding)

                    except Exception as single_e:
                        steps.append(f"    Failed to process {single_item[0]}: {str(single_e)}")
            else:
                steps.append(f"  Error processing batch {i // batch_size + 1}: {str(e)}")

    # Compute final averages for each gene
    steps.append("Computing final gene embeddings...")
    for gene, embeddings in gene_embeddings.items():
        if embeddings:
            # Stack all embeddings for this gene and compute mean
            stacked_embeddings = torch.stack(embeddings, dim=0)
            avg_embedding = stacked_embeddings.mean(dim=0).numpy()
            gene_avg_embedding[gene] = avg_embedding
            steps.append(f"  Gene {gene}: averaged {len(embeddings)} isoform embeddings")
        else:
            steps.append(f"  Gene {gene}: no valid embeddings found")

    # Use default save path if none provided
    if save_path is None:
        gene_list_str = "_".join(ensembl_gene_ids[:3])  # Use first 3 genes for filename
        if len(ensembl_gene_ids) > 3:
            gene_list_str += f"_and_{len(ensembl_gene_ids) - 3}_more"
        save_path = f"esm_embeddings_{model_name}_{gene_list_str}.pt"

    save_dir = Path(save_path).parent
    save_dir.mkdir(parents=True, exist_ok=True)

    torch_embeddings = {gene_id: torch.from_numpy(embedding) for gene_id, embedding in gene_avg_embedding.items()}

    torch.save(torch_embeddings, save_path)
    steps.append(f"Embeddings saved to: {os.path.abspath(save_path)}")
    steps.append(f"File size: {os.path.getsize(save_path) / (1024 * 1024):.2f} MB")

    return "\n".join(steps)
```

## _fetch_isoform_sequences (reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/genomics.py:284-311)

```python
def _fetch_isoform_sequences(ensembl_gene_id: str) -> list[str]:
    """
    this is not registered as a tool
    Fetch all protein isoform FASTA sequences for a given Ensembl gene ID.
    Returns a list of protein sequences (strings) for each isoform, or an empty list if not found.
    For ENSG00000012048, removes the sequence with header containing 'ENSP00000420781.2'.

    Args:
        ensembl_gene_id: Ensembl gene identifier (e.g., "ENSG00000012048")

    Returns:
        List of protein sequences as strings
    """
    url = f"https://rest.ensembl.org/sequence/id/{ensembl_gene_id}?type=protein;multiple_sequences=1"
    headers = {"Content-Type": "text/x-fasta"}
    response = requests.get(url, headers=headers)
    if not response.ok or not response.text.startswith(">"):
        return []
    sequences = []
    fasta_entries = response.text.strip().split(">")
    for entry in fasta_entries:
        if not entry.strip():
            continue
        lines = entry.strip().splitlines()
        lines[0]
        sequence = "".join(lines[1:])
        sequences.append(sequence)
    return sequences
```
