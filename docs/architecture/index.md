# Architecture Documentation Hub

_Last updated: 2025-10-13_

## Purpose

This index anchors the subsystem documentation required by the documentation-first workflow for feature `002-ensure-my-flask`. Each entry links to evidence-backed references developers must review before touching code.

## Subsystem Guides

| Subsystem      | Document                                                   | Primary Owners     | Evidence Inputs                    |
| -------------- | ---------------------------------------------------------- | ------------------ | ---------------------------------- |
| Assets         | [docs/architecture/assets.md](./assets.md)                 | Feature Team       | Tree snapshot, Blueprint registry  |
| Labels         | [docs/architecture/labels.md](./labels.md)                 | Feature Team       | Tree snapshot, Blueprint registry  |
| Devices        | [docs/architecture/devices.md](./devices.md)               | Feature Team       | Tree snapshot, Blueprint registry  |
| Students       | [docs/architecture/students.md](./students.md)             | Feature Team       | Tree snapshot, Blueprint registry  |
| Tags           | [docs/architecture/tags.md](./tags.md)                     | Feature Team       | Tree snapshot, Blueprint registry  |
| Integrations   | [docs/architecture/integrations.md](./integrations.md)     | Integrations Guild | Research notes, Blueprint registry |
| Infrastructure | [docs/architecture/infrastructure.md](./infrastructure.md) | Platform Team      | Config matrix, Tree snapshot       |

## Evidence Inputs

- [`docs/architecture/_inputs/request_tracker_utils_tree.txt`](./_inputs/request_tracker_utils_tree.txt)
- [`docs/architecture/_inputs/blueprint_registry.md`](./_inputs/blueprint_registry.md)
- [`docs/configuration/current_env_matrix.md`](../configuration/current_env_matrix.md)

## Documentation-First Workflow

1. Start from this index to locate relevant subsystem guides.
2. Update subsystem docs **before** modifying routes, utilities, templates, or scripts.
3. Embed new evidence captures (_tree snapshots, command outputs, diagrams_) into `_inputs/` with timestamps.
4. Cross-link changes in `specs/002-ensure-my-flask/quickstart.md` and `README.md` once subsystem docs are populated (see tasks T017–T018).

## Review Checklist

- Every merge request touching `request_tracker_utils/` must cite the affected subsystem doc.
- Subsystem docs must reference the latest evidence captures by filename.
- Deviations from documented standards require follow-up entries in `specs/002-ensure-my-flask/plan.md` risk register.
