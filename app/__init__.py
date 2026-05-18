from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()

login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'


def create_app(config_class=None):
    app = Flask(__name__)

    if config_class:
        app.config.from_object(config_class)
    else:
        from app.config import Config
        app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    # Import all models so SQLAlchemy is aware of every table
    from app.models import user, ticket, department    # noqa
    from app.models import sla, escalation, notification, approval  # noqa
    from app.models import forms  # noqa  (Phase 3: dynamic form models)
    from app.models import kb, api_token  # noqa  (Phase 4)
    from app.models import assignment_rule  # noqa  (dynamic assignment)
    from app.models import priority_rule    # noqa  (dynamic priority)

    # ---- Blueprints ----
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.tickets import bp as tickets_bp
    app.register_blueprint(tickets_bp, url_prefix='/tickets')

    from app.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')

    from app.notifications import bp as notifications_bp
    app.register_blueprint(notifications_bp, url_prefix='/notifications')

    from app.approvals import bp as approvals_bp
    app.register_blueprint(approvals_bp, url_prefix='/approvals')

    from app.sla import bp as sla_bp
    app.register_blueprint(sla_bp, url_prefix='/sla')

    from app.reports import bp as reports_bp
    app.register_blueprint(reports_bp, url_prefix='/reports')

    from app.kb import bp as kb_bp          # Phase 4: Knowledge Base
    app.register_blueprint(kb_bp, url_prefix='/kb')

    from app.api import bp as api_bp        # Phase 4: REST API
    app.register_blueprint(api_bp, url_prefix='/api/v1')

    # ---- Background scheduler ----
    if not app.config.get('TESTING', False):
        try:
            from app.scheduler import start_scheduler
            start_scheduler(app)
        except Exception as exc:
            app.logger.warning('Scheduler failed to start: %s', exc)

    # ---- Root redirect ----
    @app.route('/')
    def index():
        from flask import redirect, url_for
        from flask_login import current_user
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))

    return app
