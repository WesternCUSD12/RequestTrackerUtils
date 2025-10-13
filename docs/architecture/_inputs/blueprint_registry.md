# Blueprint Registry Snapshot

Captured: 2025-10-13
Source: `request_tracker_utils/__init__.py`

| Order | Blueprint Module | Object              | URL Prefix                                        | Notes                                                                      |
| ----- | ---------------- | ------------------- | ------------------------------------------------- | -------------------------------------------------------------------------- |
| 1     | `label_routes`   | `label_routes.bp`   | _None_ (defaults to `/labels` routes as declared) | Routes currently mounted at root; standardization planned in User Story 2. |
| 2     | `tag_routes`     | `tag_routes.bp`     | _None_                                            | Asset tag management endpoints mounted at root.                            |
| 3     | `device_routes`  | `device_routes.bp`  | `/devices`                                        | Device check-in/out blueprint uses explicit prefix.                        |
| 4     | `student_routes` | `student_routes.bp` | _None_                                            | Student device tracking endpoints mounted at root.                         |
| 5     | `asset_routes`   | `asset_routes.bp`   | _None_                                            | Asset batch creation endpoints mounted at root.                            |

## Observations

- Only `device_routes` currently declares an explicit `url_prefix`.
- Remaining blueprints are registered at the application root, increasing collision risk.
- Documentation task T017 will link this table in subsystem architecture docs; implementation tasks in Phase 4 will normalize prefixes and update this registry.
