# Shutdown and Cleanup Protocols

This document details the shutdown sequences, resource cleanups, file descriptor management, and failure recovery protocols across RepoPeek's runtime processes.

---

## 1. Process Termination Overview

| Process / Mode | Shutdown Trigger | Cleanup Sequence | Lingering Risk |
|---|---|---|---|
| **CLI Query Mode** | Script execution completes | Synchronous return; Python runtime closes open files and unlinks temporary objects. | None. Stateless execution. |
| **Interactive Web Viewer** | User presses `Ctrl+C` (`SIGINT`) | `KeyboardInterrupt` caught in `cli.main()`; calls `server.server_close()`. | Bound socket port might briefly remain in `TIME_WAIT` if forcibly killed (`SIGKILL`). |
| **MCP Server Mode** | Client closes `stdin` (EOF) or terminates parent process | `sys.stdin` loop breaks; process exits cleanly. | None. Standard stdio protocol shutdown. |
| **Incremental Watch Daemon** | User presses `Ctrl+C` or calls `watcher.stop()` | Sets `_stop_event.set()`; finishes any in-flight file sync; cleans state. | None. In-flight file sync completes before loop exit. |
| **Atomic Graph Build** | Indexing completes or unhandled exception occurs | `save_canonical_graph()` moves staging directory or cleans `.tmp_build_<uuid>`. | On Windows, active virus scanners or IDE indexing can lock `.tmp_old_*` folders, leaving transient directories. |

---

## 2. Resource Cleanup Protocols

### SQLite Database Connections
In [`repopeek/storage/sqlite_cache.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/storage/sqlite_cache.py):
- Every SQLite query and build function uses `try...finally: conn.close()` blocks.
- Transactions are committed explicitly (`conn.commit()`) before connection closure.
- Temporary database building uses `PRAGMA synchronous = OFF; PRAGMA journal_mode = MEMORY;` during initial population to avoid leaving trailing `-wal` or `-shm` files on disk.

### Staging Directory and Temporary Files Cleanup
In [`repopeek/storage/json_store.py:save_canonical_graph`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/storage/json_store.py#L78):
1. **Staging Directory Creation:** `.tmp_build_<uuid12>` is created in the parent of the output directory.
2. **Atomic Swap:**
   - If target `output_dir` already exists:
     - Renames `output_dir` -> `.tmp_old_<uuid12>`.
     - Renames `.tmp_build_<uuid12>` -> `output_dir`.
     - Deletes `.tmp_old_<uuid12>` via `shutil.rmtree()`.
3. **Exception Safety:**
   - If an unhandled exception occurs while building or serializing:
     - The staging directory `.tmp_build_<uuid12>` is purged in the `except` block.
     - The original `output_dir` remains intact and unmodified.
4. **Windows File Lock Recovery:**
   - On Windows, if `shutil.rmtree(.tmp_old_<uuid>)` encounters an `OSError` (e.g. file lock from an antivirus scanner or IDE indexer):
     - The error is logged as a warning; the directory remains marked `.tmp_old_*` and does not prevent the application from succeeding.

### Thread Termination
In [`repopeek/viewer/server.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/viewer/server.py):
- The `ThreadingHTTPServer` sets `self.daemon_threads = True`.
- When the main thread exits upon receiving `KeyboardInterrupt`, worker HTTP threads terminate automatically without deadlock.
