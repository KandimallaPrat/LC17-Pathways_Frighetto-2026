"""
Fetching partners of LC17 neurons from neuPrint

Runs over both datasets (hemibrain and male-CNS) in a single call and writes
one parquet per dataset into ../Data/Partners/ so the two can be compared.

"""

import os
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import connectome_analysis
import neuprint
from neuprint import NeuronCriteria as NC

#------------------------------------------------------------------------------
token = os.environ["HEMIBRAIN_TOKEN"]

# Working on datasets
datasets = ["hemibrain:v1.2.1", "male-cns:v1.0"]
names    = ["hemibrain", "malecns"]

OUT_DIR = "Data/Partners"

#------------------------------------------------------------------------------
def fetch_partners(name, dataset, min_weight = 1):
    """
    Fetch all LC17 outputs from a single neuPrint dataset and save them.

    Parameters
    ----------
    name : string
        Short name of the dataset, used in the output filename.

    dataset : string
        Dataset name and release version.

    Returns
    -------
    conn_df : DataFrame
        The grouped connectivity table for this dataset.

    """
    analysis = connectome_analysis.neuPrintConnect(
        token   = token,
        server  = 'neuprint.janelia.org',
        dataset = dataset)

    # A client per dataset stays alive across the loop, so neuPrint stops
    # picking one on its own. Point it at the dataset we're working on.
    neuprint.set_default_client(analysis.client)

    #--------------------------------------------------------------------------
    lc17_criteria = NC(instance = "LC17.*", regex = True)

    #--------------------------------------------------------------------------
    # Fetching all their outputs
    conn_df, _ = analysis.connectivity(
                            lc17_criteria,
                            min_weight = min_weight,
                            render     = False)

    # Group
    conn_df = conn_df.groupby(["bodyId_pre", "bodyId_post",
                               "instance_pre", "instance_post",
                               "type_pre", "type_post"])[
                                "weight"].sum().reset_index()

    # Keep track of where each row came from once they get combined
    conn_df["dataset"] = name

    # For hemibrain make a tiny fix
    if name == "hemibrain":
        conn_df["instance_pre"] = "LC17_R"

    # Save it
    os.makedirs(OUT_DIR, exist_ok = True)
    out_path = os.path.join(OUT_DIR, f"{name}_LC17_all-outputs.parquet")
    conn_df.to_parquet(out_path,
                       index  = False,
                       engine = "pyarrow")

    print(f"{name} : {len(conn_df)} connections -> {out_path}")

    # Group the connections by treating the entire LC17 population as a unit
    output_df = conn_df.groupby(["instance_pre",
                                 "bodyId_post", "instance_post",
                                 "type_post"])["weight"].sum().reset_index()

    # Save it
    out_path = os.path.join(OUT_DIR, f"{name}_LC17_population-outputs.parquet")
    output_df.to_parquet(out_path,
                         index  = False,
                         engine = "pyarrow")
    print(f"{name} : {len(output_df)} connections -> {out_path}\n")

    #--------------------------------------------------------------------------
    # Fetching recurrent connections
    criteria = NC(bodyId = np.unique(conn_df["bodyId_post"]))

    # Fetch recurrent
    rec_df, _ = analysis.connectivity(
                                presynaptic_criteria  = criteria,
                                postsynaptic_criteria = lc17_criteria,
                                min_weight = min_weight,
                                render = False)

    rec_df["dataset"] = name
    
    # Fix for hemibrain
    if name == "hemibrain":
        rec_df["instance_post"] = "LC17_R"

    # Save it
    out_path = os.path.join(OUT_DIR, f"{name}_LC17_all-inputs.parquet")
    rec_df.to_parquet(out_path,
                      index  = False,
                      engine = "pyarrow")
    print(f"{name} : {len(rec_df)} connections -> {out_path}")

    # Group by LC17 population
    input_df = rec_df.groupby(["instance_post",
                            "bodyId_pre", "instance_pre",
                            "type_pre"])["weight"].sum().reset_index()
    out_path = os.path.join(OUT_DIR, f"{name}_LC17_population-inputs.parquet")
    input_df.to_parquet(out_path,
                         index  = False,
                         engine = "pyarrow")
    print(f"{name} : {len(input_df)} connections -> {out_path}\n\n")

    return output_df

#------------------------------------------------------------------------------
if __name__ == "__main__":

    partners = {}
    print()
    # Run through each dataset
    for name, dataset in zip(names, datasets):
        partners[name] = fetch_partners(name, dataset)

    # Leave no stale default behind for whatever runs next
    neuprint.clear_default_client()

    # Status
    print("हो गया दोस्तों")