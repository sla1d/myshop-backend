"""add_rbac_security_saas — full schema migration

Revision ID: a1b2c3d4e5f6
Revises: c9ffaabc5a3e
Create Date: 2026-06-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "a1b2c3d4e5f6"
down_revision = "c9ffaabc5a3e"
branch_labels = None
depends_on = None

# All tables this migration creates
_NEW_TABLES = [
    "tenants", "licenses", "flash_sales", "ab_test_assignments", "ab_tests",
    "wishlist_prices", "ad_banners", "audit_logs",
    "roles", "permissions", "role_permissions", "user_roles",
    "refresh_tokens", "login_attempts", "security_events",
    "subscriptions", "invoices", "payments",
    "custom_domains", "tenant_features", "plugins",
]


def _table_exists(bind, name: str) -> bool:
    return inspect(bind).has_table(name)


def upgrade() -> None:
    conn = op.get_bind()

    # ─── Add tenant_id to existing tables ──────────
    for table in ["users", "products", "cart", "orders", "reviews", "wishlist", "promo_codes"]:
        if _table_exists(conn, table):
            try:
                op.add_column(table, sa.Column("tenant_id", sa.Integer(), nullable=True))
            except Exception:
                pass  # Already exists

    # ─── Add indexes for tenant_id ─────────────────
    for table in ["users", "products", "cart", "orders", "reviews", "wishlist", "promo_codes"]:
        try:
            op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
        except Exception:
            pass  # Already exists

    # ─── Tenants ───────────────────────────────────
    if not _table_exists(conn, "tenants"):
        op.create_table(
            "tenants",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("slug", sa.String(100), nullable=True),
            sa.Column("domain", sa.String(255), nullable=True),
            sa.Column("subscription_status", sa.String(20), server_default="active"),
            sa.Column("subscription_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("settings", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("brand_name", sa.String(255), nullable=True),
            sa.Column("primary_color", sa.String(7), nullable=True),
            sa.Column("secondary_color", sa.String(7), nullable=True),
            sa.Column("footer_text", sa.String(500), nullable=True),
            sa.Column("favicon_url", sa.String(500), nullable=True),
            sa.Column("custom_css", sa.Text(), nullable=True),
            sa.Column("hide_myshop_branding", sa.Boolean(), server_default="0"),
            sa.Column("custom_email_domain", sa.String(255), nullable=True),
            sa.Column("meta_title", sa.String(255), nullable=True),
            sa.Column("meta_description", sa.String(500), nullable=True),
            sa.Column("og_image_url", sa.String(500), nullable=True),
        )
    else:
        # Add white-label columns if table exists but columns are missing
        for col_name, col_type in [
            ("brand_name", sa.String(255)),
            ("primary_color", sa.String(7)),
            ("secondary_color", sa.String(7)),
            ("footer_text", sa.String(500)),
            ("favicon_url", sa.String(500)),
            ("custom_css", sa.Text()),
            ("hide_myshop_branding", sa.Boolean()),
            ("custom_email_domain", sa.String(255)),
            ("meta_title", sa.String(255)),
            ("meta_description", sa.String(500)),
            ("og_image_url", sa.String(500)),
        ]:
            try:
                op.add_column("tenants", sa.Column(col_name, col_type, nullable=True))
            except Exception:
                pass  # Column already exists

    if not _table_exists(conn, "licenses"):
        op.create_table(
            "licenses",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("key", sa.String(200), unique=True, nullable=False),
            sa.Column("plan", sa.String(50), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("activated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        )

    # ─── Flash Sales ───────────────────────────────
    if not _table_exists(conn, "flash_sales"):
        op.create_table(
            "flash_sales",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("discount_percent", sa.Integer(), nullable=False),
            sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    # ─── A/B Tests ─────────────────────────────────
    if not _table_exists(conn, "ab_tests"):
        op.create_table(
            "ab_tests",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("variant_a", sa.Text(), nullable=False),
            sa.Column("variant_b", sa.Text(), nullable=False),
            sa.Column("traffic_percent", sa.Integer(), nullable=False, server_default="50"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if not _table_exists(conn, "ab_test_assignments"):
        op.create_table(
            "ab_test_assignments",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("test_id", sa.Integer(), sa.ForeignKey("ab_tests.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("variant", sa.String(1), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    # ─── Ad Banners & Wishlist Prices ──────────────
    if not _table_exists(conn, "ad_banners"):
        op.create_table(
            "ad_banners",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("image_url", sa.String(500), nullable=False),
            sa.Column("link", sa.String(500), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("position", sa.String(50), nullable=False, server_default="home"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if not _table_exists(conn, "wishlist_prices"):
        op.create_table(
            "wishlist_prices",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("target_price", sa.Integer(), nullable=False),
            sa.Column("notified", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    # ─── Audit Logs ────────────────────────────────
    if not _table_exists(conn, "audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(100), nullable=False),
            sa.Column("resource_type", sa.String(50), nullable=True),
            sa.Column("resource_id", sa.Integer(), nullable=True),
            sa.Column("details", sa.Text(), nullable=True),
            sa.Column("user_agent", sa.String(500), nullable=True),
            sa.Column("ip_address", sa.String(50), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # ─── RBAC ──────────────────────────────────────
    if not _table_exists(conn, "roles"):
        op.create_table(
            "roles",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(50), unique=True, nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_roles_name", "roles", ["name"])

    if not _table_exists(conn, "permissions"):
        op.create_table(
            "permissions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(100), unique=True, nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("category", sa.String(50), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_permissions_name", "permissions", ["name"])

    if not _table_exists(conn, "role_permissions"):
        op.create_table(
            "role_permissions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False),
            sa.UniqueConstraint("role_id", "permission_id"),
        )
        op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])
        op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])

    if not _table_exists(conn, "user_roles"):
        op.create_table(
            "user_roles",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("assigned_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.UniqueConstraint("user_id", "tenant_id", "role_id"),
        )
        op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
        op.create_index("ix_user_roles_tenant_id", "user_roles", ["tenant_id"])
        op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])

    # ─── Security ──────────────────────────────────
    if not _table_exists(conn, "refresh_tokens"):
        op.create_table(
            "refresh_tokens",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("token_hash", sa.String(64), unique=True, nullable=False),
            sa.Column("ip_address", sa.String(50), nullable=True),
            sa.Column("device_info", sa.String(500), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
        op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])

    if not _table_exists(conn, "login_attempts"):
        op.create_table(
            "login_attempts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("ip", sa.String(50), nullable=False),
            sa.Column("user_agent", sa.String(500), nullable=True),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_login_attempts_email", "login_attempts", ["email"])

    if not _table_exists(conn, "security_events"):
        op.create_table(
            "security_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("event_type", sa.String(50), nullable=False),
            sa.Column("details", sa.Text(), nullable=True),
            sa.Column("ip_address", sa.String(50), nullable=True),
            sa.Column("user_agent", sa.String(500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    # ─── Billing ───────────────────────────────────
    if not _table_exists(conn, "subscriptions"):
        op.create_table(
            "subscriptions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("plan", sa.String(50), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("payment_amount", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_subscriptions_tenant_id", "subscriptions", ["tenant_id"])

    if not _table_exists(conn, "invoices"):
        op.create_table(
            "invoices",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("subscription_id", sa.Integer(), sa.ForeignKey("subscriptions.id"), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_invoices_tenant_id", "invoices", ["tenant_id"])

    if not _table_exists(conn, "payments"):
        op.create_table(
            "payments",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
            sa.Column("provider", sa.String(50), nullable=False),
            sa.Column("external_id", sa.String(200), nullable=True),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("currency", sa.String(3), nullable=False, server_default="RUB"),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_payments_tenant_id", "payments", ["tenant_id"])

    # ─── SaaS ──────────────────────────────────────
    if not _table_exists(conn, "custom_domains"):
        op.create_table(
            "custom_domains",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("domain", sa.String(255), unique=True, nullable=False),
            sa.Column("verified", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("ssl_enabled", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("dns_configured", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_custom_domains_tenant_id", "custom_domains", ["tenant_id"])

    if not _table_exists(conn, "tenant_features"):
        op.create_table(
            "tenant_features",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("feature_key", sa.String(50), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("config", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("tenant_id", "feature_key"),
        )
        op.create_index("ix_tenant_features_tenant_id", "tenant_features", ["tenant_id"])

    if not _table_exists(conn, "plugins"):
        op.create_table(
            "plugins",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("config", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_plugins_tenant_id", "plugins", ["tenant_id"])


def downgrade() -> None:
    for tbl in reversed(_NEW_TABLES):
        if _table_exists(op.get_bind(), tbl):
            op.drop_table(tbl)
