"""
Notification service – creates in-app Notification records
and optionally sends email via Flask-Mail.
"""
from app import db


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def create_notification(user_id, notif_type, title, message, ticket_pk=None):
    """Insert an in-app notification row (does NOT commit – caller commits)."""
    from app.models.notification import Notification
    n = Notification(
        user_id=user_id,
        type=notif_type,
        title=title,
        message=message,
        ticket_pk=ticket_pk,
    )
    db.session.add(n)
    return n


def send_email(to_address, subject, body):
    """
    Send a plain-text email.  Fails silently if SMTP not configured.
    Returns True on success.
    """
    try:
        from flask import current_app
        from flask_mail import Message
        from app import mail

        if not current_app.config.get('MAIL_USERNAME'):
            return False

        msg = Message(subject=subject, recipients=[to_address], body=body)
        mail.send(msg)
        return True
    except Exception as exc:
        try:
            from flask import current_app
            current_app.logger.warning(f'Email send failed to {to_address}: {exc}')
        except Exception:
            pass
        return False


# ---------------------------------------------------------------------------
# Domain-specific notification helpers
# ---------------------------------------------------------------------------

def notify_ticket_created(ticket):
    """Notify the assignee (if any) when a ticket is created."""
    if not ticket.assignee:
        return
    create_notification(
        user_id=ticket.assigned_to,
        notif_type='assigned',
        title=f'New Ticket Assigned: {ticket.ticket_id}',
        message=f'Ticket "{ticket.title}" has been assigned to you.',
        ticket_pk=ticket.id,
    )
    send_email(
        ticket.assignee.email,
        f'[CKSM] New Ticket Assigned: {ticket.ticket_id}',
        (
            f'Hello {ticket.assignee.first_name},\n\n'
            f'Ticket {ticket.ticket_id} "{ticket.title}" has been assigned to you.\n'
            f'Priority: {ticket.priority} | Department: {ticket.department.name}\n\n'
            f'Please log in to CKSM to action this ticket.'
        ),
    )


def notify_ticket_assigned(ticket, old_assignee=None):
    """Notify the new assignee on (re)assignment."""
    if not ticket.assignee:
        return
    create_notification(
        user_id=ticket.assigned_to,
        notif_type='assigned',
        title=f'Ticket Assigned: {ticket.ticket_id}',
        message=f'Ticket "{ticket.title}" has been assigned to you.',
        ticket_pk=ticket.id,
    )
    send_email(
        ticket.assignee.email,
        f'[CKSM] Ticket Assigned to You: {ticket.ticket_id}',
        (
            f'Hello {ticket.assignee.first_name},\n\n'
            f'Ticket {ticket.ticket_id} "{ticket.title}" has been assigned to you.\n'
            f'Priority: {ticket.priority} | Department: {ticket.department.name}\n\n'
            f'Please log in to CKSM to action this ticket.'
        ),
    )


def notify_reply_added(ticket, message_obj):
    """
    Notify the ticket requester and assignee when a reply is added.
    Internal notes are not emailed to the requester.
    """
    notified = set()
    requester = ticket.effective_requester

    if requester and requester.id != message_obj.user_id:
        notified.add(requester.id)
        create_notification(
            user_id=requester.id,
            notif_type='replied',
            title=f'New Reply on: {ticket.ticket_id}',
            message=f'{message_obj.user.full_name} replied on ticket "{ticket.title}".',
            ticket_pk=ticket.id,
        )
        if not message_obj.is_internal:
            send_email(
                requester.email,
                f'[CKSM] New Reply on Ticket {ticket.ticket_id}',
                (
                    f'Hello {requester.first_name},\n\n'
                    f'A reply has been added to your ticket {ticket.ticket_id} '
                    f'"{ticket.title}".\n\n'
                    f'From: {message_obj.user.full_name}\n\n'
                    f'Please log in to CKSM to view the reply.'
                ),
            )

    if (ticket.assignee and
            ticket.assigned_to not in notified and
            ticket.assigned_to != message_obj.user_id):
        create_notification(
            user_id=ticket.assigned_to,
            notif_type='replied',
            title=f'New Reply on: {ticket.ticket_id}',
            message=f'{message_obj.user.full_name} replied on ticket "{ticket.title}".',
            ticket_pk=ticket.id,
        )


def notify_status_changed(ticket, old_status, new_status):
    """Notify requester and assignee of a status change."""
    notified = set()
    requester = ticket.effective_requester

    if requester:
        notified.add(requester.id)
        create_notification(
            user_id=requester.id,
            notif_type='status_changed',
            title=f'Ticket Status Updated: {ticket.ticket_id}',
            message=f'Ticket "{ticket.title}" changed from {old_status} to {new_status}.',
            ticket_pk=ticket.id,
        )
        send_email(
            requester.email,
            f'[CKSM] Ticket {ticket.ticket_id} Status: {new_status}',
            (
                f'Hello {requester.first_name},\n\n'
                f'Ticket {ticket.ticket_id} "{ticket.title}" status updated.\n'
                f'From: {old_status}  →  To: {new_status}\n\n'
                f'Please log in to CKSM for details.'
            ),
        )

    if ticket.assignee and ticket.assigned_to not in notified:
        create_notification(
            user_id=ticket.assigned_to,
            notif_type='status_changed',
            title=f'Ticket Status Updated: {ticket.ticket_id}',
            message=f'Ticket "{ticket.title}" changed from {old_status} to {new_status}.',
            ticket_pk=ticket.id,
        )


def notify_approval_requested(approval_request):
    """Notify the designated approver of a new approval request."""
    ticket = approval_request.ticket
    approver = approval_request.approver
    if not approver:
        return

    create_notification(
        user_id=approver.id,
        notif_type='approval_requested',
        title=f'Approval Required: {ticket.ticket_id}',
        message=(
            f'{approval_request.requester.full_name} requests your approval for '
            f'ticket "{ticket.title}".'
        ),
        ticket_pk=ticket.id,
    )
    send_email(
        approver.email,
        f'[CKSM] Your Approval Required: {ticket.ticket_id}',
        (
            f'Hello {approver.first_name},\n\n'
            f'{approval_request.requester.full_name} has requested your approval for\n'
            f'ticket {ticket.ticket_id} - "{ticket.title}".\n\n'
            f'Reason: {approval_request.reason or "No reason provided"}\n\n'
            f'The ticket is now on Hold. Please log in to CKSM to approve or reject.'
        ),
    )


def notify_approval_resolved(approval_request):
    """Notify the requester of the approval decision."""
    ticket = approval_request.ticket
    status_label = approval_request.status.capitalize()
    actioner_name = (
        approval_request.approver.full_name
        if approval_request.approver else 'Approver'
    )

    create_notification(
        user_id=approval_request.requested_by,
        notif_type='approval_resolved',
        title=f'Approval {status_label}: {ticket.ticket_id}',
        message=(
            f'Your approval request for ticket "{ticket.title}" was '
            f'{approval_request.status} by {actioner_name}.'
        ),
        ticket_pk=ticket.id,
    )
    send_email(
        approval_request.requester.email,
        f'[CKSM] Approval {status_label}: {ticket.ticket_id}',
        (
            f'Hello {approval_request.requester.first_name},\n\n'
            f'Your approval request for ticket {ticket.ticket_id} "{ticket.title}" '
            f'has been {approval_request.status} by {actioner_name}.\n'
            f'The ticket is now back In Progress.\n\n'
            f'Please log in to CKSM for details.'
        ),
    )
