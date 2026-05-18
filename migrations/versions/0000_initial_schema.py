"""Initial schema — create all base tables

Revision ID: 0000initialschema
Revises:
Create Date: 2026-05-18 00:00:00.000000

NOTE: This is the root migration.  It creates every table that the app
needs before the incremental migrations (assignment rules, priority rules,
approver_id) run on top of it.
"""
from alembic import op
import sqlalchemy as sa

revision = '0000initialschema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ── permissions ──────────────────────────────────────────────────────────
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # ── roles ─────────────────────────────────────────────────────────────────
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # ── role_permissions (M2M) ────────────────────────────────────────────────
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id']),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id']),
        sa.PrimaryKeyConstraint('role_id', 'permission_id'),
    )

    # ── departments ───────────────────────────────────────────────────────────
    op.create_table(
        'departments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('password_hash', sa.String(length=256), nullable=False),
        sa.Column('first_name', sa.String(length=80), nullable=False),
        sa.Column('last_name', sa.String(length=80), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id']),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    # ── problems ──────────────────────────────────────────────────────────────
    op.create_table(
        'problems',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'department_id', name='uq_problem_dept'),
    )

    # ── sub_problems ──────────────────────────────────────────────────────────
    op.create_table(
        'sub_problems',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('problem_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['problem_id'], ['problems.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'problem_id', name='uq_subproblem_problem'),
    )

    # ── categories ────────────────────────────────────────────────────────────
    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('sub_problem_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['sub_problem_id'], ['sub_problems.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'sub_problem_id', name='uq_category_subproblem'),
    )

    # ── sub_categories ────────────────────────────────────────────────────────
    op.create_table(
        'sub_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'category_id', name='uq_subcategory_category'),
    )

    # ── ticket_sequences ──────────────────────────────────────────────────────
    op.create_table(
        'ticket_sequences',
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('last_number', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('year'),
    )

    # ── tickets ───────────────────────────────────────────────────────────────
    op.create_table(
        'tickets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=False),
        sa.Column('problem_id', sa.Integer(), nullable=True),
        sa.Column('sub_problem_id', sa.Integer(), nullable=True),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('sub_category_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('created_on_behalf_of', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id']),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['created_on_behalf_of'], ['users.id']),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id']),
        sa.ForeignKeyConstraint(['problem_id'], ['problems.id']),
        sa.ForeignKeyConstraint(['sub_category_id'], ['sub_categories.id']),
        sa.ForeignKeyConstraint(['sub_problem_id'], ['sub_problems.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tickets_ticket_id', 'tickets', ['ticket_id'], unique=True)
    op.create_index('ix_tickets_status', 'tickets', ['status'], unique=False)

    # ── ticket_messages ───────────────────────────────────────────────────────
    op.create_table(
        'ticket_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_pk', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_internal', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['ticket_pk'], ['tickets.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── ticket_attachments ────────────────────────────────────────────────────
    op.create_table(
        'ticket_attachments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_pk', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['message_id'], ['ticket_messages.id']),
        sa.ForeignKeyConstraint(['ticket_pk'], ['tickets.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── ticket_activity_logs ──────────────────────────────────────────────────
    op.create_table(
        'ticket_activity_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_pk', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['ticket_pk'], ['tickets.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── ticket_status_history ─────────────────────────────────────────────────
    op.create_table(
        'ticket_status_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_pk', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('old_status', sa.String(length=20), nullable=True),
        sa.Column('new_status', sa.String(length=20), nullable=False),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['ticket_pk'], ['tickets.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── sla_policies ──────────────────────────────────────────────────────────
    op.create_table(
        'sla_policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('priority', sa.String(length=20), nullable=True),
        sa.Column('first_response_hours', sa.Float(), nullable=False),
        sa.Column('resolution_hours', sa.Float(), nullable=False),
        sa.Column('use_business_hours', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── business_hours ────────────────────────────────────────────────────────
    op.create_table(
        'business_hours',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('is_working_day', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('day_of_week'),
    )

    # ── holidays ──────────────────────────────────────────────────────────────
    op.create_table(
        'holidays',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date'),
    )

    # ── ticket_sla ────────────────────────────────────────────────────────────
    op.create_table(
        'ticket_sla',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_pk', sa.Integer(), nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=True),
        sa.Column('first_response_due', sa.DateTime(), nullable=True),
        sa.Column('resolution_due', sa.DateTime(), nullable=True),
        sa.Column('first_response_met', sa.Boolean(), nullable=False),
        sa.Column('first_response_at', sa.DateTime(), nullable=True),
        sa.Column('first_response_breached', sa.Boolean(), nullable=False),
        sa.Column('resolution_met', sa.Boolean(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolution_breached', sa.Boolean(), nullable=False),
        sa.Column('is_paused', sa.Boolean(), nullable=False),
        sa.Column('pause_started_at', sa.DateTime(), nullable=True),
        sa.Column('total_paused_seconds', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['policy_id'], ['sla_policies.id']),
        sa.ForeignKeyConstraint(['ticket_pk'], ['tickets.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticket_pk'),
    )

    # ── sla_pauses ────────────────────────────────────────────────────────────
    op.create_table(
        'sla_pauses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_sla_id', sa.Integer(), nullable=False),
        sa.Column('pause_reason', sa.String(length=100), nullable=True),
        sa.Column('paused_at', sa.DateTime(), nullable=False),
        sa.Column('resumed_at', sa.DateTime(), nullable=True),
        sa.Column('paused_seconds', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['ticket_sla_id'], ['ticket_sla.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── escalation_rules ──────────────────────────────────────────────────────
    op.create_table(
        'escalation_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('priority', sa.String(length=20), nullable=True),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('sla_type', sa.String(length=20), nullable=False),
        sa.Column('breach_threshold_percent', sa.Integer(), nullable=False),
        sa.Column('notify_user_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id']),
        sa.ForeignKeyConstraint(['notify_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── ticket_escalations ────────────────────────────────────────────────────
    op.create_table(
        'ticket_escalations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_pk', sa.Integer(), nullable=False),
        sa.Column('rule_id', sa.Integer(), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('triggered_at', sa.DateTime(), nullable=True),
        sa.Column('notified_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['rule_id'], ['escalation_rules.id']),
        sa.ForeignKeyConstraint(['ticket_pk'], ['tickets.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticket_pk', 'rule_id', name='uq_ticket_escalation_rule'),
    )

    # ── notifications ─────────────────────────────────────────────────────────
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('ticket_pk', sa.Integer(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['ticket_pk'], ['tickets.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'], unique=False)
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'], unique=False)
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'], unique=False)

    # ── approval_requests ─────────────────────────────────────────────────────
    # NOTE: approver_id column is added in migration 217a2e0fea79
    op.create_table(
        'approval_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_pk', sa.Integer(), nullable=False),
        sa.Column('requested_by', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('requested_action', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id']),
        sa.ForeignKeyConstraint(['ticket_pk'], ['tickets.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_approval_requests_status', 'approval_requests', ['status'], unique=False)

    # ── approval_actions ──────────────────────────────────────────────────────
    op.create_table(
        'approval_actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('approval_request_id', sa.Integer(), nullable=False),
        sa.Column('actioned_by', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['actioned_by'], ['users.id']),
        sa.ForeignKeyConstraint(['approval_request_id'], ['approval_requests.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── approval_history ──────────────────────────────────────────────────────
    op.create_table(
        'approval_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('approval_request_id', sa.Integer(), nullable=False),
        sa.Column('ticket_pk', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['approval_request_id'], ['approval_requests.id']),
        sa.ForeignKeyConstraint(['ticket_pk'], ['tickets.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── kb_categories ─────────────────────────────────────────────────────────
    op.create_table(
        'kb_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug'),
    )

    # ── kb_articles ───────────────────────────────────────────────────────────
    op.create_table(
        'kb_articles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('views', sa.Integer(), nullable=False),
        sa.Column('is_published', sa.Boolean(), nullable=False),
        sa.Column('tags', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['author_id'], ['users.id']),
        sa.ForeignKeyConstraint(['category_id'], ['kb_categories.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )

    # ── form_templates ────────────────────────────────────────────────────────
    op.create_table(
        'form_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('problem_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id']),
        sa.ForeignKeyConstraint(['problem_id'], ['problems.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── form_fields ───────────────────────────────────────────────────────────
    op.create_table(
        'form_fields',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(length=100), nullable=False),
        sa.Column('field_name', sa.String(length=50), nullable=False),
        sa.Column('field_type', sa.String(length=20), nullable=False),
        sa.Column('options', sa.Text(), nullable=True),
        sa.Column('placeholder', sa.String(length=200), nullable=True),
        sa.Column('is_required', sa.Boolean(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['form_templates.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── ticket_field_values ───────────────────────────────────────────────────
    op.create_table(
        'ticket_field_values',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_pk', sa.Integer(), nullable=False),
        sa.Column('field_id', sa.Integer(), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['field_id'], ['form_fields.id']),
        sa.ForeignKeyConstraint(['ticket_pk'], ['tickets.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticket_pk', 'field_id', name='uq_ticket_field'),
    )

    # ── api_tokens ────────────────────────────────────────────────────────────
    op.create_table(
        'api_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('token_hash', sa.String(length=256), nullable=False),
        sa.Column('prefix', sa.String(length=8), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )


def downgrade():
    op.drop_table('api_tokens')
    op.drop_table('ticket_field_values')
    op.drop_table('form_fields')
    op.drop_table('form_templates')
    op.drop_table('kb_articles')
    op.drop_table('kb_categories')
    op.drop_table('approval_history')
    op.drop_table('approval_actions')
    op.drop_table('approval_requests')
    op.drop_index('ix_notifications_created_at', table_name='notifications')
    op.drop_index('ix_notifications_is_read', table_name='notifications')
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_table('notifications')
    op.drop_table('ticket_escalations')
    op.drop_table('escalation_rules')
    op.drop_table('sla_pauses')
    op.drop_table('ticket_sla')
    op.drop_table('holidays')
    op.drop_table('business_hours')
    op.drop_table('sla_policies')
    op.drop_table('ticket_status_history')
    op.drop_table('ticket_activity_logs')
    op.drop_table('ticket_attachments')
    op.drop_table('ticket_messages')
    op.drop_index('ix_tickets_status', table_name='tickets')
    op.drop_index('ix_tickets_ticket_id', table_name='tickets')
    op.drop_table('tickets')
    op.drop_table('ticket_sequences')
    op.drop_table('sub_categories')
    op.drop_table('categories')
    op.drop_table('sub_problems')
    op.drop_table('problems')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
    op.drop_table('departments')
    op.drop_table('role_permissions')
    op.drop_table('roles')
    op.drop_table('permissions')
