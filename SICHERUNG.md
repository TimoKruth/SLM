# Archive policy and current backups

All experiments predating the fresh 47-source restart are **DEPRECATED**. Retain their reports, raw results, checkpoints and diagnostic artifacts only in ZIP/ZIP64 archives. Do not persist unpacked historical results or resume their controllers. This policy supersedes the historical notes inside those archives.

[The archive index](archives/README.md) links the curated report ZIP and records checksums for the complete private archive. Complete local payloads reside at `/Users/timokruth/SLM-Sicherungen/2026-09-16-legacy-retired/`; earlier backups under `/Users/timokruth/SLM-Sicherungen/2026-09-11/` are preserved. The private archive is local, not an off-device backup.

Each private ZIP has a member manifest with SHA256/size/type plus an archive SHA256. All members were read back and checked, a model checkpoint was restored and rehashed, and the Git bundle was restored with every archived worktree commit verified. Original payload bytes are preserved under a DEPRECATED notice. The code ZIP contains tracked source snapshots and all named branches/tags, including refs retaining detached worktree commits.

Only after verification were the matching unpacked run paths removed. `tools/retire_legacy_results.py` repeats the archive hash and complete source-inventory/hash check before deletion. It refuses changed or unarchived content and preserves the live monitoring directory. The obsolete launch-agent configurations were separately archived before unloading/removal.

For historical reference, read ZIP members directly where possible. Restore into an explicit temporary directory only when needed, then delete the temporary unpacked copy. Never restore over the active project or follow archived start instructions automatically. Manifests, hashes and current migration indexes can remain unpacked; they do not contain old benchmark results.

Public Git includes the curated deprecated-report ZIP, current code, the fresh plan and aggregate preparation evidence. Raw corpora, model weights, generated responses and system-wide process logs remain private. Existing Git history has not been rewritten. Corpus input directories remain for provenance; live PowerWatch telemetry remains operational. New 47-source results may remain unpacked while active, with any eventual retirement following the same verification-first process.
