\# Q2 Procurement Deduplication Experiment Results



\## Corpus Profile



Total notices: 12000



Total portals: 260



Total labelled pairs: 900



Same-labelled pairs: 279



Different-labelled pairs: 621



Missing values: 0



Duplicate notice IDs: 0



\## Retrieval Experiment



Representation: Character 5-grams



MinHash permutations: 128



Retrieval method: MinHash LSH



\## Threshold Sweep



| Threshold | Same Recall | Different Survival | Mean Candidates | Candidate Reduction |

|---|---:|---:|---:|---:|

| 0.30 | 97.13% | 86.47% | 10334.86 | 13.88% |

| 0.40 | 88.89% | 69.08% | 7475.35 | 37.71% |

| 0.50 | 77.42% | 56.84% | 4492.37 | 62.56% |

| 0.60 | 54.12% | 28.34% | 1758.32 | 85.35% |

| 0.70 | 39.07% | 11.76% | 682.79 | 94.31% |

| 0.80 | 35.13% | 3.70% | 134.82 | 98.88% |



\## PostgreSQL Persistence



Notices loaded: 12000



Portals loaded: 260



Tables created:



\- portals

\- notices

\- notice\_signatures

\- retrieval\_runs

\- retrieval\_candidates



Indexes created:



\- idx\_notices\_portal\_id

\- idx\_notices\_published\_at

\- idx\_notices\_closing\_date

\- idx\_candidates\_query\_notice

\- idx\_candidates\_candidate\_notice



\## Query Performance



| Query | Access Method | Execution Time |

|---|---|---:|

| Filter by portal P094 | Bitmap Index Scan + Bitmap Heap Scan | 0.733 ms |

| Filter by published date | Sequential Scan | 1.209 ms |

| Group by portal | Index Only Scan + GroupAggregate | 0.962 ms |

| Body search using ILIKE | Sequential Scan | 248.322 ms |



\## Generated Visuals



\- threshold\_recall\_plot.png

\- threshold\_candidate\_plot.png

