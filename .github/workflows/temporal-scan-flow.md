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
    F1 --> SD & AI & FW & DNS & OS & SF & BD

    subgraph T1["🔍 Tier 1 — Discovery  ·  all parallel"]
        direction TB
        SD[RunSubdomainDiscoveryActivity]
        AI[RunAmassIntelDiscoveryActivity]
        FW[RunFirewallVPNScanActivity]
        DNS[RunDNSSecurityActivity]
        OS["RunGenericTaskActivity · osint"]
        SF["RunGenericTaskActivity · spiderfoot_scan
─ requires yaml spiderfoot_scan block"]
        BD["RunGenericTaskActivity · subdomain_discovery
uses_tools: [baddns]"]
    end

    SD & AI & FW & DNS & OS & SF & BD --> J1(( ))
    J1 --> PDR[ParseDiscoveryResultsActivity]
    PDR --> CP1{{"⏸ Pause Checkpoint"}}

    CP1 --> F2(( ))
    F2 --> HC & PS & VD

    subgraph T2["🌐 Tier 2 — Endpoint Discovery  ·  all parallel"]
        direction TB
        HC["SeedEndpointsForCrawlActivity → RunHTTPCrawlActivity"] --> PHC[ParseHTTPCrawlResultsActivity]
        PS[RunPortScanActivity]
        VD["RunVigoliumDiscoveryActivity
─ requires vigolium_discovery.run_vigolium_discovery"]
    end

    PHC & PS & VD --> PT2[Dispatch tier_2 plugins]
    PT2 --> F3(( ))
    F3 --> FU & SS

    subgraph T3["🔗 Tier 3 — URL Fetching + Screenshot  ·  parallel"]
        direction TB
        FU[RunFetchURLActivity]
        SS[RunScreenshotActivity]
    end

    FU & SS --> DFF

    subgraph T4["📁 Tier 4 — Directory & File Fuzzing  ·  sequential"]
        direction TB
        DFF[RunDirFileFuzzActivity] --> PFF[ParseFuzzResultsActivity]
    end

    PFF --> PER[ParseEnumerationResultsActivity]
    PER --> CP2{{"⏸ Pause Checkpoint"}}

    CP2 --> F4(( ))
    F4 --> WAD & WD & SEC & VA

    subgraph T5["🔬 Tier 5 — Analysis  ·  all parallel"]
        direction TB
        WAD[RunWebAPIDiscoveryActivity]
        WD[RunWAFDetectionActivity]
        SEC[RunSecretScanningActivity]
        VA["RunVigoliumAnalysisActivity
─ requires vigolium_analysis.run_vigolium_analysis"]
    end

    WAD & WD & SEC & VA --> J3(( ))
    J3 --> PAR[ParseAnalysisResultsActivity]
    PAR --> CP3{{"⏸ Pause Checkpoint"}}

    CP3 --> NUC

    subgraph T6["🎯 Tier 6 — Security Assessment"]
        direction TB
        subgraph NP["NucleiPlannerWorkflow · child workflow · runs first"]
            direction TB
            NUC[RunNucleiActivity / vuln stage chain]
        end
        NUC --> G6(( ))
        G6 --> WB & VS
        WB[RunWAFBypassActivity]
        VS["RunVigoliumScanActivity
─ requires vulnerability_scan.run_vigolium"]
    end

    WB & VS --> PASM[ParseAssessmentResultsActivity]
    PASM --> CP4{{"⏸ Pause Checkpoint"}}

    CP4 --> CV

    subgraph T7["🧠 Tier 7 — Intelligence  ·  sequential"]
        direction TB
        CV[CorrelateVulnerabilitiesActivity]
        EC[EnrichScanCVEsActivity]
        CR[CalculateRiskScoresActivity]
        GI[GenerateImpactAssessmentActivity]
        SG[SyncGraphActivity]
        APME["RunGenericTaskActivity · run_apme"]
        CV --> EC --> CR --> GI --> SG --> APME
    end

    APME --> SN[SendScanNotificationActivity]
    SN --> DONE([✓ Scan Complete])
```

## Execution notes

| Symbol | Meaning |
|--------|---------|
| `(( ))` | Fork / Join — marks where parallel branches split or rejoin |
| `{{"⏸ …"}}` | Pause checkpoint — workflow blocks here on a `pause` signal until `resume` |
| `─ requires …` | Node only runs when the noted YAML flag is present and true |
| Nested subgraph | `NucleiPlannerWorkflow` runs as a child workflow with its own independent Temporal history |

## Tier boundaries

| Tier | Parallelism | Gate into next tier |
|------|-------------|---------------------|
| Step 0 | Sequential | `LoadCheckpointActivity` |
| Tier 1 | All parallel (`asyncio.gather`) | `ParseDiscoveryResultsActivity` |
| Tier 2 | All parallel (`asyncio.gather`) | `ParseHTTPCrawlResultsActivity` + `RunPortScanActivity` + optional `RunVigoliumDiscoveryActivity` + tier 2 plugin dispatch |
| Tier 3 | Parallel | `RunFetchURLActivity` + `RunScreenshotActivity` |
| Tier 4 | Sequential | `ParseFuzzResultsActivity` |
| -> | | `ParseEnumerationResultsActivity` |
| Tier 5 | All parallel (`asyncio.gather`) | `ParseAnalysisResultsActivity` |
| Tier 6 | `NucleiPlannerWorkflow` first, then concurrent activities | `ParseAssessmentResultsActivity` |
| Tier 7 | Sequential chain | `CorrelateVulnerabilitiesActivity` -> `EnrichScanCVEsActivity` -> `CalculateRiskScoresActivity` -> `GenerateImpactAssessmentActivity` -> `SyncGraphActivity` -> `run_apme` |

## http_crawl dependency note

`http_crawl` runs in Tier 2 and populates the endpoint database via `httpx`. Its results directly feed:
- Tier 3 `fetch_url`
- Tier 3 `screenshot`
- Tier 4 `dir_file_fuzz`

This is why the pipeline waits for Tier 2 before continuing.

## Workflow inventory

The diagram above covers the full-scan path implemented by `MasterScanWorkflow`. The same module also defines these durable workflows:

| Workflow | Role |
|----------|------|
| `NucleiPlannerWorkflow` | Child workflow for vulnerability scanning; runs scanner stages sequentially |
| `SubScanWorkflow` | Runs one or more subdomain-scoped tasks using the same tier model |
| `StressTestWorkflow` | Sequential endpoint/tool stress execution with `kill_switch` cancellation |
| `MonitoringWorkflow` | Periodic per-domain monitoring launched by Temporal schedules |
| `ScheduledScanWorkflow` | Creates scan context, then launches `MasterScanWorkflow` as a child workflow |
| `StartupSyncWorkflow` | One-shot startup maintenance tasks such as graph sync and CVE refresh |
| `GoExecutorTaskWorkflow` | Routes heavy command execution to the dedicated Go worker queue |
| `ApmeTaskWorkflow` | On-demand attack-path modeling workflow started from the API |
| `IdentityEnrichmentWorkflow` | OSINT enrichment for names and emails |
| `GeoLocalizeWorkflow` | Geolocation enrichment for discovered IPs |
| `HackerOneImportWorkflow` | Bulk program import from HackerOne |
| `HackerOneSyncBookmarkedWorkflow` | Syncs bookmarked HackerOne programs |
| `ProxyFetchWorkflow` | Fetches and validates proxy lists in the background |
