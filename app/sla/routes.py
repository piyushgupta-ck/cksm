from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.sla import bp
from app.auth.decorators import admin_required
from app.models.sla import SLAPolicy, BusinessHoursConfig, Holiday
from app.models.escalation import EscalationRule
from app.models.department import Department
from app.models.user import User, Role
from app import db

_PRIORITIES = ['Low', 'Medium', 'High', 'Critical']


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@bp.route('/')
@login_required
@admin_required
def index():
    policies = SLAPolicy.query.order_by(SLAPolicy.name).all()
    biz_hours = BusinessHoursConfig.query.order_by(BusinessHoursConfig.day_of_week).all()
    holidays = Holiday.query.filter_by(is_active=True).order_by(Holiday.date).all()
    escalation_rules = EscalationRule.query.order_by(EscalationRule.level, EscalationRule.name).all()
    return render_template(
        'sla/index.html',
        policies=policies, biz_hours=biz_hours,
        holidays=holidays, escalation_rules=escalation_rules,
    )


# ---------------------------------------------------------------------------
# SLA Policies
# ---------------------------------------------------------------------------

@bp.route('/policies/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_policy():
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        dept_id = request.form.get('department_id', type=int) or None
        priority = request.form.get('priority', '').strip() or None
        fr_hours = request.form.get('first_response_hours', type=float)
        res_hours = request.form.get('resolution_hours', type=float)
        use_biz = request.form.get('use_business_hours') == 'on'

        if not name or not fr_hours or not res_hours:
            flash('Name, first-response hours, and resolution hours are required.', 'error')
            return render_template('sla/create_policy.html',
                                   departments=departments, priorities=_PRIORITIES)

        db.session.add(SLAPolicy(
            name=name, department_id=dept_id, priority=priority,
            first_response_hours=fr_hours, resolution_hours=res_hours,
            use_business_hours=use_biz,
        ))
        db.session.commit()
        flash(f'SLA Policy "{name}" created.', 'success')
        return redirect(url_for('sla.index'))

    return render_template('sla/create_policy.html',
                           departments=departments, priorities=_PRIORITIES)


@bp.route('/policies/<int:policy_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_policy(policy_id):
    policy = db.session.get(SLAPolicy, policy_id)
    if not policy:
        flash('Policy not found.', 'error')
        return redirect(url_for('sla.index'))
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()

    if request.method == 'POST':
        policy.name = request.form.get('name', '').strip()
        dept_id = request.form.get('department_id', type=int) or None
        policy.department_id = dept_id
        priority = request.form.get('priority', '').strip()
        policy.priority = priority or None
        policy.first_response_hours = request.form.get('first_response_hours', type=float)
        policy.resolution_hours = request.form.get('resolution_hours', type=float)
        policy.use_business_hours = request.form.get('use_business_hours') == 'on'
        policy.is_active = request.form.get('is_active') == 'on'
        db.session.commit()
        flash('SLA Policy updated.', 'success')
        return redirect(url_for('sla.index'))

    return render_template('sla/edit_policy.html',
                           policy=policy, departments=departments, priorities=_PRIORITIES)


@bp.route('/policies/<int:policy_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_policy(policy_id):
    policy = db.session.get(SLAPolicy, policy_id)
    if policy:
        policy.is_active = not policy.is_active
        db.session.commit()
        flash(f'Policy {"activated" if policy.is_active else "deactivated"}.', 'success')
    return redirect(url_for('sla.index'))


# ---------------------------------------------------------------------------
# Business Hours
# ---------------------------------------------------------------------------

@bp.route('/business-hours', methods=['POST'])
@login_required
@admin_required
def save_business_hours():
    from datetime import time
    for day in range(7):
        is_working = request.form.get(f'day_{day}_working') == 'on'
        start_str = request.form.get(f'day_{day}_start', '09:00')
        end_str = request.form.get(f'day_{day}_end', '18:00')
        try:
            sh, sm = map(int, start_str.split(':'))
            eh, em = map(int, end_str.split(':'))
            start_t = time(sh, sm)
            end_t = time(eh, em)
        except Exception:
            start_t, end_t = time(9, 0), time(18, 0)

        cfg = BusinessHoursConfig.query.filter_by(day_of_week=day).first()
        if cfg:
            cfg.is_working_day = is_working
            cfg.start_time = start_t
            cfg.end_time = end_t
        else:
            db.session.add(BusinessHoursConfig(
                day_of_week=day, start_time=start_t,
                end_time=end_t, is_working_day=is_working,
            ))
    db.session.commit()
    flash('Business hours updated.', 'success')
    return redirect(url_for('sla.index'))


# ---------------------------------------------------------------------------
# Holidays
# ---------------------------------------------------------------------------

@bp.route('/holidays/add', methods=['POST'])
@login_required
@admin_required
def add_holiday():
    name = request.form.get('name', '').strip()
    date_str = request.form.get('date', '').strip()
    if not name or not date_str:
        flash('Name and date are required.', 'error')
        return redirect(url_for('sla.index'))
    try:
        from datetime import date
        holiday_date = date.fromisoformat(date_str)
    except ValueError:
        flash('Invalid date format (use YYYY-MM-DD).', 'error')
        return redirect(url_for('sla.index'))

    existing = Holiday.query.filter_by(date=holiday_date).first()
    if existing:
        existing.name = name
        existing.is_active = True
    else:
        db.session.add(Holiday(name=name, date=holiday_date))
    db.session.commit()
    flash(f'Holiday "{name}" added.', 'success')
    return redirect(url_for('sla.index'))


@bp.route('/holidays/<int:holiday_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_holiday(holiday_id):
    holiday = db.session.get(Holiday, holiday_id)
    if holiday:
        holiday.is_active = False
        db.session.commit()
        flash('Holiday removed.', 'success')
    return redirect(url_for('sla.index'))


# ---------------------------------------------------------------------------
# Escalation Rules
# ---------------------------------------------------------------------------

@bp.route('/escalation-rules/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_escalation_rule():
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    agents = (User.query.filter_by(is_active=True)
              .join(Role).filter(Role.name.in_(['Agent', 'Admin']))
              .order_by(User.first_name).all())

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        dept_id = request.form.get('department_id', type=int) or None
        priority = request.form.get('priority', '').strip() or None
        level = request.form.get('level', type=int, default=1)
        sla_type = request.form.get('sla_type', 'resolution')
        threshold = request.form.get('breach_threshold_percent', type=int, default=80)
        notify_uid = request.form.get('notify_user_id', type=int) or None

        if not name:
            flash('Rule name is required.', 'error')
            return render_template('sla/create_escalation_rule.html',
                                   departments=departments, agents=agents, priorities=_PRIORITIES)

        db.session.add(EscalationRule(
            name=name, department_id=dept_id, priority=priority,
            level=level, sla_type=sla_type,
            breach_threshold_percent=threshold,
            notify_user_id=notify_uid,
        ))
        db.session.commit()
        flash(f'Escalation rule "{name}" created.', 'success')
        return redirect(url_for('sla.index'))

    return render_template('sla/create_escalation_rule.html',
                           departments=departments, agents=agents, priorities=_PRIORITIES)


@bp.route('/escalation-rules/<int:rule_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_escalation_rule(rule_id):
    rule = db.session.get(EscalationRule, rule_id)
    if rule:
        rule.is_active = not rule.is_active
        db.session.commit()
        flash(f'Rule {"activated" if rule.is_active else "deactivated"}.', 'success')
    return redirect(url_for('sla.index'))


@bp.route('/escalation-rules/<int:rule_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_escalation_rule(rule_id):
    rule = db.session.get(EscalationRule, rule_id)
    if rule:
        db.session.delete(rule)
        db.session.commit()
        flash('Escalation rule deleted.', 'success')
    return redirect(url_for('sla.index'))


# ---------------------------------------------------------------------------
# Manual SLA breach check
# ---------------------------------------------------------------------------

@bp.route('/run-check', methods=['POST'])
@login_required
@admin_required
def run_check():
    from app.sla.engine import check_sla_breaches
    from flask import current_app
    check_sla_breaches(current_app._get_current_object())
    flash('SLA breach check completed.', 'success')
    return redirect(url_for('sla.index'))
