# Notebooks

Analysis and visualization of the data fetched by the [scripts](../Scripts/README.md). The notebooks read from `Data/` and write figures to `Figures/`, using paths relative to this folder.

| Notebook | Description |
|---|---|
| [`LC17_partner-check.ipynb`](#lc17_partner-checkipynb) | Compares the LC17 partners across the hemibrain and the male CNS |
| [`LC17_hemibrain-DN-pathways.ipynb`](#lc17_hemibrain-dn-pathwaysipynb) | Cleans, ranks, and draws the hemibrain pathways from the LC17 partners to the DNs |
| [`LC17_malecns-DN-pathways.ipynb`](#lc17_malecns-dn-pathwaysipynb) | Repeats the pathway analysis in the male CNS, separately for each hemisphere |

---

## `LC17_partner-check.ipynb`

Identifies the strong LC17 partners in each dataset, and the partner types shared between them.

**Inputs** — `Data/Partners/{dataset}_LC17_population-{outputs,inputs}.parquet`

### Analysis

1. **Weights** — Distribution of the synaptic weights from the LC17 population onto every partner.
2. **Outputs of LC17** — Partners receiving more than 100 synapses from the LC17 population. Connections onto other LC neurons and unnamed neurons are removed.
3. **Comparing shared partners** — Partner types present in both datasets. Weights and ranks are compared across the hemibrain and each male CNS hemisphere, with each dataset ranked against its own full partner list.
4. **Recurrent inputs of LC17** — Connections from the shared partner types back onto LC17.
5. **Recurrent vs feedforward partners** — Output weight against recurrent input weight for each shared type. The reciprocity is the fraction of all connections between a partner and LC17 that run back onto LC17. Partner neuron types are pooled across hemispheres.

### Outputs

**Data** (`Data/Partners/`)

| File | Description |
|---|---|
| `LC17_dataset-shared-partners.parquet` | Shared partner types with their weight, rank, recurrent input, and reciprocity in each dataset. Used as the source list for the pathway search. |

**Figures** (`Figures/Partners/`, saved as `.pdf` and `.png`)

| File | Description |
|---|---|
| `LC17_Partner-Weights` | Weight distributions of all LC17 partners |
| `{dataset}_LC17_Output-Heatmap-100` | Heatmap of the partners receiving more than 100 synapses |
| `LC17_Weight-Rank-Comparison-Output-100` | Weights and ranks of the shared partners across datasets |
| `{dataset}_LC17_Input-Shared-Heatmap-100` | Heatmap of the recurrent inputs from the shared partners |
| `LC17_Output-vs-Input-100` | Output against recurrent input for the shared partners |
| `LC17_Output-vs-Input-100-right-label` | Same, with the labels on the right |

---

## `LC17_hemibrain-DN-pathways.ipynb`

Cleans the hemibrain pathways, ranks the DNs by how much of the partners' output reaches them, and draws the resulting networks.

**Inputs** — `Data/Pathways/hemibrain/LC17_{all-paths,path-sources,path-targets}.parquet`

### Analysis

1. **Cleaning**
   - Left-hemisphere PVLP151 neurons are dropped. They were included only because the search was run by type, and they receive very little input from LC17.
   - Pathways passing through LC17 or through unnamed neurons are removed.
2. **Fetching the connectivity** — The all-to-all connectivity between every neuron on a pathway of at most 2 hops is fetched from neuPrint. The resulting network includes connections that do not lie on a shortest path.
3. **Partner–partner connectivity** — Connections between the partner types themselves. These connections are excluded from all later steps.
4. **Removing LPLC1 / LPLC2** — Pathways through LPLC1 and LPLC2 are removed. Most of them pass through PVLP011, which synapses onto nearly every LPLC1 and LPLC2 neuron.
5. **Selecting the DNs (flow ranking)** — The DNs are ranked by how much of the partners' output reaches them within the network, without counting shared connections more than once.
   - Each partner starts with its output synapses in the network.
   - At every hop, each neuron distributes what it received among its targets in proportion to its output synapses.
   - Connections out of the DNs are removed, so whatever reaches a DN stays there.
   - The **score** is the percentage of the partners' output that reaches each DN within 3 hops.
6. **Filtering the DNs** — Two DN selections are used to draw the networks:
   - `auto_filter` — The top 10 DNs from the flow ranking.
   - `gio_filter` — A manual selection.

   Only pathways ending on a selected DN are kept.
7. **Network** — Type-level network diagrams for each selection.
   - **X axis:** three layers (LC17 partners, intermediate neurons, DNs). The intermediate neurons are spread along the X axis by a spring layout.
   - **Y axis:** clustering of the connectivity (Ward's method).

### Outputs

**Data** (`Data/Pathways/hemibrain/`)

| File | Description |
|---|---|
| `LC17_network.parquet` | All-to-all connectivity between the neurons on the pathways |

**Figures** (`Figures/Pathways/hemibrain/`, saved as `.pdf` and `.png`)

| File | Description |
|---|---|
| `hemibrain_LC17_Pathways-Cleaning` | Number of pathways per source–DN pair before and after cleaning |
| `hemibrain_LC17_Partner-Inter-Connectivity` | Heatmap of the connectivity between the partner types |
| `hemibrain_LC17_DN-Ranking` | Flow ranking of the DNs, broken down by hop |
| `hemibrain_LC17_Pathways-AutoFilter` | Network diagram for the top 10 DNs from the flow ranking |
| `hemibrain_LC17_Pathways-GioFilter` | Network diagram for the manually selected DNs |

---

## `LC17_malecns-DN-pathways.ipynb`

Repeats the hemibrain analysis in the male CNS. The male CNS contains both hemispheres, so every neuron is labelled by type and side (e.g. `PVLP061_R`). No new DN selection is made; the DN lists are taken directly from the hemibrain.

**Inputs** — `Data/Pathways/malecns/LC17_{all-paths,path-sources,path-targets}.parquet`

### Analysis

1. **Cleaning** — Pathways passing through LC17 or through unnamed neurons are removed. Partners from both hemispheres are retained.
2. **Fetching the connectivity** — As in the hemibrain.
3. **Partner–partner connectivity** — Connections between the partners, arranged with the right-hemisphere partners first so that ipsilateral and contralateral connections form separate blocks.
4. **Removing LPLC1 / LPLC2** — As in the hemibrain.
5. **Flow to the DNs** — The same flow measure as the hemibrain, run separately from the right-hemisphere and the left-hemisphere partners. No ranking or selection is performed.
   - Each score is the percentage of that hemisphere's partner output reaching each DN within 3 hops.
   - Only connections back onto the starting partners are removed. Partners in the opposite hemisphere are treated as ordinary downstream neurons, so pathways such as `PVLP120_R → PVLP151_L` are retained.
   - The left and right DNs of each type are plotted next to each other, with types sorted by their total flow.
   - A DN marked with a star (e.g. `*DNp01_R`) is absent from the network: it appears only on 3-hop pathways, whereas the network is built from pathways of at most 2 hops. It is shown as an empty row.
6. **Network** — Network diagrams using the hemibrain `auto_filter` and `gio_filter` selections, for the pathways starting from the right-hemisphere partners.
   - Only the right-hemisphere partners form the first layer. Left-hemisphere partners along these pathways are drawn as intermediates.
   - Left-hemisphere nodes are mirrored below a dotted line at zero, across all layers.

### Notes

- The hemisphere of a neuron is taken from its neuPrint instance name. Every partner receives the large majority of its LC17 input from the LC17 population on its own side (at least 76%).
- Some DNs receive direct input from partners in the opposite hemisphere. This comes almost entirely from PVLP151 (SCB004), which projects across the midline.
- The male CNS instance of DNb09 is annotated `DNb09(DNb01)`, so the hemibrain DNb01 may correspond to DNb09 in the male CNS.
- Flow percentages are not directly comparable with the hemibrain, since the male CNS pathway search was limited to 14 DN types.

### Outputs

**Data** (`Data/Pathways/malecns/`)

| File | Description |
|---|---|
| `LC17_network.parquet` | All-to-all connectivity between the neurons on the pathways |

**Figures** (`Figures/Pathways/malecns/`, saved as `.pdf` and `.png`)

| File | Description |
|---|---|
| `malecns_LC17_Partner-Inter-Connectivity` | Heatmap of the connectivity between the partners, by type and side |
| `malecns_LC17_DN-Flow` | Flow onto each DN from the right and from the left partners, broken down by hop. A star marks a DN side absent from the network. |
| `malecns_LC17_Pathways-AutoFilter-R` | Network diagram for the hemibrain top 10 DNs, from the right partners |
| `malecns_LC17_Pathways-GioFilter-R` | Network diagram for the manually selected DNs, from the right partners |
