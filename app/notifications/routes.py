from flask import render_template, redirect, url_for, jsonify, request
from flask_login import login_required, current_user
from app.notifications import bp
from app.models.notification import Notification
from app import db


@bp.route('/')
@login_required
def index():
    notifications = (
        Notification.query
        .filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(100)
        .all()
    )
    # Mark all as read when the user opens the page
    Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).update({'is_read': True})
    db.session.commit()
    return render_template('notifications/index.html', notifications=notifications)


@bp.route('/mark-read/<int:notif_id>', methods=['POST'])
@login_required
def mark_read(notif_id):
    n = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    n.is_read = True
    db.session.commit()
    next_url = request.referrer or url_for('notifications.index')
    return redirect(next_url)


@bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).update({'is_read': True})
    db.session.commit()
    return redirect(url_for('notifications.index'))


# ---- JSON API ----

@bp.route('/api/unread-count')
@login_required
def unread_count():
    count = Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).count()
    return jsonify({'count': count})


@bp.route('/api/recent')
@login_required
def recent():
    items = (
        Notification.query
        .filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(8)
        .all()
    )
    return jsonify([{
        'id': n.id,
        'type': n.type,
        'title': n.title,
        'message': n.message,
        'is_read': n.is_read,
        'ticket_id': n.ticket.ticket_id if n.ticket else None,
        'created_at': n.created_at.strftime('%d %b %H:%M'),
    } for n in items])
