# r3ngine Temporal Scan Flow
_Full pipeline — all YAML config keys enabled_

```mermaid
flowchart TD
    START([▶ Scan Initiated]) --> TP

    subgraph S0["⚙️ Step 0 — Target Setup"]
        direction TB
        TP[TargetProfilingActivity] --> LC[LoadCheckpointActivity]
    end

    LC --> F1(( ))
    F1 --> SD & AI & FW & OS & SF

    subgraph T1["🔍 Tier 1 — Discovery  ·  all parallel"]
        direction TB
        SD[RunSubdomainDiscoveryActivity]
        AI[RunAmassIntelDiscoveryActivity]
        FW[RunFirewallVPNScanActivity]
        OS["RunGenericTaskActivity · osint"]
        SF["RunGenericTaskActivity · spiderfoot_scan\n─ requires yaml spiderfoot_scan block"]
    end

    SD & AI & FW & OS & SF --> J1(( ))
    J1 --> PDR[ParseDiscoveryResultsActivity]
    PDR --> CP1{{"⏸ Pause Checkpoint"}}

    CP1 --> F2(( ))
    F2 --> HC & PS & SS

    subgraph T2["🌐 Tier 2 — HTTP Crawl · Port Scan · Screenshot  ·  all parallel"]
        direction TB
        HC["RunHTTPCrawlActivity\n─ global config · feeds Tiers 3 & 4"] --> PHC[ParseHTTPCrawlResultsActivity]
        PS[RunPortScanActivity]
        SS[RunScreenshotActivity]
    end

    PHC & PS & SS --> J2(( ))

    J2 --> FU

    subgraph T3["🔗 Tier 3 — URL Fetching  ·  sequential"]
        direction TB
        FU[RunFetchURLActivity]
    end

    FU --> DFF

    subgraph T4["📁 Tier 4 — Directory & File Fuzzing  ·  sequential"]
        direction TB
        DFF[RunDirFileFuzzActivity] --> PFF[ParseFuzzResultsActivity]
    end

    PFF --> PER[ParseEnumerationResultsActivity]
    PER --> CP2{{"⏸ Pause Checkpoint"}}

    CP2 --> F3(( ))
    F3 --> WAD & WD & SEC

    subgraph T5["🔬 Tier 5 — Analysis  ·  all parallel"]
        direction TB
        WAD[RunWebAPIDiscoveryActivity]
        WD[RunWAFDetectionActivity]
        SEC[RunSecretScanningActivity]
    end

    WAD & WD & SEC --> J3(( ))
    J3 --> PAR[ParseAnalysisResultsActivity]
    PAR --> CP3{{"⏸ Pause Checkpoint"}}

    CP3 --> F4(( ))
    F4 --> NUC & WB & BF

    subgraph T6["🎯 Tier 6 — Assessment  ·  all parallel"]
        direction TB
        subgraph NP["NucleiPlannerWorkflow · child workflow"]
            direction TB
            NUC[RunVulnerabilityScanActivity]
        end
        WB[RunWAFBypassActivity]
        BF[RunBruteForceScanActivity]
    end

    NUC & WB & BF --> J4(( ))
    J4 --> PASM[ParseAssessmentResultsActivity]
    PASM --> CP4{{"⏸ Pause Checkpoint"}}

    CP4 --> CV

    subgraph T7["🧠 Tier 7 — Intelligence  ·  sequential"]
        direction TB
        CV[CorrelateVulnerabilitiesActivity] --> CR[CalculateRiskScoresActivity]
        CR --> GI["GenerateImpactAssessmentActivity\n─ requires enable_ai_impact_analysis: true"]
        GI --> SG["SyncGraphActivity  ·  APME + Neo4j\n─ requires attack_path_modeling.enabled: true"]
    end

    SG --> SN[SendScanNotificationActivity]
    SN --> DONE([✓ Scan Complete])
```

## Execution notes

| Symbol | Meaning |
|--------|---------|
| `(( ))` | Fork / Join — marks where parallel branches split or rejoin |
| `{{"⏸ …"}}` | Pause checkpoint — workflow blocks here on a `pause` signal until `resume` |
| `─ requires …` | Node only runs when the noted YAML flag is present and true |
| Nested subgraph | `NucleiPlannerWorkflow` runs as a **child workflow** with its own independent Temporal history |

## Tier boundaries

| Tier | Parallelism | Gate into next tier |
|------|-------------|---------------------|
| Step 0 | Sequential | `LoadCheckpointActivity` |
| Tier 1 | All parallel (`asyncio.gather`) | `ParseDiscoveryResultsActivity` |
| Tier 2 | All parallel (`asyncio.gather`) | All of `ParseHTTPCrawlResults`, `RunPortScan`, `RunScreenshot` |
| Tier 3 | Sequential | `RunFetchURLActivity` |
| Tier 4 | Sequential | `ParseFuzzResultsActivity` |
| → | | `ParseEnumerationResultsActivity` |
| Tier 5 | All parallel (`asyncio.gather`) | `ParseAnalysisResultsActivity` |
| Tier 6 | All parallel (`asyncio.gather`) | `ParseAssessmentResultsActivity` |
| Tier 7 | Sequential chain | `SyncGraphActivity` |

## http_crawl — global config note

`http_crawl` runs in **Tier 2** and populates the endpoint database via `httpx`. Its results are the foundation for:
- **Tier 3** (`fetch_url`) — harvests URLs and applies GF patterns against crawled endpoints
- **Tier 4** (`dir_file_fuzz`) — fuzzes directories against the URL set built in Tiers 2–3

This is why Tiers 3 and 4 are sequential rather than parallel with Tier 2.
