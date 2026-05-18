import json
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.admin import bp
from app.admin.forms import (
    CreateUserForm, EditUserForm, DepartmentForm, ProblemForm,
    SubProblemForm, CategoryForm, SubCategoryForm
)
from app.auth.decorators import admin_required
from app.models.user import User, Role
from app.models.department import Department, Problem, SubProblem, Category, SubCategory
from app.models.forms import FormTemplate, FormField
from app.models.kb import KBCategory, KBArticle
from app.models.assignment_rule import (
    AssignmentRule, AssignmentRuleGroup, AssignmentRuleCondition
)
from app.models.priority_rule import (
    PriorityRule, PriorityRuleGroup, PriorityRuleCondition, PRIORITY_VALUES
)
from app import db


@bp.route('/')
@login_required
@admin_required
def index():
    users = User.query.order_by(User.created_at.desc()).all()
    departments = Department.query.order_by(Department.name).all()
    return render_template('admin/index.html', users=users, departments=departments)


# --- User Management ---

@bp.route('/users')
@login_required
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)


@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    form = CreateUserForm()
    form.role_id.choices = [(r.id, r.name) for r in Role.query.order_by(Role.name).all()]
    form.department_id.choices = [(0, '-- None --')] + [
        (d.id, d.name) for d in Department.query.filter_by(is_active=True).order_by(Department.name).all()
    ]

    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already in use.', 'error')
            return render_template('admin/create_user.html', form=form)
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already in use.', 'error')
            return render_template('admin/create_user.html', form=form)

        user = User(
            email=form.email.data,
            username=form.username.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            role_id=form.role_id.data,
            department_id=form.department_id.data if form.department_id.data != 0 else None,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'User {user.full_name} created successfully.', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/create_user.html', form=form)


@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users'))

    form = EditUserForm(obj=user)
    form.role_id.choices = [(r.id, r.name) for r in Role.query.order_by(Role.name).all()]
    form.department_id.choices = [(0, '-- None --')] + [
        (d.id, d.name) for d in Department.query.filter_by(is_active=True).order_by(Department.name).all()
    ]

    if form.validate_on_submit():
        existing = User.query.filter(User.email == form.email.data, User.id != user.id).first()
        if existing:
            flash('Email already in use by another user.', 'error')
            return render_template('admin/edit_user.html', form=form, user=user)

        existing = User.query.filter(User.username == form.username.data, User.id != user.id).first()
        if existing:
            flash('Username already in use by another user.', 'error')
            return render_template('admin/edit_user.html', form=form, user=user)

        user.email = form.email.data
        user.username = form.username.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.phone = form.phone.data
        user.role_id = form.role_id.data
        user.department_id = form.department_id.data if form.department_id.data != 0 else None
        user.is_active = form.is_active.data
        db.session.commit()
        flash(f'User {user.full_name} updated successfully.', 'success')
        return redirect(url_for('admin.users'))

    if request.method == 'GET':
        form.department_id.data = user.department_id or 0

    return render_template('admin/edit_user.html', form=form, user=user)


@bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_password(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users'))

    temp_password = 'Cksm@1234'
    user.set_password(temp_password)
    db.session.commit()
    flash(f'Password for {user.full_name} reset to temporary password: {temp_password}', 'success')
    return redirect(url_for('admin.edit_user', user_id=user.id))


# --- Department Management ---

@bp.route('/departments')
@login_required
@admin_required
def departments():
    all_depts = Department.query.order_by(Department.name).all()
    return render_template('admin/departments.html', departments=all_depts)


@bp.route('/departments/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_department():
    form = DepartmentForm()
    if form.validate_on_submit():
        if Department.query.filter_by(name=form.name.data).first():
            flash('Department already exists.', 'error')
            return render_template('admin/create_department.html', form=form)
        dept = Department(name=form.name.data, description=form.description.data, is_active=form.is_active.data)
        db.session.add(dept)
        db.session.commit()
        flash(f'Department "{dept.name}" created.', 'success')
        return redirect(url_for('admin.departments'))
    return render_template('admin/create_department.html', form=form)


@bp.route('/departments/<int:dept_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_department(dept_id):
    dept = db.session.get(Department, dept_id)
    if not dept:
        flash('Department not found.', 'error')
        return redirect(url_for('admin.departments'))

    form = DepartmentForm(obj=dept)
    if form.validate_on_submit():
        existing = Department.query.filter(Department.name == form.name.data, Department.id != dept.id).first()
        if existing:
            flash('Department name already in use.', 'error')
            return render_template('admin/edit_department.html', form=form, dept=dept)
        dept.name = form.name.data
        dept.description = form.description.data
        dept.is_active = form.is_active.data
        db.session.commit()
        flash(f'Department "{dept.name}" updated.', 'success')
        return redirect(url_for('admin.departments'))
    return render_template('admin/edit_department.html', form=form, dept=dept)


# --- Problem Management ---

@bp.route('/problems')
@login_required
@admin_required
def problems():
    all_problems = Problem.query.order_by(Problem.name).all()
    return render_template('admin/problems.html', problems=all_problems)


@bp.route('/problems/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_problem():
    form = ProblemForm()
    form.department_id.choices = [
        (d.id, d.name) for d in Department.query.filter_by(is_active=True).order_by(Department.name).all()
    ]
    if form.validate_on_submit():
        prob = Problem(name=form.name.data, department_id=form.department_id.data, is_active=form.is_active.data)
        db.session.add(prob)
        db.session.commit()
        flash(f'Problem "{prob.name}" created.', 'success')
        return redirect(url_for('admin.problems'))
    return render_template('admin/create_problem.html', form=form)


@bp.route('/problems/<int:problem_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_problem(problem_id):
    prob = db.session.get(Problem, problem_id)
    if not prob:
        flash('Problem not found.', 'error')
        return redirect(url_for('admin.problems'))
    form = ProblemForm(obj=prob)
    form.department_id.choices = [
        (d.id, d.name) for d in Department.query.filter_by(is_active=True).order_by(Department.name).all()
    ]
    if form.validate_on_submit():
        prob.name = form.name.data
        prob.department_id = form.department_id.data
        prob.is_active = form.is_active.data
        db.session.commit()
        flash(f'Problem "{prob.name}" updated.', 'success')
        return redirect(url_for('admin.problems'))
    return render_template('admin/edit_problem.html', form=form, problem=prob)


# --- Sub-Problem Management ---

@bp.route('/sub-problems')
@login_required
@admin_required
def sub_problems():
    all_sub = SubProblem.query.order_by(SubProblem.name).all()
    return render_template('admin/sub_problems.html', sub_problems=all_sub)


@bp.route('/sub-problems/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_sub_problem():
    form = SubProblemForm()
    all_probs = Problem.query.filter_by(is_active=True).order_by(Problem.name).all()
    form.problem_id.choices = [(p.id, p.name) for p in all_probs]
    if form.validate_on_submit():
        sub = SubProblem(name=form.name.data, problem_id=form.problem_id.data, is_active=form.is_active.data)
        db.session.add(sub)
        db.session.commit()
        flash(f'Sub-Problem "{sub.name}" created.', 'success')
        return redirect(url_for('admin.sub_problems'))
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    return render_template('admin/create_sub_problem.html', form=form,
                           departments=departments, problems=all_probs)


@bp.route('/sub-problems/<int:sub_problem_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_sub_problem(sub_problem_id):
    sub = db.session.get(SubProblem, sub_problem_id)
    if not sub:
        flash('Sub-Problem not found.', 'error')
        return redirect(url_for('admin.sub_problems'))
    form = SubProblemForm(obj=sub)
    all_probs = Problem.query.filter_by(is_active=True).order_by(Problem.name).all()
    form.problem_id.choices = [(p.id, p.name) for p in all_probs]
    if form.validate_on_submit():
        sub.name = form.name.data
        sub.problem_id = form.problem_id.data
        sub.is_active = form.is_active.data
        db.session.commit()
        flash(f'Sub-Problem "{sub.name}" updated.', 'success')
        return redirect(url_for('admin.sub_problems'))
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    preselect = {'dept_id': sub.problem.department_id, 'problem_id': sub.problem_id}
    return render_template('admin/edit_sub_problem.html', form=form, sub_problem=sub,
                           departments=departments, problems=all_probs, preselect=preselect)


# --- Category Management ---

@bp.route('/categories')
@login_required
@admin_required
def categories():
    all_cats = Category.query.order_by(Category.name).all()
    return render_template('admin/categories.html', categories=all_cats)


@bp.route('/categories/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_category():
    form = CategoryForm()
    all_subprobs = SubProblem.query.filter_by(is_active=True).order_by(SubProblem.name).all()
    form.sub_problem_id.choices = [(sp.id, sp.name) for sp in all_subprobs]
    if form.validate_on_submit():
        cat = Category(name=form.name.data, sub_problem_id=form.sub_problem_id.data, is_active=form.is_active.data)
        db.session.add(cat)
        db.session.commit()
        flash(f'Category "{cat.name}" created.', 'success')
        return redirect(url_for('admin.categories'))
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    all_probs = Problem.query.filter_by(is_active=True).order_by(Problem.name).all()
    return render_template('admin/create_category.html', form=form,
                           departments=departments, problems=all_probs, sub_problems=all_subprobs)


@bp.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category(category_id):
    cat = db.session.get(Category, category_id)
    if not cat:
        flash('Category not found.', 'error')
        return redirect(url_for('admin.categories'))
    form = CategoryForm(obj=cat)
    all_subprobs = SubProblem.query.filter_by(is_active=True).order_by(SubProblem.name).all()
    form.sub_problem_id.choices = [(sp.id, sp.name) for sp in all_subprobs]
    if form.validate_on_submit():
        cat.name = form.name.data
        cat.sub_problem_id = form.sub_problem_id.data
        cat.is_active = form.is_active.data
        db.session.commit()
        flash(f'Category "{cat.name}" updated.', 'success')
        return redirect(url_for('admin.categories'))
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    all_probs = Problem.query.filter_by(is_active=True).order_by(Problem.name).all()
    preselect = {
        'dept_id': cat.sub_problem.problem.department_id,
        'problem_id': cat.sub_problem.problem_id,
        'sub_problem_id': cat.sub_problem_id,
    }
    return render_template('admin/edit_category.html', form=form, category=cat,
                           departments=departments, problems=all_probs,
                           sub_problems=all_subprobs, preselect=preselect)


# --- Sub-Category Management ---

@bp.route('/sub-categories')
@login_required
@admin_required
def sub_categories():
    all_subcats = SubCategory.query.order_by(SubCategory.name).all()
    return render_template('admin/sub_categories.html', sub_categories=all_subcats)


@bp.route('/sub-categories/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_sub_category():
    form = SubCategoryForm()
    all_cats = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    form.category_id.choices = [(c.id, c.name) for c in all_cats]
    if form.validate_on_submit():
        subcat = SubCategory(name=form.name.data, category_id=form.category_id.data, is_active=form.is_active.data)
        db.session.add(subcat)
        db.session.commit()
        flash(f'Sub-Category "{subcat.name}" created.', 'success')
        return redirect(url_for('admin.sub_categories'))
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    all_probs = Problem.query.filter_by(is_active=True).order_by(Problem.name).all()
    all_subprobs = SubProblem.query.filter_by(is_active=True).order_by(SubProblem.name).all()
    return render_template('admin/create_sub_category.html', form=form,
                           departments=departments, problems=all_probs,
                           sub_problems=all_subprobs, categories=all_cats)


@bp.route('/sub-categories/<int:sub_category_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_sub_category(sub_category_id):
    subcat = db.session.get(SubCategory, sub_category_id)
    if not subcat:
        flash('Sub-Category not found.', 'error')
        return redirect(url_for('admin.sub_categories'))
    form = SubCategoryForm(obj=subcat)
    all_cats = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    form.category_id.choices = [(c.id, c.name) for c in all_cats]
    if form.validate_on_submit():
        subcat.name = form.name.data
        subcat.category_id = form.category_id.data
        subcat.is_active = form.is_active.data
        db.session.commit()
        flash(f'Sub-Category "{subcat.name}" updated.', 'success')
        return redirect(url_for('admin.sub_categories'))
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    all_probs = Problem.query.filter_by(is_active=True).order_by(Problem.name).all()
    all_subprobs = SubProblem.query.filter_by(is_active=True).order_by(SubProblem.name).all()
    preselect = {
        'dept_id': subcat.category.sub_problem.problem.department_id,
        'problem_id': subcat.category.sub_problem.problem_id,
        'sub_problem_id': subcat.category.sub_problem_id,
        'category_id': subcat.category_id,
    }
    return render_template('admin/edit_sub_category.html', form=form, sub_category=subcat,
                           departments=departments, problems=all_probs,
                           sub_problems=all_subprobs, categories=all_cats,
                           preselect=preselect)


# --- API endpoints for dynamic dropdowns ---

@bp.route('/api/problems/<int:department_id>')
@login_required
def api_problems(department_id):
    from flask import jsonify
    problems = Problem.query.filter_by(department_id=department_id, is_active=True).order_by(Problem.name).all()
    return jsonify([{'id': p.id, 'name': p.name} for p in problems])


@bp.route('/api/sub-problems/<int:problem_id>')
@login_required
def api_sub_problems(problem_id):
    from flask import jsonify
    subs = SubProblem.query.filter_by(problem_id=problem_id, is_active=True).order_by(SubProblem.name).all()
    return jsonify([{'id': s.id, 'name': s.name} for s in subs])


@bp.route('/api/categories/<int:sub_problem_id>')
@login_required
def api_categories(sub_problem_id):
    from flask import jsonify
    cats = Category.query.filter_by(sub_problem_id=sub_problem_id, is_active=True).order_by(Category.name).all()
    return jsonify([{'id': c.id, 'name': c.name} for c in cats])


@bp.route('/api/sub-categories/<int:category_id>')
@login_required
def api_sub_categories(category_id):
    from flask import jsonify
    subcats = SubCategory.query.filter_by(category_id=category_id, is_active=True).order_by(SubCategory.name).all()
    return jsonify([{'id': s.id, 'name': s.name} for s in subcats])


@bp.route('/api/agents/<int:department_id>')
@login_required
def api_agents(department_id):
    agents = User.query.filter_by(department_id=department_id, is_active=True).join(Role).filter(
        Role.name.in_(['Agent', 'Admin'])
    ).order_by(User.first_name).all()
    return jsonify([{'id': a.id, 'name': a.full_name} for a in agents])


# ---------------------------------------------------------------------------
# API: dynamic form fields for a dept+problem combination (used on ticket create)
# ---------------------------------------------------------------------------

@bp.route('/api/form-fields')
@login_required
def api_form_fields():
    """
    Return active form fields for the best-matching FormTemplate.
    Matching order: dept+problem → dept only → global (no dept, no problem).
    """
    department_id = request.args.get('department_id', type=int)
    problem_id = request.args.get('problem_id', type=int)

    template = None
    if department_id and problem_id:
        template = FormTemplate.query.filter_by(
            department_id=department_id, problem_id=problem_id, is_active=True
        ).first()
    if not template and department_id:
        template = FormTemplate.query.filter_by(
            department_id=department_id, problem_id=None, is_active=True
        ).first()
    if not template:
        template = FormTemplate.query.filter_by(
            department_id=None, problem_id=None, is_active=True
        ).first()

    if not template:
        return jsonify([])

    fields = []
    for f in template.get_active_fields():
        fields.append({
            'id': f.id,
            'label': f.label,
            'field_name': f.field_name,
            'field_type': f.field_type,
            'options': f.get_options_list(),
            'placeholder': f.placeholder or '',
            'is_required': f.is_required,
        })
    return jsonify(fields)


# ---------------------------------------------------------------------------
# Form Template Management
# ---------------------------------------------------------------------------

@bp.route('/form-templates')
@login_required
@admin_required
def form_templates():
    templates = FormTemplate.query.order_by(FormTemplate.name).all()
    return render_template('admin/form_templates.html', templates=templates)


@bp.route('/form-templates/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_form_template():
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    problems = Problem.query.filter_by(is_active=True).order_by(Problem.name).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        dept_id = request.form.get('department_id', type=int) or None
        prob_id = request.form.get('problem_id', type=int) or None
        is_active = request.form.get('is_active') == 'on'

        if not name:
            flash('Template name is required.', 'error')
        else:
            tmpl = FormTemplate(name=name, department_id=dept_id,
                                problem_id=prob_id, is_active=is_active)
            db.session.add(tmpl)
            db.session.commit()
            flash(f'Form template "{tmpl.name}" created.', 'success')
            return redirect(url_for('admin.form_template_detail', template_id=tmpl.id))

    return render_template('admin/create_form_template.html',
                           departments=departments, problems=problems)


@bp.route('/form-templates/<int:template_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def form_template_detail(template_id):
    tmpl = db.session.get(FormTemplate, template_id)
    if not tmpl:
        flash('Template not found.', 'error')
        return redirect(url_for('admin.form_templates'))

    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    problems = Problem.query.filter_by(is_active=True).order_by(Problem.name).all()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'edit_template':
            tmpl.name = request.form.get('name', tmpl.name).strip()
            tmpl.department_id = request.form.get('department_id', type=int) or None
            tmpl.problem_id = request.form.get('problem_id', type=int) or None
            tmpl.is_active = request.form.get('is_active') == 'on'
            db.session.commit()
            flash('Template updated.', 'success')

        elif action == 'add_field':
            label = request.form.get('label', '').strip()
            field_name = request.form.get('field_name', '').strip()
            field_type = request.form.get('field_type', 'text')
            placeholder = request.form.get('placeholder', '').strip()
            is_required = request.form.get('is_required') == 'on'
            raw_options = request.form.get('options', '').strip()
            order = request.form.get('order', 0, type=int)

            if not label or not field_name:
                flash('Label and field name are required.', 'error')
            else:
                # Parse options (one per line)
                options_list = [o.strip() for o in raw_options.splitlines() if o.strip()]
                options_json = json.dumps(options_list) if options_list else None

                field = FormField(
                    template_id=tmpl.id,
                    label=label,
                    field_name=field_name,
                    field_type=field_type,
                    placeholder=placeholder or None,
                    is_required=is_required,
                    options=options_json,
                    order=order,
                )
                db.session.add(field)
                db.session.commit()
                flash(f'Field "{label}" added.', 'success')

        elif action == 'delete_field':
            field_id = request.form.get('field_id', type=int)
            field = db.session.get(FormField, field_id)
            if field and field.template_id == tmpl.id:
                db.session.delete(field)
                db.session.commit()
                flash('Field deleted.', 'success')

        elif action == 'toggle_field':
            field_id = request.form.get('field_id', type=int)
            field = db.session.get(FormField, field_id)
            if field and field.template_id == tmpl.id:
                field.is_active = not field.is_active
                db.session.commit()
                flash('Field updated.', 'success')

        return redirect(url_for('admin.form_template_detail', template_id=tmpl.id))

    fields = tmpl.fields.all()
    return render_template('admin/form_template_detail.html',
                           tmpl=tmpl, fields=fields,
                           departments=departments, problems=problems,
                           field_types=FormField.FIELD_TYPES)


# ---------------------------------------------------------------------------
# Knowledge Base Management (Admin)
# ---------------------------------------------------------------------------

@bp.route('/kb')
@login_required
@admin_required
def kb_list():
    articles = KBArticle.query.order_by(KBArticle.updated_at.desc()).all()
    categories = KBCategory.query.order_by(KBCategory.order, KBCategory.name).all()
    return render_template('admin/kb_list.html', articles=articles, categories=categories)


@bp.route('/kb/categories/create', methods=['POST'])
@login_required
@admin_required
def kb_create_category():
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    order = request.form.get('order', 0, type=int)
    if not name:
        flash('Category name is required.', 'error')
    else:
        slug = KBCategory.make_slug(name)
        # ensure unique slug
        base, i = slug, 1
        while KBCategory.query.filter_by(slug=slug).first():
            slug = f'{base}-{i}'; i += 1
        cat = KBCategory(name=name, slug=slug,
                         description=description or None, order=order)
        db.session.add(cat)
        db.session.commit()
        flash(f'Category "{name}" created.', 'success')
    return redirect(url_for('admin.kb_list'))


@bp.route('/kb/categories/<int:cat_id>/delete', methods=['POST'])
@login_required
@admin_required
def kb_delete_category(cat_id):
    cat = db.session.get(KBCategory, cat_id)
    if cat:
        db.session.delete(cat)
        db.session.commit()
        flash('Category deleted.', 'success')
    return redirect(url_for('admin.kb_list'))


@bp.route('/kb/articles/create', methods=['GET', 'POST'])
@login_required
@admin_required
def kb_create():
    categories = KBCategory.query.filter_by(is_active=True).order_by(KBCategory.name).all()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        category_id = request.form.get('category_id', type=int) or None
        tags = request.form.get('tags', '').strip()
        is_published = request.form.get('is_published') == 'on'

        if not title or not content:
            flash('Title and content are required.', 'error')
        else:
            slug = KBArticle.make_slug(title)
            base, i = slug, 1
            while KBArticle.query.filter_by(slug=slug).first():
                slug = f'{base}-{i}'; i += 1
            art = KBArticle(
                title=title, slug=slug, content=content,
                category_id=category_id, author_id=current_user.id,
                tags=tags or None, is_published=is_published,
            )
            db.session.add(art)
            db.session.commit()
            flash(f'Article "{title}" {"published" if is_published else "saved as draft"}.', 'success')
            return redirect(url_for('admin.kb_list'))
    return render_template('admin/kb_form.html', article=None, categories=categories)


@bp.route('/kb/articles/<int:article_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def kb_edit(article_id):
    art = db.session.get(KBArticle, article_id)
    if not art:
        flash('Article not found.', 'error')
        return redirect(url_for('admin.kb_list'))

    categories = KBCategory.query.filter_by(is_active=True).order_by(KBCategory.name).all()
    if request.method == 'POST':
        art.title = request.form.get('title', art.title).strip()
        art.content = request.form.get('content', art.content).strip()
        art.category_id = request.form.get('category_id', type=int) or None
        art.tags = request.form.get('tags', '').strip() or None
        art.is_published = request.form.get('is_published') == 'on'
        db.session.commit()
        flash('Article updated.', 'success')
        return redirect(url_for('admin.kb_list'))
    return render_template('admin/kb_form.html', article=art, categories=categories)


@bp.route('/kb/articles/<int:article_id>/delete', methods=['POST'])
@login_required
@admin_required
def kb_delete(article_id):
    art = db.session.get(KBArticle, article_id)
    if art:
        db.session.delete(art)
        db.session.commit()
        flash('Article deleted.', 'success')
    return redirect(url_for('admin.kb_list'))


# ---------------------------------------------------------------------------
# API Token Management (Admin UI)
# ---------------------------------------------------------------------------

@bp.route('/api-tokens')
@login_required
@admin_required
def api_tokens():
    from app.models.api_token import APIToken
    tokens = APIToken.query.filter_by(user_id=current_user.id).order_by(
        APIToken.created_at.desc()
    ).all()
    new_token = None
    # Pull one-time token from session if just generated
    from flask import session as flask_session
    if 'new_api_token' in flask_session:
        new_token = flask_session.pop('new_api_token')
    return render_template('admin/api_tokens.html', tokens=tokens, new_token=new_token)


@bp.route('/api-tokens/create', methods=['POST'])
@login_required
@admin_required
def api_token_create():
    from app.models.api_token import APIToken
    from flask import session as flask_session
    name = request.form.get('token_name', '').strip() or 'API Token'
    plain, token_obj = APIToken.generate()
    token_obj.user_id = current_user.id
    token_obj.name = name
    db.session.add(token_obj)
    db.session.commit()
    flask_session['new_api_token'] = plain
    flash(f'Token "{name}" generated. Copy it now!', 'success')
    return redirect(url_for('admin.api_tokens'))


@bp.route('/api-tokens/<int:token_id>/revoke', methods=['POST'])
@login_required
@admin_required
def api_token_revoke(token_id):
    from app.models.api_token import APIToken
    token = APIToken.query.filter_by(id=token_id, user_id=current_user.id).first()
    if token:
        token.is_active = False
        db.session.commit()
        flash('Token revoked.', 'success')
    return redirect(url_for('admin.api_tokens'))


# ── Assignment Rules ──────────────────────────────────────────────────────────

def _agents_query():
    """Return active Agent + Admin users ordered by first name."""
    return (User.query
            .filter_by(is_active=True)
            .join(Role)
            .filter(Role.name.in_(['Agent', 'Admin']))
            .order_by(User.first_name, User.last_name)
            .all())


def _lookup_data():
    """Return all active lookup entities as lists (for the condition builder)."""
    return dict(
        departments  = Department.query.filter_by(is_active=True).order_by(Department.name).all(),
        problems     = Problem.query.filter_by(is_active=True).order_by(Problem.name).all(),
        sub_problems = SubProblem.query.filter_by(is_active=True).order_by(SubProblem.name).all(),
        categories   = Category.query.filter_by(is_active=True).order_by(Category.name).all(),
        sub_categories = SubCategory.query.filter_by(is_active=True).order_by(SubCategory.name).all(),
    )


def _save_rule_conditions(rule, conditions_json_str):
    """Parse the submitted JSON and persist condition groups + conditions."""
    try:
        groups_data = json.loads(conditions_json_str)
    except (ValueError, TypeError):
        groups_data = []

    for g_order, group_data in enumerate(groups_data):
        group = AssignmentRuleGroup(rule_id=rule.id, group_order=g_order)
        db.session.add(group)
        db.session.flush()

        for c_order, cond_data in enumerate(group_data.get('conditions', [])):
            field    = (cond_data.get('field') or '').strip()
            operator = (cond_data.get('operator') or 'is').strip()

            if not field:
                continue

            if field == 'priority':
                value_id  = None
                value_str = (cond_data.get('value_str') or '').strip() or None
            else:
                value_str = None
                raw_id    = cond_data.get('value_id')
                try:
                    value_id = int(raw_id) if raw_id not in (None, '', 'null') else None
                except (ValueError, TypeError):
                    value_id = None

            cond = AssignmentRuleCondition(
                group_id        = group.id,
                field           = field,
                operator        = operator,
                value_id        = value_id,
                value_str       = value_str,
                condition_order = c_order,
            )
            db.session.add(cond)


@bp.route('/assignment-rules')
@login_required
@admin_required
def assignment_rules():
    rules = (AssignmentRule.query
             .order_by(AssignmentRule.priority.asc(), AssignmentRule.id.asc())
             .all())
    return render_template('admin/assignment_rules.html', rules=rules)


@bp.route('/assignment-rules/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_assignment_rule():
    agents = _agents_query()
    lookups = _lookup_data()

    if request.method == 'POST':
        name           = request.form.get('name', '').strip()
        description    = request.form.get('description', '').strip() or None
        assigned_to_id = int(request.form.get('assigned_to_id') or 0)
        priority       = int(request.form.get('priority') or 0)
        is_active      = request.form.get('is_active') == '1'
        stop_on_match  = request.form.get('stop_on_match') == '1'
        conditions_json = request.form.get('conditions_json', '[]')

        if not name:
            flash('Rule name is required.', 'error')
        elif not assigned_to_id:
            flash('Please select an agent to assign to.', 'error')
        else:
            rule = AssignmentRule(
                name           = name,
                description    = description,
                priority       = priority,
                assigned_to_id = assigned_to_id,
                is_active      = is_active,
                stop_on_match  = stop_on_match,
            )
            db.session.add(rule)
            db.session.flush()
            _save_rule_conditions(rule, conditions_json)
            db.session.commit()
            flash(f'Assignment rule "{rule.name}" created.', 'success')
            return redirect(url_for('admin.assignment_rules'))

    return render_template('admin/create_assignment_rule.html',
                           agents=agents, **lookups)


@bp.route('/assignment-rules/<int:rule_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_assignment_rule(rule_id):
    rule = db.session.get(AssignmentRule, rule_id)
    if not rule:
        flash('Assignment rule not found.', 'error')
        return redirect(url_for('admin.assignment_rules'))

    agents  = _agents_query()
    lookups = _lookup_data()

    # Serialise existing groups → JSON for the template JS
    existing_groups = []
    for group in rule.condition_groups.order_by(None).all():
        conds = []
        for cond in group.conditions.order_by(None).all():
            conds.append({
                'field':     cond.field,
                'operator':  cond.operator,
                'value_id':  cond.value_id,
                'value_str': cond.value_str,
            })
        existing_groups.append({'conditions': conds})

    if request.method == 'POST':
        rule.name           = request.form.get('name', '').strip()
        rule.description    = request.form.get('description', '').strip() or None
        rule.assigned_to_id = int(request.form.get('assigned_to_id') or 0)
        rule.priority       = int(request.form.get('priority') or 0)
        rule.is_active      = request.form.get('is_active') == '1'
        rule.stop_on_match  = request.form.get('stop_on_match') == '1'
        conditions_json     = request.form.get('conditions_json', '[]')

        if not rule.name:
            flash('Rule name is required.', 'error')
        elif not rule.assigned_to_id:
            flash('Please select an agent.', 'error')
        else:
            # Drop old groups (cascade deletes conditions)
            for grp in list(rule.condition_groups.all()):
                db.session.delete(grp)
            db.session.flush()

            _save_rule_conditions(rule, conditions_json)
            rule.updated_at = datetime.utcnow()
            db.session.commit()
            flash(f'Rule "{rule.name}" updated.', 'success')
            return redirect(url_for('admin.assignment_rules'))

    return render_template('admin/edit_assignment_rule.html',
                           rule=rule, agents=agents,
                           existing_groups=json.dumps(existing_groups),
                           **lookups)


@bp.route('/assignment-rules/<int:rule_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_assignment_rule(rule_id):
    rule = db.session.get(AssignmentRule, rule_id)
    if rule:
        name = rule.name
        db.session.delete(rule)
        db.session.commit()
        flash(f'Rule "{name}" deleted.', 'success')
    return redirect(url_for('admin.assignment_rules'))


@bp.route('/assignment-rules/<int:rule_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_assignment_rule(rule_id):
    rule = db.session.get(AssignmentRule, rule_id)
    if rule:
        rule.is_active = not rule.is_active
        db.session.commit()
        state = 'enabled' if rule.is_active else 'disabled'
        flash(f'Rule "{rule.name}" {state}.', 'success')
    return redirect(url_for('admin.assignment_rules'))


# ── Priority Rules ────────────────────────────────────────────────────────────

def _save_priority_rule_conditions(rule, conditions_json_str):
    """Parse submitted JSON and persist PriorityRuleGroup + PriorityRuleCondition records."""
    try:
        groups_data = json.loads(conditions_json_str)
    except (ValueError, TypeError):
        groups_data = []

    for g_order, group_data in enumerate(groups_data):
        group = PriorityRuleGroup(rule_id=rule.id, group_order=g_order)
        db.session.add(group)
        db.session.flush()

        for c_order, cond_data in enumerate(group_data.get('conditions', [])):
            field    = (cond_data.get('field') or '').strip()
            operator = (cond_data.get('operator') or 'is').strip()

            if not field:
                continue

            if field == 'priority':
                value_id  = None
                value_str = (cond_data.get('value_str') or '').strip() or None
            else:
                value_str = None
                raw_id    = cond_data.get('value_id')
                try:
                    value_id = int(raw_id) if raw_id not in (None, '', 'null') else None
                except (ValueError, TypeError):
                    value_id = None

            cond = PriorityRuleCondition(
                group_id        = group.id,
                field           = field,
                operator        = operator,
                value_id        = value_id,
                value_str       = value_str,
                condition_order = c_order,
            )
            db.session.add(cond)


@bp.route('/priority-rules')
@login_required
@admin_required
def priority_rules():
    rules = (PriorityRule.query
             .order_by(PriorityRule.priority_order.asc(), PriorityRule.id.asc())
             .all())
    return render_template('admin/priority_rules.html', rules=rules)


@bp.route('/priority-rules/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_priority_rule():
    lookups = _lookup_data()

    if request.method == 'POST':
        name           = request.form.get('name', '').strip()
        description    = request.form.get('description', '').strip() or None
        set_priority   = request.form.get('set_priority', 'Medium')
        priority_order = int(request.form.get('priority_order') or 0)
        is_active      = request.form.get('is_active') == '1'
        stop_on_match  = request.form.get('stop_on_match') == '1'
        conditions_json = request.form.get('conditions_json', '[]')

        if not name:
            flash('Rule name is required.', 'error')
        elif set_priority not in PRIORITY_VALUES:
            flash('Invalid priority value.', 'error')
        else:
            rule = PriorityRule(
                name           = name,
                description    = description,
                priority_order = priority_order,
                set_priority   = set_priority,
                is_active      = is_active,
                stop_on_match  = stop_on_match,
            )
            db.session.add(rule)
            db.session.flush()
            _save_priority_rule_conditions(rule, conditions_json)
            db.session.commit()
            flash(f'Priority rule "{rule.name}" created.', 'success')
            return redirect(url_for('admin.priority_rules'))

    return render_template('admin/create_priority_rule.html',
                           priority_values=PRIORITY_VALUES, **lookups)


@bp.route('/priority-rules/<int:rule_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_priority_rule(rule_id):
    rule = db.session.get(PriorityRule, rule_id)
    if not rule:
        flash('Priority rule not found.', 'error')
        return redirect(url_for('admin.priority_rules'))

    lookups = _lookup_data()

    existing_groups = []
    for group in rule.condition_groups.order_by(None).all():
        conds = []
        for cond in group.conditions.order_by(None).all():
            conds.append({
                'field':     cond.field,
                'operator':  cond.operator,
                'value_id':  cond.value_id,
                'value_str': cond.value_str,
            })
        existing_groups.append({'conditions': conds})

    if request.method == 'POST':
        rule.name           = request.form.get('name', '').strip()
        rule.description    = request.form.get('description', '').strip() or None
        rule.set_priority   = request.form.get('set_priority', 'Medium')
        rule.priority_order = int(request.form.get('priority_order') or 0)
        rule.is_active      = request.form.get('is_active') == '1'
        rule.stop_on_match  = request.form.get('stop_on_match') == '1'
        conditions_json     = request.form.get('conditions_json', '[]')

        if not rule.name:
            flash('Rule name is required.', 'error')
        elif rule.set_priority not in PRIORITY_VALUES:
            flash('Invalid priority value.', 'error')
        else:
            for grp in list(rule.condition_groups.all()):
                db.session.delete(grp)
            db.session.flush()

            _save_priority_rule_conditions(rule, conditions_json)
            rule.updated_at = datetime.utcnow()
            db.session.commit()
            flash(f'Priority rule "{rule.name}" updated.', 'success')
            return redirect(url_for('admin.priority_rules'))

    return render_template('admin/edit_priority_rule.html',
                           rule=rule, priority_values=PRIORITY_VALUES,
                           existing_groups=json.dumps(existing_groups),
                           **lookups)


@bp.route('/priority-rules/<int:rule_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_priority_rule(rule_id):
    rule = db.session.get(PriorityRule, rule_id)
    if rule:
        name = rule.name
        db.session.delete(rule)
        db.session.commit()
        flash(f'Priority rule "{name}" deleted.', 'success')
    return redirect(url_for('admin.priority_rules'))


@bp.route('/priority-rules/<int:rule_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_priority_rule(rule_id):
    rule = db.session.get(PriorityRule, rule_id)
    if rule:
        rule.is_active = not rule.is_active
        db.session.commit()
        state = 'enabled' if rule.is_active else 'disabled'
        flash(f'Priority rule "{rule.name}" {state}.', 'success')
    return redirect(url_for('admin.priority_rules'))
