# TA / SC / BAR Archive

Live: https://stephenshorton.github.io/rts-unit-catalog/

A visual catalog of three Chris Taylor RTS generations:

1. **Total Annihilation** (1997) — ARM & CORE
2. **Supreme Commander / Forged Alliance** (2007) — UEF, Cybran, Aeon, Seraphim
3. **Beyond All Reason** (2023) — Armada, Cortex, Legion

Portraits first. Click a unit for a full page. The header switches eras; **Lineage** lines up the same job across 1997 → 2007 → now.

## Use it locally

Open `catalog/index.html`, or after clone:

```powershell
Start-Process (Resolve-Path .\catalog\index.html)
```

`/` focuses search. Esc leaves a unit page.

## Database

| Set | Units |
|---|---|
| Total Annihilation (base + CC + BT) | 278 |
| Supreme Commander + FA (no Nomads) | 407 |
| Beyond All Reason | 569 |
| **Total** | **1,254** (1,250 with portraits) |

- `data/units.json`
- `data/units.csv`

## Rebuild

Clones of the source repos live in `vendor/` (gitignored). Once those exist:

```powershell
python .\scripts\build_catalog.py
```

Sources:

- TA: [coreprime/reference-ta](https://github.com/coreprime/reference-ta)
- SC: [FAForever etfreeman-db](https://faforever.github.io/etfreeman-db/) + [FAForever/fa](https://github.com/FAForever/fa) icons
- BAR: [paul/BAR-units-db](https://github.com/paul/BAR-units-db)

Art and stats remain copyright of the original publishers and BAR contributors. This repo is a personal reference, not a redistribution of the games.
