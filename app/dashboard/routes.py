from flask import render_template
from flask_login import login_required, current_user
from app.dashboard import bp
from app.models.ticket import Ticket
from app.models.user import User
from app.models.department import Department
from app import db


@bp.route('/')
@login_required
def index():
    if current_user.has_role('Admin'):
        return _admin_dashboard()
    elif current_user.has_role('Agent'):
        return _agent_dashboard()
    else:
        return _user_dashboard()


def _admin_dashboard():
    total = Ticket.query.count()
    open_count = Ticket.query.filter_by(status='Open').count()
    in_progress = Ticket.query.filter_by(status='InProgress').count()
    on_hold = Ticket.query.filter_by(status='Hold').count()
    resolved = Ticket.query.filter_by(status='Resolved').count()
    closed = Ticket.query.filter_by(status='Closed').count()
    rejected = Ticket.query.filter_by(status='Rejected').count()

    recent_tickets = Ticket.query.order_by(Ticket.created_at.desc()).limit(10).all()
    total_users = User.query.count()
    total_departments = Department.query.filter_by(is_active=True).count()

    dept_stats = db.session.query(
        Department.name,
        db.func.count(Ticket.id)
    ).join(Ticket, Ticket.department_id == Department.id).group_by(Department.name).all()

    return render_template('dashboard/admin.html',
        total=total, open_count=open_count, in_progress=in_progress,
        on_hold=on_hold, resolved=resolved, closed=closed, rejected=rejected,
        recent_tickets=recent_tickets, total_users=total_users,
        total_departments=total_departments, dept_stats=dept_stats,
    )


def _agent_dashboard():
    my_tickets = Ticket.query.filter_by(assigned_to=current_user.id)
    assigned_total = my_tickets.count()
    assigned_open = my_tickets.filter_by(status='InProgress').count()
    assigned_hold = my_tickets.filter_by(status='Hold').count()
    assigned_resolved = my_tickets.filter(Ticket.status.in_(['Resolved', 'Closed'])).count()

    pending_tickets = Ticket.query.filter_by(
        assigned_to=current_user.id
    ).filter(
        Ticket.status.in_(['Open', 'InProgress', 'Hold', 'Reopened'])
    ).order_by(Ticket.created_at.desc()).limit(10).all()

    unassigned = Ticket.query.filter_by(assigned_to=None, status='Open')
    if current_user.department_id:
        unassigned = unassigned.filter_by(department_id=current_user.department_id)
    unassigned_tickets = unassigned.order_by(Ticket.created_at.desc()).limit(10).all()

    return render_template('dashboard/agent.html',
        assigned_total=assigned_total, assigned_open=assigned_open,
        assigned_hold=assigned_hold, assigned_resolved=assigned_resolved,
        pending_tickets=pending_tickets, unassigned_tickets=unassigned_tickets,
    )


def _user_dashboard():
    my_tickets = Ticket.query.filter(
        db.or_(Ticket.created_by == current_user.id, Ticket.created_on_behalf_of == current_user.id)
    )
    total = my_tickets.count()
    active = my_tickets.filter(Ticket.status.in_(['Open', 'InProgress', 'Hold', 'Reopened'])).count()
    resolved = my_tickets.filter(Ticket.status.in_(['Resolved', 'Closed'])).count()

    recent_tickets = my_tickets.order_by(Ticket.created_at.desc()).limit(10).all()

    return render_template('dashboard/user.html',
        total=total, active=active, resolved=resolved,
        recent_tickets=recent_tickets,
    )
