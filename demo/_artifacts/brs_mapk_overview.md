### Biology

**MEK1** phosphorylates **ERK2** on its Thr-X-Tyr motif in the
cytoplasm. Phospho-ERK then imports through nuclear pore
complexes; nuclear phosphatases reset it. MEK is active-site
limited — one ERK at a time.

### Bigraph encoding

- **Place graph**: `Cell ⊃ Cytoplasm ⊃ {Nucleus, ERLumen, MEK, ERK, pERK}`.
- **Link graph**: one shared edge per MEK·pERK complex.
- **Sorts**: `Cell`, `Compartment`, `MEK`, `ERK`, `pERK` + kind
  tags `Cytoplasm`, `Nucleus`, `ERLumen`.

### Rules (Gillespie SSA, propensity = `k × |matches|`)

- **`phosphorylate`** (k = 2.0): co-located free MEK + free ERK bind via a fresh edge.
- **`dissociate`** (k = 0.5): MEK·pERK → free MEK + free pERK.
- **`dephosphorylate`** (k = 0.4): nuclear pERK → ERK (DUSP-style reset).
- **`translocate_erk_in / out`** (k = 1.0 each): free ERK between cytoplasm and child compartment.
- **`translocate_perk_in`** (k = 2.0): free pERK, cytoplasm → nucleus (active import).
- **`translocate_perk_out`** (k = 0.1): free pERK, nucleus → cytoplasm (slow leak).

The **20-fold in/out asymmetry** drives nuclear pERK accumulation
— the signal itself.

### Why bigraphs?

Compartment-only models capture *where*; reaction-network models
capture *what's bound*. Bigraphs unify both — a single redex
constrains place AND link in one step (e.g. `phosphorylate`
requires co-location AND no prior bond). See
`references/brs_mapk.md` for citations.
