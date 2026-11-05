# Exact live gate-edit responses

## family1_n20_base: aggregate

Request `af035daee40b0a05b7813d079eff1ff9f07ba513a0a4136ec41db1e09f045c3d`; status `ok`; admission `accepted`.

````text
{
  "version": "data-edge-program-v2",
  "exchanges": {
    "p1": {"edge": "EDGE_0_1", "group": 1},
    "p2": {"edge": "EDGE_0_2", "group": 1},
    "p3": {"edge": "EDGE_0_3", "group": 1},
    "p4": {"edge": "EDGE_0_4", "group": 1},
    "p5": {"edge": "EDGE_0_5", "group": 1},
    "p6": {"edge": "EDGE_1_6", "group": 1},
    "p7": {"edge": "EDGE_1_7", "group": 1},
    "p8": {"edge": "EDGE_1_8", "group": 1},
    "p9": {"edge": "EDGE_1_9", "group": 1},
    "p10": {"edge": "EDGE_1_10", "group": 1},
    "p11": {"edge": "EDGE_1_11", "group": 1},
    "p12": {"edge": "EDGE_1_12", "group": 1},
    "p13": {"edge": "EDGE_1_13", "group": 1},
    "p14": {"edge": "EDGE_1_14", "group": 1},
    "p15": {"edge": "EDGE_1_15", "group": 1},
    "p16": {"edge": "EDGE_1_16", "group": 1},
    "p17": {"edge": "EDGE_1_17", "group": 1},
    "p18": {"edge": "EDGE_1_18", "group": 1},
    "p19": {"edge": "EDGE_1_19", "group": 1}
  },
  "preparation": "compiler_counter_dicke_v1",
  "depth": 1,
  "explanation": {
    "connections": "Chose edges to connect asset qubits 0 and 1 through 19 with a consistent beta group 1, based on the proxy-B RMS and signed mean change for stability and allocation pressure. The selection prioritizes edges with lower RMS and stable signed Δ",
    "sharing": "All selected edges use the same beta group (1) for uniformity and to align with the compiler's greedy disjoint-round scheduling. This ensures consistent quantum gate application and resource allocation.",
    "falsifier": "The chosen edges may not minimize allocated F if the proxy-B RMS or correlation stability does not reflect true quantum resource or financial outcome; the numerical optimizer must validate."
  }
}
````

## family1_n20_base: counterfactual

Request `84013b07b87e8d5a039d0a90e0c6fd53bf4428792eb372d33a462e5f1635ae9c`; status `ok`; admission `accepted`.

````text
{
  "version": "data-edge-program-v2",
  "exchanges": {
    "p1": {"edge": "EDGE_0_1", "group": 1},
    "p2": {"edge": "EDGE_0_2", "group": 1},
    "p3": {"edge": "EDGE_0_3", "group": 1},
    "p4": {"edge": "EDGE_0_4", "group": 1},
    "p5": {"edge": "EDGE_0_5", "group": 1},
    "p6": {"edge": "EDGE_2_6", "group": 1},
    "p7": {"edge": "EDGE_1_7", "group": 1},
    "p8": {"edge": "EDGE_1_8", "group": 1},
    "p9": {"edge": "EDGE_1_9", "group": 1},
    "p10": {"edge": "EDGE_1_10", "group": 1},
    "p11": {"edge": "EDGE_1_11", "group": 1},
    "p12": {"edge": "EDGE_1_12", "group": 1},
    "p13": {"edge": "EDGE_1_13", "group": 1},
    "p14": {"edge": "EDGE_12_14", "group": 1},
    "p15": {"edge": "EDGE_1_15", "group": 1},
    "p16": {"edge": "EDGE_1_16", "group": 1},
    "p17": {"edge": "EDGE_1_17", "group": 1},
    "p18": {"edge": "EDGE_1_18", "group": 1},
    "p19": {"edge": "EDGE_18_19", "group": 1}
  },
  "preparation": "compiler_counter_dicke_v1",
  "depth": 1,
  "explanation": {
    "connections": "Selected edges based on proxy-B RMS and signed mean change to balance sensitivity and stability, favoring low-RMS alternatives that may better reflect true financial outcomes. Changed p6 from EDGE_1_6 to EDGE_2_6, p14 from EDGE_1_14 to EDGE", 
    "sharing": "All selected edges use beta group 1, aligning with compiler's greedy disjoint-round scheduling and maintaining uniformity across the circuit.",
    "falsifier": "The chosen edges may not minimize allocated F if proxy-B RMS or correlation stability does not reflect true quantum resource or financial outcome; numerical optimizer must validate."
  }
}
````

## family1_n20_exit: aggregate

Request `834301b701cce07c93f5784e6d3714fc7ecd48b1d965cf68e7338cd5b1060a28`; status `ok`; admission `accepted`.

````text
{
  "version": "data-edge-program-v2",
  "exchanges": {
    "p1": {
      "edge": "EDGE_1_2",
      "group": 1
    },
    "p2": {
      "edge": "EDGE_1_3",
      "group": 1
    },
    "p3": {
      "edge": "EDGE_1_4",
      "group": 1
    },
    "p4": {
      "edge": "EDGE_1_5",
      "group": 1
    },
    "p5": {
      "edge": "EDGE_1_6",
      "group": 1
    },
    "p6": {
      "edge": "EDGE_1_7",
      "group": 1
    },
    "p7": {
      "edge": "EDGE_1_8",
      "group": 1
    },
    "p8": {
      "edge": "EDGE_1_9",
      "group": 1
    },
    "p9": {
      "edge": "EDGE_1_10",
      "group": 1
    },
    "p10": {
      "edge": "EDGE_1_11",
      "group": 1
    },
    "p11": {
      "edge": "EDGE_1_12",
      "group": 1
    },
    "p12": {
      "edge": "EDGE_1_13",
      "group": 1
    },
    "p13": {
      "edge": "EDGE_1_14",
      "group": 1
    },
    "p14": {
      "edge": "EDGE_1_15",
      "group": 1
    },
    "p15": {
      "edge": "EDGE_1_16",
      "group": 1
    },
    "p16": {
      "edge": "EDGE_1_17",
      "group": 1
    },
    "p17": {
      "edge": "EDGE_1_18",
      "group": 1
    },
    "p18": {
      "edge": "EDGE_1_19",
      "group": 1
    }
  },
  "preparation": "compiler_counter_dicke_v1",
  "depth": 1,
  "explanation": {
    "connections": "Selected edges E1_2 through E1_19 to connect the fixed qubit (0) to all other free qubits, enabling support selection via quantum exchange. These edges reflect the highest proxy-B RMS changes, indicating sensitivity to portfolio adjustments",
    "sharing": "All edges use beta group 1, balancing the number of connections against angle budget constraints. This group choice is based on the lowest RMS and highest correlation for the first few edges, suggesting consistent financial signal.",
    "falsifier": "The selection does not consider the full set of quadratic terms or their numerical contrast. A different edge set with lower RMS but higher correlation might outperform if the proxy-B RMS is a poor indicator of actual allocated-F quality."
  }
}
````

## family1_n20_exit: counterfactual

Request `7567a64c160bfce361c7eae15e3816184748da125c48802d95c77a8feb9c95e8`; status `ok`; admission `accepted`.

````text
{
  "version": "data-edge-program-v2",
  "exchanges": {
    "p1": {
      "edge": "EDGE_1_2",
      "group": 1
    },
    "p2": {
      "edge": "EDGE_1_3",
      "group": 1
    },
    "p3": {
      "edge": "EDGE_1_4",
      "group": 1
    },
    "p4": {
      "edge": "EDGE_1_5",
      "group": 1
    },
    "p5": {
      "edge": "EDGE_2_6",
      "group": 1
    },
    "p6": {
      "edge": "EDGE_1_7",
      "group": 1
    },
    "p7": {
      "edge": "EDGE_1_8",
      "group": 1
    },
    "p8": {
      "edge": "EDGE_1_9",
      "group": 1
    },
    "p9": {
      "edge": "EDGE_1_10",
      "group": 1
    },
    "p10": {
      "edge": "EDGE_1_11",
      "group": 1
    },
    "p11": {
      "edge": "EDGE_1_12",
      "group": 1
    },
    "p12": {
      "edge": "EDGE_12_13",
      "group": 1
    },
    "p13": {
      "edge": "EDGE_12_14",
      "group": 1
    },
    "p14": {
      "edge": "EDGE_1_15",
      "group": 1
    },
    "p15": {
      "edge": "EDGE_1_16",
      "group": 1
    },
    "p16": {
      "edge": "EDGE_1_17",
      "group": 1
    },
    "p17": {
      "edge": "EDGE_1_18",
      "group": 1
    },
    "p18": {
      "edge": "EDGE_18_19",
      "group": 1
    }
  },
  "preparation": "compiler_counter_dicke_v1",
  "depth": 1,
  "explanation": {
    "connections": "Selected edges E1_2 through E1_19 to connect the fixed qubit (0) to all other free qubits, enabling support selection via quantum exchange. These edges reflect the highest proxy-B RMS changes, indicating sensitivity to portfolio adjustments",
    "sharing": "All edges use beta group 1, balancing the number of connections against angle budget constraints. This group choice is based on the lowest RMS and highest correlation for the first few edges, suggesting consistent financial signal.",
    "falsifier": "The selection does not consider the full set of quadratic terms or their numerical contrast. A different edge set with lower RMS but higher correlation might outperform if the proxy-B RMS is a poor indicator of actual allocated-F quality."
  }
}
````
