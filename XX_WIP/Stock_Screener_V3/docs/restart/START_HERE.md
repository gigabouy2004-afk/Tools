# V3_Charter Restart Folder

Use this folder as the single restart entry point for future Codex sessions.

Folder:

```text
D:\Tools\Stock_Screener_V3\docs\restart
```

Read in this order:

1. [05_v3_charter_restart_signoff_20260616.md](/D:/Tools/Stock_Screener_V3/docs/restart/05_v3_charter_restart_signoff_20260616.md)
2. [04_v3_charter_consolidated_engine_design.md](/D:/Tools/Stock_Screener_V3/docs/restart/04_v3_charter_consolidated_engine_design.md)
3. [01_v3_original_intent_and_handover.md](/D:/Tools/Stock_Screener_V3/docs/restart/01_v3_original_intent_and_handover.md)
4. [03_README.md](/D:/Tools/Stock_Screener_V3/docs/restart/03_README.md)
5. [02_current_session_handover.md](/D:/Tools/Stock_Screener_V3/docs/restart/02_current_session_handover.md)

Then verify branch state:

```powershell
cd D:\Tools\Stock_Screener_V3
git status --short --branch
git log --oneline --decorate -8
```

Expected branch state:

```text
## V3_Charter...origin/V3_Charter
```

Current restart-relevant commits:

- `bb50871 Record V1.6 charter revision hash`
- `9c11379 Advance master charter to V1.6`
- `5e8180a Record V1.5 charter revision hash`

Current restart baseline:

- `V3_Charter` is the only working branch baseline.
- `V1.6` of the consolidated charter is the current offline master document.
- The 2026-06-16 restart signoff is the low-token first-read document.
- `Stock_Engine3_Pythoncode.py` is accepted only as a seed scaffold, not a drop-in engine replacement.
- Current coding focus is integration of accepted manifest/slicing/EMA-high logic into the package and web app path.

These files are restart copies collected into one folder for convenience. If they ever drift, the canonical sources remain:

- [docs/charter/v3_original_intent_and_handover.md](/D:/Tools/Stock_Screener_V3/docs/charter/v3_original_intent_and_handover.md)
- [docs/handover/current_session_handover.md](/D:/Tools/Stock_Screener_V3/docs/handover/current_session_handover.md)
- [README.md](/D:/Tools/Stock_Screener_V3/README.md)
