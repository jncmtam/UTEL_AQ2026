# Exact GPU model responses for live_edge_v2

Recorded outputs from the single real GPU batch. They are not hand-authored examples or compiler-generated substitutes. Explanations are unverified and sometimes incorrect; see FINDINGS.md.

## family0_n12_base / context_only

Request hash: `8b33b91f866a96ab4d1300c6664d0e25ba1f1b749ccd7f915b96430a81ca0aae`. Finish reason: stop.

```json
{
  "version": "data-edge-program-v2",
  "exchanges": {
    "p1": {
      "edge": "EDGE_0_1",
      "group": 1
    },
    "p2": {
      "edge": "EDGE_0_2",
      "group": 1
    },
    "p3": {
      "edge": "EDGE_0_3",
      "group": 1
    },
    "p4": {
      "edge": "EDGE_0_4",
      "group": 1
    },
    "p5": {
      "edge": "EDGE_0_5",
      "group": 1
    },
    "p6": {
      "edge": "EDGE_0_6",
      "group": 1
    },
    "p7": {
      "edge": "EDGE_0_7",
      "group": 1
    },
    "p8": {
      "edge": "EDGE_0_8",
      "group": 1
    },
    "p9": {
      "edge": "EDGE_0_9",
      "group": 1
    },
    "p10": {
      "edge": "EDGE_0_10",
      "group": 1
    },
    "p11": {
      "edge": "EDGE_0_11",
      "group": 1
    }
  },
  "preparation": "compiler_counter_dicke_v1",
  "depth": 1,
  "explanation": {
    "connections": "Each child is connected to the root asset (ASSET_0) via a unique data-edge, reflecting the quadratic ZZ interactions in the Hamiltonian where ASSET_0 is the central hub for all pairwise correlations. This structure ensures that the QAOA ans",
    "sharing": "The root asset's influence on all others is encoded through its connections to each child, maintaining the problem's cardinality constraint of k=3 while preserving sector weight caps and position bounds.",
    "falsifier": "If any child's edge coefficient exceeds the specified penalty threshold or if the total allocated F score falls below the minimum empirical feasibility, the exchange graph fails validation."
  }
}
```

## family0_n12_base / guided

Request hash: `eae722dc85459b5e6ac01e1de45a0a7b7a750a58280771510b83efd952a4cdba`. Finish reason: stop.

```json
{
  "version": "data-edge-program-v2",
  "exchanges": {
    "p1": {
      "edge": "EDGE_0_1",
      "group": 1
    },
    "p2": {
      "edge": "EDGE_0_2",
      "group": 1
    },
    "p3": {
      "edge": "EDGE_0_3",
      "group": 1
    },
    "p4": {
      "edge": "EDGE_0_4",
      "group": 1
    },
    "p5": {
      "edge": "EDGE_0_5",
      "group": 1
    },
    "p6": {
      "edge": "EDGE_0_6",
      "group": 1
    },
    "p7": {
      "edge": "EDGE_0_7",
      "group": 1
    },
    "p8": {
      "edge": "EDGE_0_8",
      "group": 1
    },
    "p9": {
      "edge": "EDGE_0_9",
      "group": 1
    },
    "p10": {
      "edge": "EDGE_0_10",
      "group": 1
    },
    "p11": {
      "edge": "EDGE_0_11",
      "group": 1
    }
  },
  "preparation": "compiler_counter_dicke_v1",
  "depth": 1,
  "explanation": {
    "connections": "All edges from ASSET_0 to other assets selected to maintain full connectivity with the reference asset, enabling effective quantum correlation in the support selection.",
    "sharing": "Each selected edge is assigned to one beta group to ensure uniform quantum gate application and maintain the integrity of the QAOA layer.",
    "falsifier": "If any selected edge exhibits low RMS or unstable correlation, it could indicate a poor resource tradeoff, suggesting the need for alternative edge selection to improve the fidelity of the quantum optimization."
  }
}
```

## family0_n12_exit / context_only

Request hash: `31c659df4d04a467f27078a6568a3ad74cdcba169d75558ba3ee4d727aa29baf`. Finish reason: stop.

```json
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
    }
  },
  "preparation": "compiler_counter_dicke_v1",
  "depth": 1,
  "explanation": {
    "connections": "Each child node connects to the root via a unique data-edge, forming a star topology. The root node (ASSET_00) is excluded from the support set, and all other nodes are connected to it to represent pairwise interactions in the portfolio.",
    "sharing": "The beta group 1 is used for all edges, indicating a uniform coupling strength across all pairwise interactions in the exchange graph. This ensures consistent quantum gate scheduling and resource allocation.",
    "falsifier": "If any edge's coefficient in the Hamiltonian is zero or negligible, the corresponding data-edge connection is invalid. Additionally, if the cardinality constraint is violated by selecting more than k assets, the exchange graph is falsified."
  }
}
```

## family0_n12_exit / guided

Request hash: `de816aeb85a2791678c1e9f19b6722179e6e57aca468c7d51029996bc4b6c5b9`. Finish reason: stop.

```json
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
    }
  },
  "preparation": "compiler_counter_dicke_v1",
  "depth": 1,
  "explanation": {
    "connections": "Selected edges form a star graph centered at ASSET_00 (frozen qubit 0) to enable efficient quantum optimization of portfolio weights while respecting sector constraints and turnover limits.",
    "sharing": "Each edge represents a pairwise correlation between ASSET_00 and other assets, capturing risk interdependencies for portfolio rebalancing.",
    "falsifier": "If the selected edges do not reflect significant correlations or if the chosen beta group fails to optimize the objective function within the given budget, the exchange graph may not yield a valid portfolio solution."
  }
}
```

## family1_n20_base / context_only

Request hash: `a956999404817bb5474049231e3b6287df39f503c52db10ffefc9f041bf75395`. Finish reason: stop.

```json
{
  "version": "data-edge-program-v2",
  "exchanges": {
    "p1": {
      "edge": "EDGE_0_1",
      "group": 1
    },
    "p2": {
      "edge": "EDGE_0_2",
      "group": 1
    },
    "p3": {
      "edge": "EDGE_0_3",
      "group": 1
    },
    "p4": {
      "edge": "EDGE_0_4",
      "group": 1
    },
    "p5": {
      "edge": "EDGE_0_5",
      "group": 1
    },
    "p6": {
      "edge": "EDGE_0_6",
      "group": 1
    },
    "p7": {
      "edge": "EDGE_0_7",
      "group": 1
    },
    "p8": {
      "edge": "EDGE_0_8",
      "group": 1
    },
    "p9": {
      "edge": "EDGE_0_9",
      "group": 1
    },
    "p10": {
      "edge": "EDGE_0_10",
      "group": 1
    },
    "p11": {
      "edge": "EDGE_0_11",
      "group": 1
    },
    "p12": {
      "edge": "EDGE_0_12",
      "group": 1
    },
    "p13": {
      "edge": "EDGE_0_13",
      "group": 1
    },
    "p14": {
      "edge": "EDGE_0_14",
      "group": 1
    },
    "p15": {
      "edge": "EDGE_0_15",
      "group": 1
    },
    "p16": {
      "edge": "EDGE_0_16",
      "group": 1
    },
    "p17": {
      "edge": "EDGE_0_17",
      "group": 1
    },
    "p18": {
      "edge": "EDGE_0_18",
      "group": 1
    },
    "p19": {
      "edge": "EDGE_0_19",
      "group": 1
    }
  },
  "preparation": "compiler_counter_dicke_v1",
  "depth": 1,
  "explanation": {
    "connections": "Each data-edge ID represents a unique pairwise interaction between assets in the portfolio. These interactions are derived from the Hamiltonian's quadratic ZZ terms, which encode the correlation structure of the optimization problem. The q-",
    "sharing": "The beta group assignment ensures that each pair of assets is connected through a shared RXX(2*beta) and RYY(2*beta) gate, enabling quantum evolution under the problem Hamiltonian.",
    "falsifier": "If any asset pair's interaction strength (coefficient) is below the numerical precision threshold, the corresponding edge may be omitted from the exchange graph, invalidating the cardinality constraint."
  }
}
```

## family1_n20_base / guided

Request hash: `ad59e875f9ef6bc31868ce9b681645d61252396cb745f9931d43a8e2ae47e57a`. Finish reason: stop.

```json
{
  "version": "data-edge-program-v2",
  "exchanges": {
    "p1": {
      "edge": "EDGE_0_1",
      "group": 1
    },
    "p2": {
      "edge": "EDGE_0_2",
      "group": 1
    },
    "p3": {
      "edge": "EDGE_0_3",
      "group": 1
    },
    "p4": {
      "edge": "EDGE_0_4",
      "group": 1
    },
    "p5": {
      "edge": "EDGE_0_5",
      "group": 1
    },
    "p6": {
      "edge": "EDGE_0_6",
      "group": 1
    },
    "p7": {
      "edge": "EDGE_0_7",
      "group": 1
    },
    "p8": {
      "edge": "EDGE_0_8",
      "group": 1
    },
    "p9": {
      "edge": "EDGE_0_9",
      "group": 1
    },
    "p10": {
      "edge": "EDGE_0_10",
      "group": 1
    },
    "p11": {
      "edge": "EDGE_0_11",
      "group": 1
    },
    "p12": {
      "edge": "EDGE_0_12",
      "group": 1
    },
    "p13": {
      "edge": "EDGE_0_13",
      "group": 1
    },
    "p14": {
      "edge": "EDGE_0_14",
      "group": 1
    },
    "p15": {
      "edge": "EDGE_0_15",
      "group": 1
    },
    "p16": {
      "edge": "EDGE_0_16",
      "group": 1
    },
    "p17": {
      "edge": "EDGE_0_17",
      "group": 1
    },
    "p18": {
      "edge": "EDGE_0_18",
      "group": 1
    },
    "p19": {
      "edge": "EDGE_0_19",
      "group": 1
    }
  },
  "preparation": "compiler_counter_dicke_v1",
  "depth": 1,
  "explanation": {
    "connections": "Each selected edge connects two assets in the portfolio, forming a pairwise interaction graph for QAOA. The choice of edges is based on the proxy-B RMS/signed mean change to assess sensitivity and correlation stability. The edges are chosen",
    "sharing": "The beta group 1 is assigned to all edges to maintain a uniform interaction strength across the selected connections. This simplifies the scheduling and ensures consistent quantum gate application.",
    "falsifier": "The falsifier is the potential for suboptimal portfolio selection if the selected edges do not adequately represent the underlying correlation structure or if the beta group is insufficient to capture the complexity of the financial problem"
  }
}
```

## family1_n20_exit / context_only

Request hash: `c2d50203074cc008f47995b1b190dbd621bdbdced5b411fbde68b7f744e13a79`. Finish reason: stop.

```json
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
    "connections": "Each parent-child pair in the exchange table is mapped to a unique data-edge ID (e.g., EDGE_1_2) connecting asset qubits 1 and 2. These edges are chosen to reflect the highest quadratic ZZ coefficients in the Hamiltonian, indicating strong,",
    "sharing": "The beta group 1 is assigned to all connections, implying a uniform parameterization for all exchange interactions in the single QAOA layer. This simplifies scheduling and ensures consistent quantum gate application across all selected qub",
    "falsifier": "If the Hamiltonian's quadratic ZZ coefficients were not the primary driver of exchange interactions, or if a different cardinality constraint or sector weight cap were more influential, then the selection of these specific edges and group 1"
  }
}
```

## family1_n20_exit / guided

Request hash: `2e227e94562c50930a6bab31607b61488ed563ab3d7dfd713909e270f43b2be1`. Finish reason: stop.

```json
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
    "connections": "Each selected edge represents a pairwise interaction between ASSET_01 and another asset, forming a star topology centered on ASSET_01. This choice emphasizes the central role of ASSET_01 in the portfolio's exchange dynamics, aligning with a",
    "sharing": "The beta group 1 is assigned to all edges to maintain uniformity in the QAOA layer's parameterization, ensuring consistent quantum gate scheduling and resource allocation across all interactions.",
    "falsifier": "If the optimal solution requires strong correlations between assets other than those involving ASSET_01, this star topology will underperform, as it restricts exchange to a single hub."
  }
}
```
