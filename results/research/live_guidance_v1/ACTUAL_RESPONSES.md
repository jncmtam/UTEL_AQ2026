# Actual new live model responses

These are recorded model outputs, not hand-authored examples. Admission and financial evaluation are separate.

## family0_n12_base / context_only

Request hash: `c1e8bf3f75ed0516e5bb14c0a1fbd12414e74f5976ffe629bf14461c0f052c39`. Status: ok.

```json
{
  "version": "data-guided-common-counter-v1",
  "parents": {
    "p1": 0,
    "p2": 1,
    "p3": 2,
    "p4": 3,
    "p5": 4,
    "p6": 5,
    "p7": 6,
    "p8": 7,
    "p9": 8,
    "p10": 9,
    "p11": 10
  },
  "schedule": [
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10
  ],
  "groups": [
    0,
    1,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1
  ],
  "preparation": "compiler_counter_dicke_v1",
  "depth": 1,
  "rationale": [
    {
      "feature_ids": [
        "CORRELATION",
        "SPECTRUM",
        "INCUMBENT",
        "CORRELATION",
        "SPECTRUM",
        "INCUMBENT",
        "CORRELATION",
        "SPECTRUM",
        "INCUMBENT",
        "CORRELATION",
        "SPECTRUM"
      ],
      "decision": "p1->p2->p3->p4->p5->p6->p7->p8->p9->p10->p11"
    }
  ],
  "evidence": {
    "parent_edges": {
      "p1": "EDGE_0_1",
      "p2": "EDGE_0_2",
      "p3": "EDGE_0_3",
      "p4": "EDGE_0_4",
      "p5": "EDGE_0_5",
      "p6": "EDGE_0_6",
      "p7": "EDGE_0_7",
      "p8": "EDGE_0_8",
      "p9": "EDGE_0_9",
      "p10": "EDGE_0_10",
      "p11": "EDGE_0_11"
    },
    "schedule": {
      "feature_ids": [
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET"
      ],
      "hypothesis": "All edges are scheduled in the order of their index to ensure minimal resource usage.",
      "falsifier": "If any edge is scheduled out of order, it would increase the circuit depth and resource usage."
    },
    "sharing": {
      "feature_ids": [
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET"
      ],
      "hypothesis": "All edges are shared equally to maintain balanced resource allocation.",
      "falsifier": "Unequal sharing would result in resource imbalance and potentially suboptimal performance."
    }
  }
}
```

## family0_n12_base / guided

Request hash: `2d5f954d1cff678b65dbbecd58332d7647e068859164728378084d26ee8d245a`. Status: ok.

```json
{
  "version": "data-guided-common-counter-v1",
  "parents": {
    "p1": 0,
    "p2": 1,
    "p3": 2,
    "p4": 3,
    "p5": 4,
    "p6": 5,
    "p7": 6,
    "p8": 7,
    "p9": 8,
    "p10": 9,
    "p11": 10
  },
  "schedule": [
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10
  ],
  "groups": [
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0
  ],
  "preparation": "compiler_counter_dicke_v1",
  "depth": 1,
  "rationale": [
    {
      "feature_ids": [
        "CORRELATION",
        "SPECTRUM"
      ],
      "decision": "select p1,p2,p3 as parent tree based on high correlation and low RMS of mean delta B"
    }
  ],
  "evidence": {
    "parent_edges": {
      "p1": "EDGE_0_1",
      "p2": "EDGE_0_2",
      "p3": "EDGE_0_3",
      "p4": "EDGE_0_4",
      "p5": "EDGE_0_5",
      "p6": "EDGE_0_6",
      "p7": "EDGE_0_7",
      "p8": "EDGE_0_8",
      "p9": "EDGE_0_9",
      "p10": "EDGE_0_10",
      "p11": "EDGE_0_11"
    },
    "schedule": {
      "feature_ids": [
        "RESOURCE_BUDGET",
        "EXCHANGE_TABLE"
      ],
      "hypothesis": "schedule is a permutation of edge indices that preserves cardinality",
      "falsifier": "if any edge is missing or duplicated in the schedule"
    },
    "sharing": {
      "feature_ids": [
        "RESOURCE_BUDGET",
        "EXCHANGE_TABLE"
      ],
      "hypothesis": "beta groups share qubits but do not overlap",
      "falsifier": "if any qubit is used in more than one beta group"
    }
  }
}
```

## family0_n12_exit / context_only

Request hash: `496e9673a1b151e53ed4131ca862703927450f30afa09707abb420a79ea34fbd`. Status: ok.

```json
{
  "version": "data-guided-common-counter-v1",
  "parents": {
    "p1": 0,
    "p2": 1,
    "p3": 2,
    "p4": 3,
    "p5": 4,
    "p6": 5,
    "p7": 6,
    "p8": 7,
    "p9": 8,
    "p10": 9
  },
  "schedule": [
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    1
  ],
  "groups": [
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1
  ],
  "preparation": "compiler_counter_dicke_v1",
  "depth": 1,
  "rationale": [
    {
      "feature_ids": [
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION"
      ],
      "decision": "select p1, p2, p3, p4, p5, p6, p7, p8, p9, p10"
    }
  ],
  "evidence": {
    "parent_edges": {
      "p1": "EDGE_1_2",
      "p2": "EDGE_1_3",
      "p3": "EDGE_1_4",
      "p4": "EDGE_1_5",
      "p5": "EDGE_1_6",
      "p6": "EDGE_1_7",
      "p7": "EDGE_1_8",
      "p8": "EDGE_1_9",
      "p9": "EDGE_1_10",
      "p10": "EDGE_1_11"
    },
    "schedule": {
      "feature_ids": [
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE"
      ],
      "hypothesis": "exchange schedule is permutation of edge indices",
      "falsifier": "no edge index appears twice in schedule"
    },
    "sharing": {
      "feature_ids": [
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET"
      ],
      "hypothesis": "beta groups are shared between parent edges",
      "falsifier": "beta group indices do not repeat for same parent"
    }
  }
}
```

## family0_n12_exit / guided

Request hash: `1752cf1624a60548e4730d07512bd0760f72fbbb249eea3d21f453f1ed6f82d8`. Status: ok.

```json
{
  "version": "data-guided-common-counter-v1",
  "parents": {
    "p1": 0,
    "p2": 1,
    "p3": 2,
    "p4": 3,
    "p5": 4,
    "p6": 5,
    "p7": 6,
    "p8": 7,
    "p9": 8,
    "p10": 9
  },
  "schedule": [
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    1
  ],
  "groups": [
    0,
    1,
    1,
    0,
    1,
    1,
    0,
    1,
    1,
    0
  ],
  "preparation": "compiler_counter_dicke_v1",
  "depth": 1,
  "rationale": [
    {
      "feature_ids": [
        "CORRELATION",
        "SPECTRUM",
        "CORRELATION",
        "SPECTRUM"
      ],
      "decision": "selecting p1 as parent for p2, p3, p4, p5, p6, p7, p8, p9, p10 based on highest correlation and lowest RMS in exchange table"
    }
  ],
  "evidence": {
    "parent_edges": {
      "p1": "EDGE_1_2",
      "p2": "EDGE_1_3",
      "p3": "EDGE_1_4",
      "p4": "EDGE_1_5",
      "p5": "EDGE_1_6",
      "p6": "EDGE_1_7",
      "p7": "EDGE_1_8",
      "p8": "EDGE_1_9",
      "p9": "EDGE_1_10",
      "p10": "EDGE_1_11"
    },
    "schedule": {
      "feature_ids": [
        "EXCHANGE_TABLE",
        "RESOURCE_BUDGET"
      ],
      "hypothesis": "schedule is permutation of edge indices that maximizes disjoint pairs and minimizes shared qubit conflicts",
      "falsifier": "if any exchange in schedule causes shared qubit conflict or violates resource budget"
    },
    "sharing": {
      "feature_ids": [
        "EXCHANGE_TABLE",
        "RESOURCE_BUDGET"
      ],
      "hypothesis": "beta groups are assigned to minimize channel heterogeneity and maximize angle evaluation budget",
      "falsifier": "if any group assignment leads to resource exhaustion or angle evaluation inefficiency"
    }
  }
}
```

## family1_n20_base / context_only

Request hash: `4be3663b5f4cf09547df4ec5fd8ca48b1540ca7bcd5800347259ef9968076d31`. Status: ok.

```json
{
  "version": "data-guided-common-counter-v1",
  "parents": {
    "p1": 0,
    "p2": 0,
    "p3": 0,
    "p4": 1,
    "p5": 1,
    "p6": 1,
    "p7": 2,
    "p8": 2,
    "p9": 2,
    "p10": 3,
    "p11": 3,
    "p12": 3,
    "p13": 4,
    "p14": 4,
    "p15": 4,
    "p16": 5,
    "p17": 5,
    "p18": 5,
    "p19": 6
  },
  "schedule": [
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    18
  ],
  "groups": [
    0,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1
  ],
  "preparation": "compiler_counter_dicke_v1",
  "depth": 1,
  "rationale": [
    {
      "feature_ids": [
        "CORRELATION",
        "SPECTRUM",
        "INCUMBENT",
        "INCUMBENT"
      ],
      "decision": "p1,p2,p3,p4,p5,p6,p7,p8,p9,p10,p11,p12,p13,p14,p15,p16,p17,p18,p19"
    }
  ],
  "evidence": {
    "parent_edges": {
      "p1": "EDGE_0_1",
      "p2": "EDGE_0_2",
      "p3": "EDGE_0_3",
      "p4": "EDGE_1_4",
      "p5": "EDGE_1_5",
      "p6": "EDGE_1_6",
      "p7": "EDGE_2_7",
      "p8": "EDGE_2_8",
      "p9": "EDGE_2_9",
      "p10": "EDGE_3_10",
      "p11": "EDGE_3_11",
      "p12": "EDGE_3_12",
      "p13": "EDGE_4_13",
      "p14": "EDGE_4_14",
      "p15": "EDGE_4_15",
      "p16": "EDGE_5_16",
      "p17": "EDGE_5_17",
      "p18": "EDGE_5_18",
      "p19": "EDGE_6_19"
    },
    "schedule": {
      "feature_ids": [
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE"
      ],
      "hypothesis": "Edge schedule is a permutation of edge indices.",
      "falsifier": "If any edge index is repeated or missing, schedule is invalid."
    },
    "sharing": {
      "feature_ids": [
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE"
      ],
      "hypothesis": "Each child qubit is connected to a parent qubit with smaller index.",
      "falsifier": "If any child qubit is connected to a parent qubit with larger index, sharing is invalid."
    }
  }
}
```

## family1_n20_base / guided

Request hash: `1f6b33202fa3e1c1c0c92055528f51ab354c2cbb6a8f906e3fe6e820f4232b10`. Status: ok.

```json
{
  "version": "data-guided-common-counter-v1",
  "parents": {
    "p1": 0,
    "p2": 1,
    "p3": 2,
    "p4": 3,
    "p5": 4,
    "p6": 5,
    "p7": 6,
    "p8": 7,
    "p9": 8,
    "p10": 9,
    "p11": 10,
    "p12": 11,
    "p13": 12,
    "p14": 13,
    "p15": 14,
    "p16": 15,
    "p17": 16,
    "p18": 17,
    "p19": 18
  },
  "schedule": [
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18
  ],
  "groups": [
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0
  ],
  "preparation": "compiler_counter_dicke_v1",
  "depth": 1,
  "rationale": [
    {
      "feature_ids": [
        "CORRELATION",
        "SPECTRUM",
        "CORRELATION",
        "SPECTRUM"
      ],
      "decision": "p1,p2,p3 are selected as the parent tree for their high correlation and low RMS in the exchange table. The schedule orders these exchanges to preserve cardinality and avoid shared qubit conflicts. The two beta groups are chosen to reflect the heterogeneity in the spectrum of the selected edges, with"
    }
  ],
  "evidence": {
    "parent_edges": {
      "p1": "EDGE_0_1",
      "p2": "EDGE_0_2",
      "p3": "EDGE_0_3",
      "p4": "EDGE_0_4",
      "p5": "EDGE_0_5",
      "p6": "EDGE_0_6",
      "p7": "EDGE_0_7",
      "p8": "EDGE_0_8",
      "p9": "EDGE_0_9",
      "p10": "EDGE_0_10",
      "p11": "EDGE_0_11",
      "p12": "EDGE_0_12",
      "p13": "EDGE_0_13",
      "p14": "EDGE_0_14",
      "p15": "EDGE_0_15",
      "p16": "EDGE_0_16",
      "p17": "EDGE_0_17",
      "p18": "EDGE_0_18",
      "p19": "EDGE_0_19"
    },
    "schedule": {
      "feature_ids": [
        "EXCHANGE_TABLE",
        "RESOURCE_BUDGET",
        "EXCHANGE_TABLE",
        "RESOURCE_BUDGET"
      ],
      "hypothesis": "The schedule orders exchanges to avoid conflicts and preserve cardinality. The evidence supports the hypothesis that this schedule is optimal for the given resource constraints.",
      "falsifier": "If the schedule results in a violation of the sector weight caps or position bounds, then the hypothesis is falsified. The falsifier is the observed violation of constraints during execution."
    },
    "sharing": {
      "feature_ids": [
        "EXCHANGE_TABLE",
        "RESOURCE_BUDGET",
        "EXCHANGE_TABLE",
        "RESOURCE_BUDGET"
      ],
      "hypothesis": "The sharing of qubits between exchanges is managed to minimize resource usage. The evidence supports the hypothesis that this sharing is efficient and within resource limits.",
      "falsifier": "If the sharing results in resource exhaustion or constraint violations, then the hypothesis is falsified. The falsifier is the observed resource exhaustion or constraint violation."
    }
  }
}
```

## family1_n20_exit / context_only

Request hash: `bfd254609384b64fde36c419f5636f619a0383c6ef6fd5ea84e4d3fd57d1121b`. Status: ok.

```json
{
  "version": "data-guided-common-counter-v1",
  "parents": {
    "p1": 0,
    "p2": 1,
    "p3": 1,
    "p4": 1,
    "p5": 1,
    "p6": 1,
    "p7": 1,
    "p8": 1,
    "p9": 1,
    "p10": 1,
    "p11": 1,
    "p12": 1,
    "p13": 1,
    "p14": 1,
    "p15": 1,
    "p16": 1,
    "p17": 1,
    "p18": 1
  },
  "schedule": [
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17
  ],
  "groups": [
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1
  ],
  "preparation": "compiler_counter_dicke_v1",
  "depth": 1,
  "rationale": [
    {
      "feature_ids": [
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION",
        "CORRELATION"
      ],
      "decision": "select_edge_1_6"
    }
  ],
  "evidence": {
    "parent_edges": {
      "p1": "EDGE_1_2",
      "p2": "EDGE_1_3",
      "p3": "EDGE_1_4",
      "p4": "EDGE_1_5",
      "p5": "EDGE_1_6",
      "p6": "EDGE_1_7",
      "p7": "EDGE_1_8",
      "p8": "EDGE_1_9",
      "p9": "EDGE_1_10",
      "p10": "EDGE_1_11",
      "p11": "EDGE_1_12",
      "p12": "EDGE_1_13",
      "p13": "EDGE_1_14",
      "p14": "EDGE_1_15",
      "p15": "EDGE_1_16",
      "p16": "EDGE_1_17",
      "p17": "EDGE_1_18",
      "p18": "EDGE_1_19"
    },
    "schedule": {
      "feature_ids": [
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET",
        "RESOURCE_BUDGET"
      ],
      "hypothesis": "All edges in schedule are valid for exchange.",
      "falsifier": "None of the edges in the schedule violate cardinality constraints."
    },
    "sharing": {
      "feature_ids": [
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE"
      ],
      "hypothesis": "All exchanges are within the exchange table constraints.",
      "falsifier": "No exchange violates the exchange table bounds."
    }
  }
}
```

## family1_n20_exit / guided

Request hash: `742c64ebf02f0c284db8405761d3c21fb9dfd5f379fce364f20f6eec54b06685`. Status: ok.

```json
{
  "version": "data-guided-common-counter-v1",
  "parents": {
    "p1": 0,
    "p2": 1,
    "p3": 2,
    "p4": 3,
    "p5": 4,
    "p6": 5,
    "p7": 6,
    "p8": 7,
    "p9": 8,
    "p10": 9,
    "p11": 10,
    "p12": 11,
    "p13": 12,
    "p14": 13,
    "p15": 14,
    "p16": 15,
    "p17": 16,
    "p18": 17
  },
  "schedule": [
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17
  ],
  "groups": [
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1
  ],
  "preparation": "compiler_counter_dicke_v1",
  "depth": 1,
  "rationale": [
    {
      "feature_ids": [
        "CORRELATION",
        "SPECTRUM",
        "SPECTRUM"
      ],
      "decision": "selecting p16 as parent for p17 due to high correlation and low RMS in exchange features"
    },
    {
      "feature_ids": [
        "CORRELATION",
        "SPECTRUM",
        "SPECTRUM"
      ],
      "decision": "selecting p15 as parent for p16 due to high correlation and low RMS in exchange features"
    },
    {
      "feature_ids": [
        "CORRELATION",
        "SPECTRUM",
        "SPECTRUM"
      ],
      "decision": "selecting p14 as parent for p15 due to high correlation and low RMS in exchange features"
    },
    {
      "feature_ids": [
        "CORRELATION",
        "SPECTRUM",
        "SPECTRUM"
      ],
      "decision": "selecting p13 as parent for p14 due to high correlation and low RMS in exchange features"
    }
  ],
  "evidence": {
    "parent_edges": {
      "p1": "EDGE_1_2",
      "p2": "EDGE_1_3",
      "p3": "EDGE_1_4",
      "p4": "EDGE_1_5",
      "p5": "EDGE_1_6",
      "p6": "EDGE_1_7",
      "p7": "EDGE_1_8",
      "p8": "EDGE_1_9",
      "p9": "EDGE_1_10",
      "p10": "EDGE_1_11",
      "p11": "EDGE_1_12",
      "p12": "EDGE_1_13",
      "p13": "EDGE_1_14",
      "p14": "EDGE_1_15",
      "p15": "EDGE_1_16",
      "p16": "EDGE_1_17",
      "p17": "EDGE_1_18",
      "p18": "EDGE_1_19"
    },
    "schedule": {
      "feature_ids": [
        "RESOURCE_BUDGET",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE"
      ],
      "hypothesis": "The schedule orders exchanges to minimize shared qubit conflicts while maximizing correlation between adjacent edges",
      "falsifier": "If any two adjacent edges in the schedule share more than one qubit, the unitary will not be correctly implemented"
    },
    "sharing": {
      "feature_ids": [
        "RESOURCE_BUDGET",
        "EXCHANGE_TABLE",
        "EXCHANGE_TABLE"
      ],
      "hypothesis": "Each exchange is designed to be implemented with minimal shared qubits between adjacent exchanges",
      "falsifier": "If any exchange requires more than one shared qubit with its neighbors, the exchange sequence will not preserve cardinality"
    }
  }
}
```
