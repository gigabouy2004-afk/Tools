# LiveScreener V7/V8 historical baseline

This branch preserves the reviewed V7/V8 session lineage.

- `Live_Scanner_v7.py` is the final recovered V7 snapshot.
- `Live_Scanner_v8.py` is the canonical V8 snapshot and the preferred file for
  reviewing automatic live-session candle handling.
- `archive/v8_session_variants/` contains noncanonical V8 work-session files.

Install the declared runtime dependencies and run the deterministic checks:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p "test_*.py" -v
```

See [`docs/BASELINE_V7_V8.md`](docs/BASELINE_V7_V8.md) for source checksums,
session disposition, review findings, and known limitations.
