# Registry Refactor Plan

This historical plan was superseded by the registry-driven service architecture now implemented in `src/rakkib/data/registry.yaml`, `src/rakkib/steps/services.py`, and `src/rakkib/hooks/services.py`.

Current service additions should be made through the registry, templates, and named hooks rather than service-specific dispatch branches. Keep tests and snapshot fixtures aligned with rendered output whenever registry behavior changes.
