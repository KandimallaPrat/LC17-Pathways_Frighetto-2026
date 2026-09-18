# Scripts

Scripts that fetch data from [neuPrint](https://neuprint.janelia.org). All plotting and downstream analysis is carried out in the [notebooks](../Notebooks/README.md).

All scripts use paths relative to the repository root and should be run from there:

```bash
python Scripts/<script>.py
```

## Analysis Pipeline

The scripts and notebooks run in the following order. Each step reads the output of the previous one.

| Step | File | Reads | Writes |
|:---:|---|---|---|
| 1 | `Scripts/LC17_partners.py` | neuPrint | `Data/Partners/` |
| 2 | `Notebooks/LC17_partner-check.ipynb` | `Data/Partners/` | `Data/Partners/LC17_dataset-shared-partners.parquet` |
| 3 | `Scripts/fetch_pathways_hemibrain.py` | Shared partner table, neuPrint | `Data/Pathways/hemibrain/` |
| 4 | `Notebooks/LC17_hemibrain-DN-pathways.ipynb` | `Data/Pathways/hemibrain/` | DN selections (`auto_filter`, `gio_filter`) |
| 5 | `Scripts/fetch_pathways_malecns.py` | Shared partner table, DN selections, neuPrint | `Data/Pathways/malecns/` |
| 6 | `Notebooks/LC17_malecns-DN-pathways.ipynb` | `Data/Pathways/malecns/` | Male CNS flow and network figures |
| 7 | `Notebooks/LC17-LPLC2_malecns-outputs.ipynb` | neuPrint | `Data/Direct/malecns/` |

---

### 1. `LC17_partners.py` — LC17 Partners

Fetches the synaptic partners of every LC17 neuron in both the hemibrain (`hemibrain:v1.2.1`) and the male CNS (`male-cns:v1.0`).

1. **Outputs** — All connections from LC17 neurons to their postsynaptic partners (minimum weight of 1 synapse), summed across ROIs.
2. **Population outputs** — The same connections, with the LC17 population treated as a single presynaptic unit.
3. **Recurrent inputs** — All connections from those postsynaptic partners back onto LC17.
4. **Population inputs** — The recurrent inputs, with the LC17 population treated as a single postsynaptic unit.

All hemibrain LC17 neurons are labelled `LC17_R`, since the hemibrain contains only the right hemisphere.

**Outputs** (`Data/Partners/`, one set per dataset)

| File | Description |
|---|---|
| `{dataset}_LC17_all-outputs.parquet` | Neuron-to-neuron LC17 outputs |
| `{dataset}_LC17_population-outputs.parquet` | Outputs grouped by LC17 population |
| `{dataset}_LC17_all-inputs.parquet` | Neuron-to-neuron inputs from partners onto LC17 |
| `{dataset}_LC17_population-inputs.parquet` | Inputs grouped by LC17 population |

---

### 3. `fetch_pathways_hemibrain.py` — Hemibrain Pathways

Maps the multi-hop pathways from the first-order LC17 partners to the descending neurons (DNs) in the hemibrain.

1. **Sources** — The top 15 partner types, ranked by hemibrain weight in the shared partner table. Every neuron of those types is used as a source.
2. **Targets** — Every neuron whose instance begins with `DN`, excluding cells that are not descending neurons (the circadian DN1a / DN1p, the endocrine DNES, and unnamed `DN?` cells).
3. **Pathway search** — `fetch_shortest_paths` between every source–target pair, keeping paths of at most 3 hops with a minimum weight of 10 synapses per connection. Pairs without a route are dropped.

---

### 5. `fetch_pathways_malecns.py` — Male CNS Pathways

Repeats the hemibrain pathway search in the male CNS. The search is limited to the DNs selected in the hemibrain.

1. **Sources** — The same top 15 partner types, from both hemispheres.
2. **Targets** — Every neuron belonging to the union of the two DN selections from the hemibrain notebook (14 DN types, 28 neurons):
   - `auto_filter` — The top 10 DNs from the flow ranking.
   - `gio_filter` — A manual selection.
3. **Pathway search** — Identical to the hemibrain search.

> [!NOTE]
> The DN selections are written into the script by hand. If the hemibrain ranking changes, `auto_filter` must be updated manually.

---

**Pathway outputs** (`Data/Pathways/{dataset}/`, shared by steps 3 and 5)

| File | Description |
|---|---|
| `LC17_all-paths.parquet` | Every retained pathway, one row per node, with the source, target, path ID, and hop count |
| `LC17_path-sources.parquet` | Neuron properties of the partner neurons used as sources |
| `LC17_path-targets.parquet` | Neuron properties of the DNs used as targets |

## Search Parameters

| Parameter | Value | Description |
|---|---|---|
| `top_n` | 15 | Number of partner types used as sources |
| `path_weight` | 10 | Minimum synapses per connection along a pathway |
| `max_hops` | 3 | Maximum pathway length |

## Dependencies

- [`neuprint-python`](https://github.com/connectome-neuprint/neuprint-python) — neuPrint API client
- `connectome_analysis` — Wrapper around the neuPrint client
- `pandas`, `numpy`, `pyarrow`

A neuPrint API token is required and should be set as the `HEMIBRAIN_TOKEN` environment variable. The same token is used for both datasets. Tokens are available from [neuprint.janelia.org](https://neuprint.janelia.org) after logging in.
