"""SQLAlchemy dialect for StarRocks."""

from sqlalchemy.dialects import registry

registry.register(
    "starrocks",
    "gyra_ext.datasource.rdbms.dialect.starrocks.sqlalchemy.dialect",
    "StarRocksDialect",
)
