"""
REST API v1  —  /api/v1/

Authentication: Bearer token in Authorization header.

Endpoints
---------
POST   /api/v1/tokens                  — issue a new token (username+password)
DELETE /api/v1/tokens/<prefix>         — revoke a token
GET    /api/v1/tickets                 — list tickets (paginated)
POST   /api/v1/tickets                 — create ticket
GET    /api/v1/tickets/<ticket_id>     — get one ticket
PATCH  /api/v1/tickets/<ticket_id>/status — change status
GET    /api/v1/departments             — list active departments
GET    /api/v1/me                      — current user info
"""
from datetime import datetime, timezone
from flask import request, jsonify, g
from werkzeug.security import check_password_hash

from app import db
from app.api import bp
from app.api.auth import api_token_required
from app.models.api_token import APIToken
from app.models.user import User
from app.models.ticket import Ticket, TicketMessage, TicketActivityLog
from app.models.department import Department


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ticket_dict(t):
    return {
        'id': t.ticket_id,
        'title': t.title,
        'description': t.description,
        'status': t.status,
        'priority': t.priority,
        'department': t.department.name if t.department else None,
        'created_by': t.creator.full_name,
        'assigned_to': t.assignee.full_name if t.assignee else None,
        'created_at': t.created_at.isoformat(),
        'updated_at': t.updated_at.isoformat(),
        'resolved_at': t.resolved_at.isoformat() if t.resolved_at else None,
    }


def _user_dict(u):
    return {
        'id': u.id,
        'email': u.email,
        'username': u.username,
        'full_name': u.full_name,
        'role': u.role.name,
        'department': u.department.name if u.department else None,
    }


# ---------------------------------------------------------------------------
# Token management (no auth required)
# ---------------------------------------------------------------------------

@bp.route('/tokens', methods=['POST'])
def issue_token():
    """
    Body: {"email": "...", "password": "...", "name": "My App"}
    Returns: {"token": "...", "prefix": "..."}
    """
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip()
    password = data.get('password', '')
    token_name = data.get('name', 'API Token').strip()

    user = User.query.filter_by(email=email, is_active=True).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials.'}), 401

    plain, token_obj = APIToken.generate()
    token_obj.user_id = user.id
    token_obj.name = token_name or 'API Token'
    db.session.add(token_obj)
    db.session.commit()

    return jsonify({
        'token': plain,
        'prefix': token_obj.prefix,
        'message': 'Store this token securely — it will not be shown again.',
    }), 201


@bp.route('/tokens/<prefix>', methods=['DELETE'])
@api_token_required
def revoke_token(prefix):
    """Revoke a token by its prefix (must belong to the authenticated user)."""
    token = APIToken.query.filter_by(
        prefix=prefix, user_id=g.api_user.id
    ).first()
    if not token:
        return jsonify({'error': 'Token not found.'}), 404
    token.is_active = False
    db.session.commit()
    return jsonify({'message': 'Token revoked.'}), 200


# ---------------------------------------------------------------------------
# Current user
# ---------------------------------------------------------------------------

@bp.route('/me', methods=['GET'])
@api_token_required
def me():
    return jsonify(_user_dict(g.api_user))


# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------

@bp.route('/departments', methods=['GET'])
@api_token_required
def list_departments():
    depts = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    return jsonify([{'id': d.id, 'name': d.name} for d in depts])


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------

@bp.route('/tickets', methods=['GET'])
@api_token_required
def list_tickets():
    """
    Query params:
      status, priority, department_id, page (default 1), per_page (default 20, max 100)
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    q = Ticket.query
    user = g.api_user

    # Non-admin users can only see their own + assigned tickets
    if not (user.has_role('Admin') or user.has_role('Agent')):
        q = q.filter(
            (Ticket.created_by == user.id) | (Ticket.assigned_to == user.id)
        )

    if request.args.get('status'):
        q = q.filter(Ticket.status == request.args['status'])
    if request.args.get('priority'):
        q = q.filter(Ticket.priority == request.args['priority'])
    if request.args.get('department_id'):
        q = q.filter(Ticket.department_id == request.args.get('department_id', type=int))

    pagination = q.order_by(Ticket.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        'tickets': [_ticket_dict(t) for t in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages,
        'per_page': per_page,
    })


@bp.route('/tickets', methods=['POST'])
@api_token_required
def create_ticket():
    """
    Body (JSON):
      title*, description*, department_id*, priority (default Medium),
      problem_id, assigned_to (user id)
    """
    data = request.get_json(silent=True) or {}

    title = (data.get('title') or '').strip()
    description = (data.get('description') or '').strip()
    department_id = data.get('department_id')
    priority = data.get('priority', 'Medium')

    if not title:
        return jsonify({'error': 'title is required.'}), 422
    if not description:
        return jsonify({'error': 'description is required.'}), 422
    if not department_id:
        return jsonify({'error': 'department_id is required.'}), 422
    if priority not in Ticket.PRIORITIES:
        return jsonify({'error': f'priority must be one of {Ticket.PRIORITIES}'}), 422

    dept = db.session.get(Department, department_id)
    if not dept or not dept.is_active:
        return jsonify({'error': 'Invalid department_id.'}), 422

    ticket_id = Ticket.generate_ticket_id()
    ticket = Ticket(
        ticket_id=ticket_id,
        title=title,
        description=description,
        department_id=department_id,
        priority=priority,
        problem_id=data.get('problem_id'),
        created_by=g.api_user.id,
    )

    # Optional assignment
    assignee_id = data.get('assigned_to')
    if assignee_id:
        assignee = db.session.get(User, assignee_id)
        if assignee and assignee.is_active:
            ticket.assigned_to = assignee.id

    db.session.add(ticket)
    db.session.flush()

    db.session.add(TicketActivityLog(
        ticket_pk=ticket.id,
        user_id=g.api_user.id,
        action='created',
        details=f'Ticket created via API by {g.api_user.full_name}',
    ))
    db.session.commit()

    # Attach SLA
    try:
        from app.sla.engine import attach_sla
        attach_sla(ticket)
        db.session.commit()
    except Exception:
        pass

    return jsonify(_ticket_dict(ticket)), 201


@bp.route('/tickets/<ticket_id>', methods=['GET'])
@api_token_required
def get_ticket(ticket_id):
    ticket = Ticket.query.filter_by(ticket_id=ticket_id).first()
    if not ticket:
        return jsonify({'error': 'Ticket not found.'}), 404

    user = g.api_user
    if not (user.has_role('Admin') or user.has_role('Agent') or
            ticket.created_by == user.id or ticket.assigned_to == user.id):
        return jsonify({'error': 'Forbidden.'}), 403

    # Include messages
    messages = []
    for m in ticket.messages.filter_by(is_internal=False).all():
        messages.append({
            'id': m.id,
            'author': m.user.full_name,
            'content': m.content,
            'created_at': m.created_at.isoformat(),
        })

    result = _ticket_dict(ticket)
    result['messages'] = messages
    return jsonify(result)


@bp.route('/tickets/<ticket_id>/status', methods=['PATCH'])
@api_token_required
def update_ticket_status(ticket_id):
    """
    Body: {"status": "InProgress", "remarks": "..."}
    Agents/Admins only.
    """
    user = g.api_user
    if not (user.has_role('Admin') or user.has_role('Agent')):
        return jsonify({'error': 'Forbidden. Agents or Admins only.'}), 403

    ticket = Ticket.query.filter_by(ticket_id=ticket_id).first()
    if not ticket:
        return jsonify({'error': 'Ticket not found.'}), 404

    data = request.get_json(silent=True) or {}
    new_status = data.get('status', '').strip()
    remarks = data.get('remarks', '').strip()

    if new_status not in Ticket.STATUSES:
        return jsonify({'error': f'status must be one of {Ticket.STATUSES}'}), 422

    old_status = ticket.status
    ticket.status = new_status
    now = datetime.now(timezone.utc)

    if new_status in ('Resolved',):
        ticket.resolved_at = now
    elif new_status == 'Closed':
        ticket.closed_at = now

    db.session.add(TicketActivityLog(
        ticket_pk=ticket.id,
        user_id=user.id,
        action='status_changed',
        details=f'Status changed from {old_status} to {new_status} via API. {remarks}'.strip(),
    ))
    db.session.commit()

    return jsonify({'message': 'Status updated.', 'ticket': _ticket_dict(ticket)})


@bp.route('/tickets/<ticket_id>/messages', methods=['POST'])
@api_token_required
def add_message(ticket_id):
    """
    Body: {"content": "...", "is_internal": false}
    """
    ticket = Ticket.query.filter_by(ticket_id=ticket_id).first()
    if not ticket:
        return jsonify({'error': 'Ticket not found.'}), 404

    user = g.api_user
    if not (user.has_role('Admin') or user.has_role('Agent') or
            ticket.created_by == user.id or ticket.assigned_to == user.id):
        return jsonify({'error': 'Forbidden.'}), 403

    data = request.get_json(silent=True) or {}
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'error': 'content is required.'}), 422

    is_internal = bool(data.get('is_internal', False))
    msg = TicketMessage(
        ticket_pk=ticket.id,
        user_id=user.id,
        content=content,
        is_internal=is_internal,
    )
    db.session.add(msg)
    db.session.commit()

    return jsonify({
        'id': msg.id,
        'author': user.full_name,
        'content': msg.content,
        'is_internal': msg.is_internal,
        'created_at': msg.created_at.isoformat(),
    }), 201
