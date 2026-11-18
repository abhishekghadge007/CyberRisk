
from sqlalchemy import text
from database import engine

statements = [
    """
    ALTER TABLE optimization_recommendations
    ADD COLUMN IF NOT EXISTS asset_id BIGINT
    REFERENCES assets(asset_id) ON DELETE SET NULL
    """,
    """
    ALTER TABLE optimization_recommendations
    ADD COLUMN IF NOT EXISTS priority_weight NUMERIC(5, 2)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_optimization_recommendations_asset
    ON optimization_recommendations(asset_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_optimization_recommendations_run
    ON optimization_recommendations(run_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS optimization_run_assets (
        id BIGSERIAL PRIMARY KEY,
        run_id BIGINT NOT NULL
            REFERENCES optimization_runs(run_id) ON DELETE CASCADE,
        asset_id BIGINT NOT NULL
            REFERENCES assets(asset_id) ON DELETE CASCADE,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_optimization_run_asset
            UNIQUE (run_id, asset_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_optimization_run_assets_run
    ON optimization_run_assets(run_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_optimization_run_assets_asset
    ON optimization_run_assets(asset_id)
    """
]

try:
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

    print("Multi-asset optimization database changes completed successfully.")

except Exception as error:
    print("Database update failed:")
    print(error)
    raise
