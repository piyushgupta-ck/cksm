from datetime import time as t
from app import create_app, db
from app.models.user import User, Role, Permission
from app.models.department import Department, Problem, SubProblem, Category, SubCategory
from app.models.sla import SLAPolicy, BusinessHoursConfig
from app.models.escalation import EscalationRule

app = create_app()


def seed():
    with app.app_context():
        db.create_all()

        if Role.query.first():
            print('Database already seeded. Skipping.')
            return

        # ── Permissions ────────────────────────────────────────────────────
        perms = {}
        perm_names = [
            'manage_users', 'manage_departments', 'manage_tickets',
            'view_all_tickets', 'assign_tickets', 'create_tickets',
            'view_own_tickets', 'reply_tickets', 'change_ticket_status',
            'view_reports', 'manage_sla', 'manage_workflows',
        ]
        for name in perm_names:
            p = Permission(name=name, description=name.replace('_', ' ').title())
            db.session.add(p)
            perms[name] = p

        db.session.flush()

        # ── Roles ──────────────────────────────────────────────────────────
        admin_role = Role(name='Admin', description='Full system administrator')
        admin_role.permissions = list(perms.values())
        db.session.add(admin_role)

        agent_role = Role(name='Agent', description='Support agent / technician')
        agent_role.permissions = [
            perms['manage_tickets'], perms['view_all_tickets'],
            perms['assign_tickets'], perms['create_tickets'],
            perms['reply_tickets'], perms['change_ticket_status'],
        ]
        db.session.add(agent_role)

        user_role = Role(name='End User', description='Regular end user')
        user_role.permissions = [
            perms['create_tickets'], perms['view_own_tickets'], perms['reply_tickets'],
        ]
        db.session.add(user_role)

        db.session.flush()

        # ── Departments ────────────────────────────────────────────────────
        it_dept = Department(name='IT', description='Information Technology')
        hr_dept = Department(name='HR', description='Human Resources')
        finance_dept = Department(name='Finance', description='Finance & Accounting')
        admin_dept = Department(name='Administration', description='General Administration')
        db.session.add_all([it_dept, hr_dept, finance_dept, admin_dept])
        db.session.flush()

        # ── Problems (IT) ──────────────────────────────────────────────────
        hw_problem = Problem(name='Hardware', department_id=it_dept.id)
        sw_problem = Problem(name='Software', department_id=it_dept.id)
        nw_problem = Problem(name='Network', department_id=it_dept.id)
        db.session.add_all([hw_problem, sw_problem, nw_problem])
        db.session.flush()

        # ── Sub-problems ───────────────────────────────────────────────────
        laptop_sub = SubProblem(name='Laptop', problem_id=hw_problem.id)
        printer_sub = SubProblem(name='Printer', problem_id=hw_problem.id)
        email_sub = SubProblem(name='Email', problem_id=sw_problem.id)
        erp_sub = SubProblem(name='ERP', problem_id=sw_problem.id)
        db.session.add_all([laptop_sub, printer_sub, email_sub, erp_sub])
        db.session.flush()

        # ── Categories ─────────────────────────────────────────────────────
        repair_cat = Category(name='Repair', sub_problem_id=laptop_sub.id)
        replace_cat = Category(name='Replacement', sub_problem_id=laptop_sub.id)
        config_cat = Category(name='Configuration', sub_problem_id=email_sub.id)
        access_cat = Category(name='Access Issue', sub_problem_id=email_sub.id)
        db.session.add_all([repair_cat, replace_cat, config_cat, access_cat])
        db.session.flush()

        # ── Sub-categories ─────────────────────────────────────────────────
        db.session.add_all([
            SubCategory(name='Screen Damage', category_id=repair_cat.id),
            SubCategory(name='Keyboard Issue', category_id=repair_cat.id),
            SubCategory(name='Battery Replacement', category_id=replace_cat.id),
            SubCategory(name='Password Reset', category_id=access_cat.id),
        ])

        # ── Users ──────────────────────────────────────────────────────────
        admin_user = User(
            email='admin@citykart.com', username='admin',
            first_name='System', last_name='Administrator',
            role_id=admin_role.id, department_id=it_dept.id,
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)

        agent_user = User(
            email='agent@citykart.com', username='agent1',
            first_name='Rahul', last_name='Sharma',
            role_id=agent_role.id, department_id=it_dept.id,
        )
        agent_user.set_password('agent123')
        db.session.add(agent_user)

        end_user = User(
            email='user@citykart.com', username='user1',
            first_name='Priya', last_name='Verma',
            role_id=user_role.id,
        )
        end_user.set_password('user123')
        db.session.add(end_user)

        db.session.flush()

        # ── Business Hours (Mon–Fri 09:00–18:00, Sat–Sun off) ──────────────
        for day in range(7):
            is_working = day < 5   # Mon=0 … Fri=4; Sat=5, Sun=6 → off
            db.session.add(BusinessHoursConfig(
                day_of_week=day,
                start_time=t(9, 0),
                end_time=t(18, 0),
                is_working_day=is_working,
            ))

        # ── SLA Policies (global defaults by priority) ─────────────────────
        sla_configs = [
            ('Critical – Global', None, 'Critical', 1.0,  4.0),
            ('High – Global',     None, 'High',     2.0,  8.0),
            ('Medium – Global',   None, 'Medium',   4.0,  24.0),
            ('Low – Global',      None, 'Low',      8.0,  48.0),
        ]
        for name, dept_id, priority, fr_h, res_h in sla_configs:
            db.session.add(SLAPolicy(
                name=name, department_id=dept_id, priority=priority,
                first_response_hours=fr_h, resolution_hours=res_h,
                use_business_hours=True,
            ))

        db.session.flush()

        # ── Default Escalation Rule ────────────────────────────────────────
        db.session.add(EscalationRule(
            name='Critical Resolution Warning (L1)',
            department_id=None,
            priority='Critical',
            level=1,
            sla_type='resolution',
            breach_threshold_percent=80,
            notify_user_id=admin_user.id,
        ))

        db.session.commit()
        print('Database seeded successfully!')
        print()
        print('Login credentials:')
        print('  Admin:  admin@citykart.com / admin123')
        print('  Agent:  agent@citykart.com / agent123')
        print('  User:   user@citykart.com  / user123')


if __name__ == '__main__':
    seed()
