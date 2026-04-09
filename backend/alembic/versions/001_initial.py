"""Initial migration — create predictions and training_runs tables.

Revision ID: 001
Create Date: 2026-04-02
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("prediction_id", sa.String(36), nullable=False, unique=True),
        sa.Column("batch_id", sa.String(36), nullable=True),
        sa.Column("home_team", sa.String(200), nullable=False),
        sa.Column("away_team", sa.String(200), nullable=False),
        sa.Column("competition", sa.String(50), nullable=True),
        sa.Column("match_date", sa.String(30), nullable=True),
        sa.Column("payload_json", sa.Text, nullable=True),
        sa.Column("result_json", sa.Text, nullable=False),
        sa.Column("model_confidence", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_predictions_prediction_id", "predictions", ["prediction_id"])
    op.create_index("ix_predictions_batch_id", "predictions", ["batch_id"])

    op.create_table(
        "training_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("samples", sa.Integer, nullable=False),
        sa.Column("metrics_json", sa.Text, nullable=True),
        sa.Column("model_path", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("training_runs")
    op.drop_index("ix_predictions_batch_id", table_name="predictions")
    op.drop_index("ix_predictions_prediction_id", table_name="predictions")
    op.drop_table("predictions")
