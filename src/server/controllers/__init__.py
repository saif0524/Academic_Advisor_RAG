"""Resource controllers — orchestrate services, map errors, build responses.

Controllers are the only layer between routers and services. They stay free of
business logic; constraint rejections (`core.errors`, FC29–FC32) surface
through the global handlers registered in `errors.py` once `core/` lands —
never swallowed into generic 500s.
"""