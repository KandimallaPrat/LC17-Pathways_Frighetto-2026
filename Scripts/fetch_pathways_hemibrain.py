"""
Fetch pathways from neuPrint for LC17 partners

Takes the top partners by hemibrain weight out of the shared partner table,
then walks the shortest paths from each of them to every descending neuron,
for both datasets in one call.

Fetching only - all the plotting happens elsewhere.

"""

import os
from itertools import product

import numpy as np
import pandas as pd

# Connectome
import connectome_analysis
import neuprint
from neuprint import NeuronCriteria as NC

#------------------------------------------------------------------------------
token = os.environ["HEMIBRAIN_TOKEN"]

# Working on datasets
#datasets = ["hemibrain:v1.2.1", "male-cns:v1.0"]
#names    = ["hemibrain", "malecns"]

datasets = ["hemibrain:v1.2.1"]
names    = ["hemibrain"]

PARTNER_FILE = "Data/Partners/LC17_dataset-shared-partners.parquet"
OUT_DIR      = "Data/Pathways"

# Top partners to follow, ranked on hemibrain
top_n = 15

# Same path search as the notebook
path_weight = 10
max_hops    = 3

# Not actually descending neurons - the circadian DN1a / DN1p cells, the
# endocrine DNES cells, and anything that never got a proper name
dn_exclude = r"DN1a|DN1p|DNES|DN\?"

#------------------------------------------------------------------------------
def get_targets(analysis):
    """
    Fetch the descending neurons and drop the tags that aren't really DNs.

    Parameters
    ----------
    analysis : neuPrintConnect
        Connected client for the dataset being worked on.

    Returns
    -------
    dn_info : DataFrame
        Neuron properties for the retained descending neurons.

    """
    dn_info, _ = neuprint.fetch_neurons(NC(instance = "DN.*", regex = True))

    # Remove the non-descending elements
    dn_info = dn_info.loc[~(dn_info["instance"].str.contains(dn_exclude,
                                                             regex = True,
                                                             na    = False))]

    # Anything unnamed is no use downstream either
    dn_info = dn_info.loc[dn_info["type"].notna()]

    return dn_info.reset_index(drop = True)

#------------------------------------------------------------------------------
def get_sources(top_types):
    """
    Fetch every neuron belonging to the top partner types.

    The shared partner table only carries types, so the bodyIds come straight
    out of the dataset being worked on - both hemispheres where there are two.

    Parameters
    ----------
    top_types : list
        Partner types to follow, ranked on hemibrain.

    Returns
    -------
    sources : DataFrame
        Neuron properties for the partners feeding the path search.

    """
    sources, _ = neuprint.fetch_neurons(NC(type = top_types))

    return sources.reset_index(drop = True)

#------------------------------------------------------------------------------
def fetch_paths(analysis, source_ids, target_ids):
    """
    Walk the shortest paths between every source and target pair.

    Same technique as the notebook - shortest paths only, capped at max_hops,
    with pairs that have no route simply dropped.

    Parameters
    ----------
    analysis : neuPrintConnect
        Connected client for the dataset being worked on.

    source_ids : array
        Partner bodyIds to start from.

    target_ids : array
        Descending neuron bodyIds to reach.

    Returns
    -------
    all_paths : DataFrame
        Every retained path, one row per node.

    """
    pairs = list(product(source_ids, target_ids))
    print(f"    # pairs : {len(pairs)}")

    path_lists = []

    # Loop over each pair
    for i, pair in enumerate(pairs, start = 1):

        # Get all the paths
        path = neuprint.queries.fetch_shortest_paths(
                    pair[0], pair[1],
                    min_weight = path_weight,
                    client     = analysis.client)

        # Get the size of each path
        path["size"] = path.groupby("path")["path"].transform("count")
        # Minus 1 for hops
        path["size"] = path["size"] - 1
        path = path.loc[path["size"] <= max_hops]

        # Remove
        if len(path) == 0:
            continue

        # Add Source and Target information
        path["source"] = pair[0]
        path["target"] = pair[1]

        # Append
        path_lists.append(path)

        # Something to watch while it runs
        if i % 250 == 0:
            print(f"    {i} / {len(pairs)} pairs, "
                  f"{len(path_lists)} with a route")

    # Convert to DataFrame
    all_paths = pd.concat(path_lists, ignore_index = True)

    return all_paths

#------------------------------------------------------------------------------
def fetch_dataset(name, dataset, top_types):
    """
    Everything for a single dataset, saved into its own folder.

    Parameters
    ----------
    name : string
        Short name of the dataset, used for the folder.

    dataset : string
        Dataset name and release version.

    top_types : list
        Partner types to follow, ranked on hemibrain.

    Returns
    -------
    None.

    """
    print(f"\n{name}")

    analysis = connectome_analysis.neuPrintConnect(
        token   = token,
        server  = 'neuprint.janelia.org',
        dataset = dataset)

    # A client per dataset stays alive across the loop, so neuPrint stops
    # picking one on its own. Point it at the dataset we're working on.
    neuprint.set_default_client(analysis.client)

    #--------------------------------------------------------------------------
    dn_info = get_targets(analysis)
    sources = get_sources(top_types)

    source_ids = np.unique(sources["bodyId"])
    target_ids = np.unique(dn_info["bodyId"])

    print(f"    # sources : {len(source_ids)} bodies "
          f"across {sources['type'].nunique()} of {len(top_types)} types")
    print(f"    # targets : {len(target_ids)} DN bodies "
          f"across {dn_info['type'].nunique()} types")

    #--------------------------------------------------------------------------
    all_paths = fetch_paths(analysis, source_ids, target_ids)

    # Save it, one folder per dataset
    out_dir = os.path.join(OUT_DIR, name)
    os.makedirs(out_dir, exist_ok = True)

    for frame, filename in [(all_paths, "LC17_all-paths"),
                            (sources,   "LC17_path-sources"),
                            (dn_info,   "LC17_path-targets")]:

        out_path = os.path.join(out_dir, f"{filename}.parquet")
        frame.to_parquet(out_path, index = False, engine = "pyarrow")
        print(f"    {len(frame)} rows -> {out_path}")

#------------------------------------------------------------------------------
if __name__ == "__main__":

    # The top partners, ranked on hemibrain
    partners  = pd.read_parquet(PARTNER_FILE)
    partners  = partners.sort_values("Hemibrain_weight", ascending = False)
    top_types = list(partners.head(top_n).index)

    print(f"top {top_n} partners : {', '.join(top_types)}")

    # Run through each dataset
    for name, dataset in zip(names, datasets):
        fetch_dataset(name, dataset, top_types)

    # Leave no stale default behind for whatever runs next
    neuprint.clear_default_client()
