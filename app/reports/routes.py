"""
Reports & Analytics blueprint — admin-only.
All chart data is served as JSON; the template renders via Chart.js.
"""
import csv
import io
from datetime import datetime, timezone, timedelta

from flask import render_template, jsonify, request, Response
from flask_login import login_required
from sqlalchemy import func

from app.reports import bp
from app.auth.decorators import admin_required
from app.models.ticket import Ticket
from app.models.user import User, Role
from app.models.department import Department
from app.models.sla import TicketSLA
from app.models.escalation import TicketEscalation
from app import db


# ---------------------------------------------------------------------------
# Dashboard page
# ---------------------------------------------------------------------------

@bp.route('/')
@login_required
@admin_required
def index():
    return render_template('reports/index.html')


# ---------------------------------------------------------------------------
# JSON API — overview stats
# ---------------------------------------------------------------------------

@bp.route('/api/overview')
@login_required
@admin_required
def api_overview():
    total = Ticket.query.count()
    by_status = {s: Ticket.query.filter_by(status=s).count() for s in Ticket.STATUSES}

    total_sla = TicketSLA.query.count()
    fr_met = TicketSLA.query.filter_by(first_response_met=True).count()
    fr_breached = TicketSLA.query.filter_by(first_response_breached=True).count()
    res_breached = TicketSLA.query.filter_by(resolution_breached=True).count()

    return jsonify({
        'total': total,
        'by_status': by_status,
        'sla_total': total_sla,
        'sla_fr_met': fr_met,
        'sla_fr_breached': fr_breached,
        'sla_res_breached': res_breached,
    })


# ---------------------------------------------------------------------------
# JSON API — tickets created per day
# ---------------------------------------------------------------------------

@bp.route('/api/tickets-by-day')
@login_required
@admin_required
def api_tickets_by_day():
    days = request.args.get('days', 30, type=int)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (
        db.session.query(
            func.date(Ticket.created_at).label('day'),
            func.count(Ticket.id).label('count'),
        )
        .filter(Ticket.created_at >= since)
        .group_by(func.date(Ticket.created_at))
        .order_by(func.date(Ticket.created_at))
        .all()
    )
    return jsonify([{'day': str(r.day), 'count': r.count} for r in rows])


# ---------------------------------------------------------------------------
# JSON API — tickets by status / priority / department
# ---------------------------------------------------------------------------

@bp.route('/api/tickets-by-status')
@login_required
@admin_required
def api_tickets_by_status():
    rows = db.session.query(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status).all()
    return jsonify([{'status': r[0], 'count': r[1]} for r in rows])


@bp.route('/api/tickets-by-priority')
@login_required
@admin_required
def api_tickets_by_priority():
    rows = db.session.query(Ticket.priority, func.count(Ticket.id)).group_by(Ticket.priority).all()
    return jsonify([{'priority': r[0], 'count': r[1]} for r in rows])


@bp.route('/api/tickets-by-department')
@login_required
@admin_required
def api_tickets_by_department():
    rows = (
        db.session.query(Department.name, func.count(Ticket.id))
        .join(Ticket, Ticket.department_id == Department.id)
        .group_by(Department.name)
        .order_by(func.count(Ticket.id).desc())
        .all()
    )
    return jsonify([{'department': r[0], 'count': r[1]} for r in rows])


# ---------------------------------------------------------------------------
# JSON API — SLA compliance by priority
# ---------------------------------------------------------------------------

@bp.route('/api/sla-compliance')
@login_required
@admin_required
def api_sla_compliance():
    result = []
    for p in Ticket.PRIORITIES:
        total = (
            db.session.query(func.count(TicketSLA.id))
            .join(Ticket, Ticket.id == TicketSLA.ticket_pk)
            .filter(Ticket.priority == p)
            .scalar() or 0
        )
        fr_met = (
            db.session.query(func.count(TicketSLA.id))
            .join(Ticket, Ticket.id == TicketSLA.ticket_pk)
            .filter(Ticket.priority == p, TicketSLA.first_response_met == True)
            .scalar() or 0
        )
        res_met = (
            db.session.query(func.count(TicketSLA.id))
            .join(Ticket, Ticket.id == TicketSLA.ticket_pk)
            .filter(Ticket.priority == p, TicketSLA.resolution_met == True)
            .scalar() or 0
        )
        result.append({
            'priority': p,
            'total': total,
            'fr_rate': round(fr_met / total * 100, 1) if total > 0 else 0,
            'res_rate': round(res_met / total * 100, 1) if total > 0 else 0,
        })
    return jsonify(result)


# ---------------------------------------------------------------------------
# JSON API — agent performance
# ---------------------------------------------------------------------------

@bp.route('/api/agent-performance')
@login_required
@admin_required
def api_agent_performance():
    agent_role = Role.query.filter_by(name='Agent').first()
    admin_role = Role.query.filter_by(name='Admin').first()
    role_ids = [r.id for r in [agent_role, admin_role] if r]

    agents = (
        User.query.filter(User.role_id.in_(role_ids), User.is_active == True)
        .order_by(User.first_name)
        .all()
    )

    result = []
    for agent in agents:
        assigned = Ticket.query.filter_by(assigned_to=agent.id).count()
        resolved = Ticket.query.filter_by(assigned_to=agent.id).filter(
            Ticket.status.in_(['Resolved', 'Closed'])
        ).count()
        active = Ticket.query.filter_by(assigned_to=agent.id).filter(
            Ticket.status.in_(['Open', 'InProgress', 'Hold', 'Reopened'])
        ).count()

        # Avg resolution time in hours
        resolved_tix = Ticket.query.filter(
            Ticket.assigned_to == agent.id,
            Ticket.resolved_at.isnot(None),
        ).all()
        avg_hours = None
        if resolved_tix:
            total_sec = 0
            cnt = 0
            for t in resolved_tix:
                ra = t.resolved_at
                ca = t.created_at
                if ra and ca:
                    if ra.tzinfo is None:
                        ra = ra.replace(tzinfo=timezone.utc)
                    if ca.tzinfo is None:
                        ca = ca.replace(tzinfo=timezone.utc)
                    total_sec += (ra - ca).total_seconds()
                    cnt += 1
            if cnt:
                avg_hours = round(total_sec / cnt / 3600, 1)

        result.append({
            'agent': agent.full_name,
            'assigned': assigned,
            'active': active,
            'resolved': resolved,
            'avg_hours': avg_hours,
        })

    result.sort(key=lambda x: x['resolved'], reverse=True)
    return jsonify(result)


# ---------------------------------------------------------------------------
# JSON API — escalation summary
# ---------------------------------------------------------------------------

@bp.route('/api/escalation-summary')
@login_required
@admin_required
def api_escalation_summary():
    rows = (
        db.session.query(TicketEscalation.level, func.count(TicketEscalation.id))
        .group_by(TicketEscalation.level)
        .order_by(TicketEscalation.level)
        .all()
    )
    return jsonify([{'level': f'L{r[0]}', 'count': r[1]} for r in rows])


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

@bp.route('/export/tickets')
@login_required
@admin_required
def export_tickets():
    days = request.args.get('days', 30, type=int)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    tickets = (
        Ticket.query
        .filter(Ticket.created_at >= since)
        .order_by(Ticket.created_at.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Ticket ID', 'Title', 'Status', 'Priority', 'Department',
        'Assigned To', 'Created By', 'Created At', 'Resolved At',
        'FR Due', 'FR Breached', 'Resolution Due', 'Res Breached',
    ])

    for t in tickets:
        sla = t.sla
        writer.writerow([
            t.ticket_id,
            t.title,
            t.status,
            t.priority,
            t.department.name if t.department else '',
            t.assignee.full_name if t.assignee else 'Unassigned',
            t.creator.full_name if t.creator else '',
            t.created_at.strftime('%Y-%m-%d %H:%M') if t.created_at else '',
            t.resolved_at.strftime('%Y-%m-%d %H:%M') if t.resolved_at else '',
            sla.first_response_due.strftime('%Y-%m-%d %H:%M') if sla and sla.first_response_due else '',
            'Yes' if sla and sla.first_response_breached else 'No',
            sla.resolution_due.strftime('%Y-%m-%d %H:%M') if sla and sla.resolution_due else '',
            'Yes' if sla and sla.resolution_breached else 'No',
        ])

    output.seek(0)
    filename = f'tickets_{datetime.now().strftime("%Y%m%d")}.csv'
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )
