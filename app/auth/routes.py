from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import bp
from app.auth.forms import LoginForm, ChangePasswordForm
from app.models.user import User
from app import db


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Contact an administrator.', 'error')
                return redirect(url_for('auth.login'))
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if next_page and not next_page.startswith('/'):
                next_page = None
            return redirect(next_page or url_for('dashboard.index'))
        flash('Invalid email or password.', 'error')

    return render_template('auth/login.html', form=form)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('auth.change_password'))
        if form.new_password.data != form.confirm_password.data:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('auth.change_password'))
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Password changed successfully.', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('auth/change_password.html', form=form)
