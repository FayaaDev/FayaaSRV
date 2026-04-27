uthentik-worker  | 2026-04-27 20:19:05 [info     ] Migration needs to be applied  migration=tenant_files.py
authentik-worker  | 2026-04-27 20:19:05 [info     ] releasing database lock
authentik-worker  | Traceback (most recent call last):
authentik-worker  |   File "<frozen runpy>", line 198, in _run_module_as_main
authentik-worker  |   File "<frozen runpy>", line 88, in _run_code
authentik-worker  |   File "/manage.py", line 43, in <module>
authentik-worker  |     run_migrations()
authentik-worker  |   File "/lifecycle/migrate.py", line 103, in run_migrations
authentik-worker  |     migration.run()
authentik-worker  |   File "/lifecycle/system_migrations/tenant_files.py", line 18, in run
authentik-worker  |     TENANT_MEDIA_ROOT.mkdir(parents=True)
authentik-worker  |   File "/usr/local/lib/python3.12/pathlib.py", line 1311, in mkdir
authentik-worker  |     os.mkdir(self, mode)
authentik-worker  | PermissionError: [Errno 13] Permission denied: '/media/public'
authentik-worker exited with code 1
authentik-server  | {"event": "Loaded config", "level": "debug", "logger": "authentik.lib.config", "timestamp": 1777321147.7275002, "file": "/authentik/lib/default.yml"}
authentik-server  | {"event": "Loaded environment variables", "level": "debug", "logger": "authentik.lib.config", "timestamp": 1777321147.7315807, "count": 11}
authentik-server  | {"event": "Starting authentik bootstrap", "level": "info", "logger": "authentik.lib.config", "timestamp": 1777321148.977729}
authentik-server  | {"event": "PostgreSQL connection successful", "level": "info", "logger": "authentik.lib.config", "timestamp": 1777321149.0242727}
authentik-server  | {"event": "Redis Connection successful", "level": "info", "logger": "authentik.lib.config", "timestamp": 1777321149.0367699}
authentik-server  | {"event": "Finished authentik bootstrap", "level": "info", "logger": "authentik.lib.config", "timestamp": 1777321149.0380611}
authentik-server  | 2026-04-27 20:19:09 [info     ] waiting to acquire database lock
authentik-server  | 2026-04-27 20:19:09 [info     ] Migration needs to be applied  migration=tenant_files.py
authentik-server  | 2026-04-27 20:19:09 [info     ] releasing database lock
authentik-server  | Traceback (most recent call last):
authentik-server  |   File "<frozen runpy>", line 198, in _run_module_as_main
authentik-server  |   File "<frozen runpy>", line 88, in _run_code
authentik-server  |   File "/manage.py", line 43, in <module>
authentik-server  |     run_migrations()
authentik-server  |   File "/lifecycle/migrate.py", line 103, in run_migrations
authentik-server  |     migration.run()
authentik-server  |   File "/lifecycle/system_migrations/tenant_files.py", line 18, in run
authentik-server  |     TENANT_MEDIA_ROOT.mkdir(parents=True)
authentik-server  |   File "/usr/local/lib/python3.12/pathlib.py", line 1311, in mkdir
authentik-server  |     os.mkdir(self, mode)
authentik-server  | PermissionError: [Errno 13] Permission denied: '/media/public'
authentik-server exited with code 1
authentik-worker  | {"event": "Not running as root, disabling permission fixes", "level": "info", "logger": "bootstrap"}
authentik-worker  | {"event": "Loaded config", "level": "debug", "logger": "authentik.lib.config", "timestamp": 1777321174.0306287, "file": "/authentik/lib/default.yml"}
authentik-worker  | {"event": "Loaded environment variables", "level": "debug", "logger": "authentik.lib.config", "timestamp": 1777321174.032005, "count": 11}
authentik-worker  | {"event": "Starting authentik bootstrap", "level": "info", "logger": "authentik.lib.config", "timestamp": 1777321175.5404475}
authentik-worker  | {"event": "PostgreSQL connection successful", "level": "info", "logger": "authentik.lib.config", "timestamp": 1777321175.6104753}
authentik-worker  | {"event": "Redis Connection successful", "level": "info", "logger": "authentik.lib.config", "timestamp": 1777321175.6343567}
authentik-worker  | {"event": "Finished authentik bootstrap", "level": "info", "logger": "authentik.lib.config", "timestamp": 1777321175.6355472}
authentik-worker  | 2026-04-27 20:19:35 [info     ] waiting to acquire database lock
authentik-worker  | 2026-04-27 20:19:35 [info     ] Migration needs to be applied  migration=tenant_files.py
authentik-worker  | 2026-04-27 20:19:35 [info     ] releasing database lock
authentik-worker  | Traceback (most recent call last):
authentik-worker  |   File "<frozen runpy>", line 198, in _run_module_as_main
authentik-worker  |   File "<frozen runpy>", line 88, in _run_code
authentik-worker  |   File "/manage.py", line 43, in <module>
authentik-worker  |     run_migrations()
authentik-worker  |   File "/lifecycle/migrate.py", line 103, in run_migrations
authentik-worker  |     migration.run()
authentik-worker  |   File "/lifecycle/system_migrations/tenant_files.py", line 18, in run
authentik-worker  |     TENANT_MEDIA_ROOT.mkdir(parents=True)
authentik-worker  |   File "/usr/local/lib/python3.12/pathlib.py", line 1311, in mkdir
authentik-worker  |     os.mkdir(self, mode)
authentik-worker  | PermissionError: [Errno 13] Permission denied: '/media/public'
authentik-worker exited with code 1
authentik-server  | {"event": "Loaded config", "level": "debug", "logger": "authentik.lib.config", "timestamp": 1777321177.4008067, "file": "/authentik/lib/default.yml"}
authentik-server  | {"event": "Loaded environment variables", "level": "debug", "logger": "authentik.lib.config", "timestamp": 1777321177.402055, "count": 11}
authentik-s
