"""
Fetch pathways from neuPrint for LC17 partners - Male CNS

Same as the hemibrain fetch, but only walking the shortest paths to the DNs
we ended up picking in the hemibrain - the union of the auto filter (top 10
from the flow ranking) and Gio's filter.

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

# Working on dataset
dataset = "male-cns:v1.0"
name    = "malecns"

PARTNER_FILE = "Data/Partners/LC17_dataset-shared-partners.parquet"
OUT_DIR      = "Data/Pathways"

# Top partners to follow, ranked on hemibrain
top_n = 15

# Same path search as the hemibrain
path_weight = 10
max_hops    = 3

# Top 10 DNs from the flow ranking in LC17_hemibrain-DN-pathways
auto_filter = ["DNp06", "DNp23", "DNp09", "DNp11", "DNb01",
               "DNp05", "DNa04", "DNp04", "DNa03", "DNp03"]

# Gio's DNs, same as LC17_hemibrain-DN-pathways
gio_filter = ["DNa01", "DNa02", "DNa03", "DNa04", "DNa10",
              "DNb01", "DNp07", "DNp09"]

# Both lists together
dn_types = sorted(set(auto_filter) | set(gio_filter))

#------------------------------------------------------------------------------
def get_targets(dn_types):
    """
    Fetch every neuron belonging to the DN types we picked.

    Parameters
    ----------
    dn_types : list
        DN types to walk the paths to.

    Returns
    -------
    dn_info : DataFrame
        Neuron properties for the DNs - both hemispheres.

    """
    dn_info, _ = neuprint.fetch_neurons(NC(type = dn_types))

    return dn_info.reset_index(drop = True)

#------------------------------------------------------------------------------
def get_sources(top_types):
    """
    Fetch every neuron belonging to the top partner types.

    The shared partner table only carries types, so the bodyIds come straight
    out of the male CNS - both hemispheres.

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

    Same technique as the hemibrain - shortest paths only, capped at max_hops,
    with pairs that have no route simply dropped.

    Parameters
    ----------
    analysis : neuPrintConnect
        Connected client for the male CNS.

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
if __name__ == "__main__":

    # The top partners, ranked on hemibrain
    partners  = pd.read_parquet(PARTNER_FILE)
    partners  = partners.sort_values("Hemibrain_weight", ascending = False)
    top_types = list(partners.head(top_n).index)

    print(f"top {top_n} partners : {', '.join(top_types)}")
    print(f"{len(dn_types)} DN types : {', '.join(dn_types)}")

    print(f"\n{name}")

    analysis = connectome_analysis.neuPrintConnect(
        token   = token,
        server  = 'neuprint.janelia.org',
        dataset = dataset)

    # Point neuPrint at the male CNS
    neuprint.set_default_client(analysis.client)

    #--------------------------------------------------------------------------
    dn_info = get_targets(dn_types)
    sources = get_sources(top_types)

    source_ids = np.unique(sources["bodyId"])
    target_ids = np.unique(dn_info["bodyId"])

    print(f"    # sources : {len(source_ids)} bodies "
          f"across {sources['type'].nunique()} of {len(top_types)} types")
    print(f"    # targets : {len(target_ids)} DN bodies "
          f"across {dn_info['type'].nunique()} of {len(dn_types)} types")

    #--------------------------------------------------------------------------
    all_paths = fetch_paths(analysis, source_ids, target_ids)

    # Save it, same folder layout as the hemibrain
    out_dir = os.path.join(OUT_DIR, name)
    os.makedirs(out_dir, exist_ok = True)

    for frame, filename in [(all_paths, "LC17_all-paths"),
                            (sources,   "LC17_path-sources"),
                            (dn_info,   "LC17_path-targets")]:

        out_path = os.path.join(out_dir, f"{filename}.parquet")
        frame.to_parquet(out_path, index = False, engine = "pyarrow")
        print(f"    {len(frame)} rows -> {out_path}")

    # Leave no stale default behind for whatever runs next
    neuprint.clear_default_client()
