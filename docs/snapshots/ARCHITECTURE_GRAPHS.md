# GTBS / G1 Architecture Graphs — Snapshot v0.3

Frozen diagrams for the L2 / L2.5 observational cognition stack.  
See [GTBS_SYSTEM_SNAPSHOT_v0.3.md](./GTBS_SYSTEM_SNAPSHOT_v0.3.md) for full context.

---

## 1. L2 pipeline graph

```mermaid
flowchart TB
    subgraph OBS["Observability Streams (append-only)"]
        SH[gtbs_shadow.jsonl]
        EC[ecology_metrics.jsonl]
        SI[singularity_metrics.jsonl]
        TX[gtbs_transactions.jsonl]
        FA[frozen_anchors.jsonl]
    end

    subgraph L2v01["L2 v0.1 Snapshot Semantics"]
        SNAP[GTBSSnapshot]
        INTERP[SemanticInterpreter]
        REND[GTBSL2Renderer]
    end

    subgraph L2v02["L2 v0.2 Temporal Semantics"]
        WIN[L2TemporalWindow]
        TRAJ[TrajectorySynthesizer]
    end

    subgraph L2v03["L2 v0.3 Fusion Semantics"]
        FIELD[CrossStreamField]
        COUP[SemanticCouplingEngine]
        FUSE[FusionSynthesizer]
    end

    subgraph L2v05["L2.5 Attractor Inference"]
        LATENT[field_to_latent]
        TOPO[stability_topology]
        ATT[GTBSL2AttractorReport]
    end

    SH --> SNAP
    EC --> SNAP
    SI --> SNAP
    SNAP --> INTERP --> REND

    SH --> WIN
    EC --> WIN
    SI --> WIN
    WIN --> TRAJ

    SH --> FIELD
    EC --> FIELD
    SI --> FIELD
    WIN --> FIELD
    FIELD --> COUP --> FUSE

    FUSE --> LATENT --> TOPO --> ATT

    REND --> OUT["Read-only narrative / JSON"]
    TRAJ --> OUT
    FUSE --> OUT
    ATT --> OUT
```

---

## 2. Observability stream graph

```mermaid
flowchart LR
    subgraph Runtime["Runtime / Interaction"]
        CAP[capture / interaction]
        MUT[mutation paths]
    end

    subgraph Hooks["Instrumentation Hooks"]
        P15[P1.5 shadow hook]
        P2[P2 capture boundary pilot]
    end

    subgraph Streams["Observability JSONL"]
        SHADOW[gtbs_shadow.jsonl]
        ECO[ecology_metrics.jsonl]
        SING[singularity_metrics.jsonl]
        TRANS[gtbs_transactions.jsonl]
        ANCH[frozen_anchors.jsonl]
    end

    subgraph Collectors["Phase Collectors"]
        PA[Phase A landscape]
        PB[Phase B singularity]
        PC[Phase C ecology]
    end

    CAP --> P15 --> SHADOW
    CAP --> P2 --> TRANS
    MUT -.->|read-only projection| PA
    PA --> SHADOW
    PA --> ANCH
    PB --> SING
    PC --> ECO

    SHADOW --> L2["L2 / L2.5 stack"]
    ECO --> L2
    SING --> L2
    TRANS --> L2
    ANCH --> L2
```

---

## 3. Attractor field diagram

```mermaid
flowchart TB
    subgraph Fusion["L2 v0.3 Fusion Output"]
        CM[CrossStreamCouplingMatrix]
        CS[coupling_signals]
    end

    subgraph Compression["Coupling Compression"]
        BEH["A-BEH behavioral basin<br/>shadow × ecology"]
        INS["A-INS instability basin<br/>ecology × singularity"]
        SELF["A-SELF self-referential basin<br/>shadow × singularity"]
    end

    subgraph Basin["Basin Estimation"]
        BD["basin_depth = weighted(NCR, CPX, RSCI, ODC)"]
    end

    subgraph Classify["Stability Classification"]
        ST[stable / metastable / collapsing / emerging]
    end

    subgraph Field["AttractorField"]
        AF[attractors + global_entropy + coupling_density]
        REG[field_regime: diffuse / clustered / locked / bifurcating]
    end

    subgraph Topology["TopologySignature"]
        TC[cluster_count]
        DOM[dominant_attractor]
        EG[entropy_gradient]
        LI[lock_in_probability]
    end

    CM --> BEH
    CM --> INS
    CM --> SELF
    BEH --> BD
    INS --> BD
    SELF --> BD
    BD --> ST --> AF --> REG
    AF --> TC
    AF --> DOM
    AF --> EG
    AF --> LI

    LI --> RISK["risk_surface (observational only)"]
    REG --> INTERP["interpretation (S11/S12: not action)"]
```

---

## 4. Governance isolation boundary

```mermaid
flowchart TB
    subgraph ALLOWED["L2 / L2.5 — ALLOWED"]
        READ[Read observability streams]
        INTERP[Generate narratives / JSON reports]
        CLI[CLI report scripts]
    end

    subgraph FORBIDDEN["FORBIDDEN — Governance Isolation"]
        CDG[CDG gradient controller]
        GATE[GTBS gatekeeper enforcement]
        RUN[Runtime mutation paths]
        POL[policy generation]
        MB[mutation_budget]
    end

    OBS[(observability JSONL)] --> READ --> INTERP --> CLI

    INTERP -.->|MUST NOT| CDG
    INTERP -.->|MUST NOT| GATE
    INTERP -.->|MUST NOT| RUN
    INTERP -.->|MUST NOT| POL
    INTERP -.->|MUST NOT| MB

    style FORBIDDEN fill:#fee,stroke:#c00
    style ALLOWED fill:#efe,stroke:#060
```
