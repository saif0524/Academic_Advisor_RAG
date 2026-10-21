"""Resource routers — paths, methods, and HTTP shapes only (zero business logic).

Each router delegates to its controller; dependencies arrive via
`dependencies.py` providers. Every endpoint declares `response_model` and
documents its FC ids.
"""