# Blueprint Prefix Audit (code-grounded)

I ran a code-level audit of blueprint definitions and their registrations in `request_tracker_utils` to capture the current state and plan normalization.

| Blueprint module | Blueprint name | Registration prefix (create_app) | Notes |
|------------------|----------------|----------------------------------|-------|
| `routes/label_routes.py` | `label_routes.bp` | `/labels` | Registered with explicit prefix in `create_app()` |
| `routes/tag_routes.py` | `tag_routes.bp` | (no prefix / root) | Registered at app root in `create_app()` to preserve existing client paths like `/next-asset-tag` |
| `routes/device_routes.py` | `device_routes.bp` | `/devices` | Registered with explicit prefix in `create_app()` |
| `routes/student_routes.py` | `student_routes.bp` | `/students` | Registered with explicit prefix in `create_app()` |
| `routes/asset_routes.py` | `asset_routes.bp` | `/assets` | Registered with explicit prefix in `create_app()` |

Recommendation: Normalize `tag_routes` to register with `url_prefix='/tags'` and update any external callers or clients that expect the root-level tag endpoints, or leave it mounted at root if backward compatibility with existing webhooks and clients is required. Add a regression test in `tests/integration/test_blueprint_prefixes.py` as specified in tasks T025.
