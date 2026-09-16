# Deprecated experiment archives

All reports and results preceding the fresh 47-source restart are **DEPRECATED**, retained only for reference. They are not current baselines or evidence for selecting the fresh model.

- [Curated report ZIP](deprecated-reports-2026-09-16.zip): 115 report/plan/evidence files, 344,559 bytes. Every entry is marked deprecated in the ZIP manifest and stored beneath `deprecated/`; original contents are preserved.
- [Archive index and hashes](legacy-index.json): 70 private ZIP64 archives, 266,613,611,659 bytes (248.30 GiB), covering 68 run paths, all 27 historical worktree source snapshots/commits, and three obsolete launch-agent configurations.
- Complete private archive location: `/Users/timokruth/SLM-Sicherungen/2026-09-16-legacy-retired/`. Full weights, raw responses and process logs were not uploaded to GitHub.

All ZIP members passed read-back hash/CRC verification. A checkpoint restore and a Git-bundle restore covering every archived worktree commit passed. Source content was rechecked immediately before pruning; 68 run paths and 26 old worktrees were removed. The three obsolete launch agents were unloaded after archiving. The active main checkout, corpus inputs and live PowerWatch monitoring remain.

The public ZIP contains tracked reports and the final matched-75M, conservative and JEPA report exports. Other complete branch-specific reports and raw evidence remain in the private ZIPs. Previous local September 11 backups remain untouched. Existing Git history is preserved; this migration changes the current tree and local artifact layout, not historical commits.

Read members directly from ZIP where possible. Any necessary unpacking must use a temporary reference directory that is removed afterward. See [the archive policy](../SICHERUNG.md). The new active plan is [fresh 47-source training](../FRESH_47_TRAINING.md).

Public report ZIP SHA256: `6a7d5726e62fa38990833b266f8c525d7131305c883a1f427f6ed4b785cdc07c`.
