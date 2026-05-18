from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.approvals import bp
from app.models.approval import ApprovalRequest, ApprovalAction, ApprovalHistory
from app.models.ticket import Ticket, TicketActivityLog, TicketStatusHistory
from app.models.user import User
from app import db
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _log_status(ticket, old_status, new_status, remarks, actor_id):
    db.session.add(TicketStatusHistory(
        ticket_pk=ticket.id,
        user_id=actor_id,
        old_status=old_status,
        new_status=new_status,
        remarks=remarks,
    ))
    db.session.add(TicketActivityLog(
        ticket_pk=ticket.id,
        user_id=actor_id,
        action='status_changed',
        details=f'{old_status} -> {new_status}: {remarks}',
    ))


# ---------------------------------------------------------------------------
# My approvals to action  (any logged-in user)
# ---------------------------------------------------------------------------

@bp.route('/')
@login_required
def index():
    """Show pending approvals where the current user is the designated approver."""
    pending = (
        ApprovalRequest.query
        .filter_by(approver_id=current_user.id, status='pending')
        .order_by(ApprovalRequest.created_at.asc())
        .all()
    )
    recent = (
        ApprovalRequest.query
        .filter(
            ApprovalRequest.approver_id == current_user.id,
            ApprovalRequest.status != 'pending',
        )
        .order_by(ApprovalRequest.created_at.desc())
        .limit(20)
        .all()
    )
    return render_template('approvals/index.html', pending=pending, recent=recent)


# ---------------------------------------------------------------------------
# Approve
# ---------------------------------------------------------------------------

@bp.route('/<int:approval_id>/approve', methods=['POST'])
@login_required
def approve(approval_id):
    approval = db.session.get(ApprovalRequest, approval_id)
    if not approval or approval.status != 'pending':
        flash('Approval request not found or already resolved.', 'warning')
        return redirect(url_for('approvals.index'))

    # Only the designated approver (or any Admin) may act
    if approval.approver_id != current_user.id and not current_user.has_role('Admin'):
        flash('You are not authorised to action this approval.', 'error')
        return redirect(url_for('tickets.view', ticket_id=approval.ticket.ticket_id))

    remarks = request.form.get('remarks', '').strip()

    action = ApprovalAction(
        approval_request_id=approval.id,
        actioned_by=current_user.id,
        action='approved',
        remarks=remarks,
    )
    db.session.add(action)

    approval.status = 'approved'
    approval.resolved_at = datetime.now(timezone.utc)

    db.session.add(ApprovalHistory(
        approval_request_id=approval.id,
        ticket_pk=approval.ticket_pk,
        action='approved',
        details=f'Approved by {current_user.full_name}. {remarks}'.strip(),
    ))

    # Ticket: Hold → InProgress + resume SLA
    ticket = approval.ticket
    old_status = ticket.status
    ticket.status = 'InProgress'

    try:
        from app.sla.engine import resume_sla
        resume_sla(ticket)
    except Exception as exc:
        from flask import current_app
        current_app.logger.warning('SLA resume failed: %s', exc)

    _log_status(ticket, old_status, 'InProgress',
                f'Approval approved by {current_user.full_name}. {remarks}'.strip(),
                current_user.id)

    try:
        from app.notifications.service import notify_approval_resolved
        notify_approval_resolved(approval)
    except Exception:
        pass

    db.session.commit()
    flash(f'Approval granted. Ticket {ticket.ticket_id} is back In Progress.', 'success')
    return redirect(url_for('tickets.view', ticket_id=ticket.ticket_id))


# ---------------------------------------------------------------------------
# Reject
# ---------------------------------------------------------------------------

@bp.route('/<int:approval_id>/reject', methods=['POST'])
@login_required
def reject(approval_id):
    approval = db.session.get(ApprovalRequest, approval_id)
    if not approval or approval.status != 'pending':
        flash('Approval request not found or already resolved.', 'warning')
        return redirect(url_for('approvals.index'))

    if approval.approver_id != current_user.id and not current_user.has_role('Admin'):
        flash('You are not authorised to action this approval.', 'error')
        return redirect(url_for('tickets.view', ticket_id=approval.ticket.ticket_id))

    remarks = request.form.get('remarks', '').strip()

    action = ApprovalAction(
        approval_request_id=approval.id,
        actioned_by=current_user.id,
        action='rejected',
        remarks=remarks,
    )
    db.session.add(action)

    approval.status = 'rejected'
    approval.resolved_at = datetime.now(timezone.utc)

    db.session.add(ApprovalHistory(
        approval_request_id=approval.id,
        ticket_pk=approval.ticket_pk,
        action='rejected',
        details=f'Rejected by {current_user.full_name}. {remarks}'.strip(),
    ))

    # Ticket: Hold → InProgress + resume SLA regardless of rejection
    ticket = approval.ticket
    old_status = ticket.status
    ticket.status = 'InProgress'

    try:
        from app.sla.engine import resume_sla
        resume_sla(ticket)
    except Exception as exc:
        from flask import current_app
        current_app.logger.warning('SLA resume failed: %s', exc)

    _log_status(ticket, old_status, 'InProgress',
                f'Approval rejected by {current_user.full_name}. {remarks}'.strip(),
                current_user.id)

    try:
        from app.notifications.service import notify_approval_resolved
        notify_approval_resolved(approval)
    except Exception:
        pass

    db.session.commit()
    flash(f'Approval rejected. Ticket {ticket.ticket_id} is back In Progress.', 'success')
    return redirect(url_for('tickets.view', ticket_id=ticket.ticket_id))


# ---------------------------------------------------------------------------
# Request approval  (any logged-in user)
# ---------------------------------------------------------------------------

@bp.route('/request', methods=['POST'])
@login_required
def request_approval():
    ticket_id   = request.form.get('ticket_id', '').strip()
    approver_id = int(request.form.get('approver_id') or 0)
    reason      = request.form.get('reason', '').strip()

    ticket = Ticket.query.filter_by(ticket_id=ticket_id).first_or_404()

    # Access check: end users can only request for their own tickets
    if current_user.has_role('End User'):
        if (ticket.created_by != current_user.id and
                ticket.created_on_behalf_of != current_user.id):
            flash('You do not have access to this ticket.', 'error')
            return redirect(url_for('tickets.index'))

    if ticket.status in ('Resolved', 'Closed', 'Rejected', 'Hold'):
        flash('Approval cannot be requested for a ticket in this status.', 'error')
        return redirect(url_for('tickets.view', ticket_id=ticket_id))

    # Validate approver
    approver = User.query.filter_by(id=approver_id, is_active=True).first()
    if not approver:
        flash('Please select a valid approver.', 'error')
        return redirect(url_for('tickets.view', ticket_id=ticket_id))

    # Block if there's already a pending request
    existing = ApprovalRequest.query.filter_by(
        ticket_pk=ticket.id, status='pending'
    ).first()
    if existing:
        flash('A pending approval request already exists for this ticket.', 'warning')
        return redirect(url_for('tickets.view', ticket_id=ticket_id))

    # Create approval request
    approval = ApprovalRequest(
        ticket_pk       = ticket.id,
        requested_by    = current_user.id,
        approver_id     = approver.id,
        reason          = reason or None,
        requested_action= 'Hold',
        status          = 'pending',
    )
    db.session.add(approval)
    db.session.flush()

    db.session.add(ApprovalHistory(
        approval_request_id=approval.id,
        ticket_pk=ticket.id,
        action='requested',
        details=(
            f'Approval requested by {current_user.full_name} '
            f'for {approver.full_name}. Reason: {reason or "none"}'
        ),
    ))
    db.session.add(TicketActivityLog(
        ticket_pk=ticket.id,
        user_id=current_user.id,
        action='approval_requested',
        details=f'Approval requested — sent to {approver.full_name}. Reason: {reason or "none"}',
    ))

    # Ticket immediately goes to Hold + SLA paused
    old_status = ticket.status
    ticket.status = 'Hold'

    try:
        from app.sla.engine import pause_sla
        pause_sla(ticket)
    except Exception as exc:
        from flask import current_app
        current_app.logger.warning('SLA pause failed: %s', exc)

    _log_status(ticket, old_status, 'Hold',
                f'Ticket placed on Hold pending approval from {approver.full_name}',
                current_user.id)

    try:
        from app.notifications.service import notify_approval_requested
        notify_approval_requested(approval)
    except Exception:
        pass

    db.session.commit()
    flash(
        f'Approval request sent to {approver.full_name}. '
        f'Ticket {ticket.ticket_id} is now on Hold.',
        'success',
    )
    return redirect(url_for('tickets.view', ticket_id=ticket_id))


# ---------------------------------------------------------------------------
# My submitted requests  (any logged-in user)
# ---------------------------------------------------------------------------

@bp.route('/my-requests')
@login_required
def my_requests():
    reqs = (
        ApprovalRequest.query
        .filter_by(requested_by=current_user.id)
        .order_by(ApprovalRequest.created_at.desc())
        .all()
    )
    return render_template('approvals/my_requests.html', requests=reqs)
