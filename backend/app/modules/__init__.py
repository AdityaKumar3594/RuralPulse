"""Domain modules (identity, profile, interview, catalog, ...).

Each module owns its models, schemas, service and router. Modules talk to each
other through service functions, never by importing another module's models
into their own tables' business logic.
"""
