"""
CKSM Demo Seed
==============
Populates a rich dataset for showcasing / testing all features:

  • 5 departments with full Problem → SubProblem → Category → SubCategory trees
  • 5 custom form templates (per-dept, with multiple field types)
  • 7 end users  +  6 agents  (admin already exists from seed.py)
  • 30 tickets spanning all 7 statuses, all priorities, all departments
  • Ticket messages, activity logs, status history & SLA records
  • KB categories + sample articles

Run:
    python seed_demo.py

Safe to re-run — existing rows are skipped.
"""
import json
from datetime import datetime, timezone, timedelta
from datetime import time as t

from app import create_app, db

app = create_app()


# --- helpers ----------------------------------------------------------------

def get_or_create(model, defaults=None, **kw):
    obj = model.query.filter_by(**kw).first()
    if obj:
        return obj, False
    params = {**kw, **(defaults or {})}
    obj = model(**params)
    db.session.add(obj)
    db.session.flush()
    return obj, True


def utc(days_ago=0, hours_ago=0):
    return datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours_ago)


# --- main --------------------------------------------------------------------

def seed_demo():
    with app.app_context():
        from app.models.user import User, Role
        from app.models.department import Department, Problem, SubProblem, Category, SubCategory
        from app.models.forms import FormTemplate, FormField, TicketFieldValue
        from app.models.ticket import Ticket, TicketMessage, TicketActivityLog, TicketStatusHistory
        from app.models.sla import SLAPolicy, TicketSLA
        from app.models.kb import KBCategory, KBArticle

        admin_role  = Role.query.filter_by(name='Admin').first()
        agent_role  = Role.query.filter_by(name='Agent').first()
        user_role   = Role.query.filter_by(name='End User').first()
        admin_user  = User.query.filter_by(username='admin').first()

        if not admin_role:
            print('ERROR: Base seed not run. Run `python seed.py` first.')
            return

        print('\n-- Departments ----------------------------------------------')

        # -- Departments -------------------------------------------------------
        it_dept,  _  = get_or_create(Department, name='IT',
                                     defaults={'description': 'Information Technology', 'is_active': True})
        hr_dept,  _  = get_or_create(Department, name='HR',
                                     defaults={'description': 'Human Resources', 'is_active': True})
        fin_dept, _  = get_or_create(Department, name='Finance',
                                     defaults={'description': 'Finance & Accounting', 'is_active': True})
        ops_dept, c  = get_or_create(Department, name='Operations',
                                     defaults={'description': 'Operations & Logistics', 'is_active': True})
        fac_dept, c  = get_or_create(Department, name='Facilities',
                                     defaults={'description': 'Facilities & Admin', 'is_active': True})
        db.session.flush()
        print(f'  IT={it_dept.id}  HR={hr_dept.id}  Finance={fin_dept.id}  Operations={ops_dept.id}  Facilities={fac_dept.id}')

        print('\n-- Problem Hierarchy -----------------------------------------')

        # --------------------------------------------------------------------
        # IT
        # --------------------------------------------------------------------
        hw_p, _   = get_or_create(Problem, name='Hardware',  department_id=it_dept.id,  defaults={'is_active': True})
        sw_p, _   = get_or_create(Problem, name='Software',  department_id=it_dept.id,  defaults={'is_active': True})
        nw_p, _   = get_or_create(Problem, name='Network',   department_id=it_dept.id,  defaults={'is_active': True})
        sec_p, _  = get_or_create(Problem, name='Security',  department_id=it_dept.id,  defaults={'is_active': True})
        db.session.flush()

        laptop_sp,  _ = get_or_create(SubProblem, name='Laptop',    problem_id=hw_p.id, defaults={'is_active': True})
        desktop_sp, _ = get_or_create(SubProblem, name='Desktop',   problem_id=hw_p.id, defaults={'is_active': True})
        printer_sp, _ = get_or_create(SubProblem, name='Printer',   problem_id=hw_p.id, defaults={'is_active': True})
        email_sp,   _ = get_or_create(SubProblem, name='Email',     problem_id=sw_p.id, defaults={'is_active': True})
        erp_sp,     _ = get_or_create(SubProblem, name='ERP',       problem_id=sw_p.id, defaults={'is_active': True})
        os_sp,      _ = get_or_create(SubProblem, name='OS',        problem_id=sw_p.id, defaults={'is_active': True})
        vpn_sp,     _ = get_or_create(SubProblem, name='VPN',       problem_id=nw_p.id, defaults={'is_active': True})
        wifi_sp,    _ = get_or_create(SubProblem, name='WiFi',      problem_id=nw_p.id, defaults={'is_active': True})
        inet_sp,    _ = get_or_create(SubProblem, name='Internet',  problem_id=nw_p.id, defaults={'is_active': True})
        acc_sp,     _ = get_or_create(SubProblem, name='Account Security', problem_id=sec_p.id, defaults={'is_active': True})
        db.session.flush()

        # IT categories
        for sp, cats in [
            (laptop_sp,  ['Screen Damage', 'Battery Replacement', 'Keyboard Issue', 'Replacement']),
            (desktop_sp, ['Hardware Failure', 'Slow Performance', 'Replacement']),
            (printer_sp, ['Paper Jam', 'Driver Issue', 'Connectivity', 'Replacement']),
            (email_sp,   ['Access Issue', 'Configuration', 'Migration', 'Spam']),
            (erp_sp,     ['Login Issue', 'Slow Performance', 'Data Error', 'Report Issue']),
            (os_sp,      ['OS Crash', 'Update Failure', 'Virus/Malware', 'Activation']),
            (vpn_sp,     ['Cannot Connect', 'Slow VPN', 'Access Denied']),
            (wifi_sp,    ['Cannot Connect', 'Slow WiFi', 'Authentication']),
            (inet_sp,    ['No Internet', 'Slow Internet', 'Blocked Site']),
            (acc_sp,     ['Password Reset', 'Account Locked', 'Suspicious Activity']),
        ]:
            for cat_name in cats:
                cat, _ = get_or_create(Category, name=cat_name, sub_problem_id=sp.id,
                                       defaults={'is_active': True})
                db.session.flush()
                # Add 2 sub-categories per category
                for sc in [f'{cat_name} — L1', f'{cat_name} — L2']:
                    get_or_create(SubCategory, name=sc, category_id=cat.id, defaults={'is_active': True})
                db.session.flush()

        # --------------------------------------------------------------------
        # HR
        # --------------------------------------------------------------------
        payroll_p,  _ = get_or_create(Problem, name='Payroll',          department_id=hr_dept.id, defaults={'is_active': True})
        leave_p,    _ = get_or_create(Problem, name='Leave Management', department_id=hr_dept.id, defaults={'is_active': True})
        recruit_p,  _ = get_or_create(Problem, name='Recruitment',      department_id=hr_dept.id, defaults={'is_active': True})
        benefit_p,  _ = get_or_create(Problem, name='Benefits',         department_id=hr_dept.id, defaults={'is_active': True})
        db.session.flush()

        pay_salary_sp, _ = get_or_create(SubProblem, name='Salary Issue',  problem_id=payroll_p.id, defaults={'is_active': True})
        pay_bonus_sp,  _ = get_or_create(SubProblem, name='Bonus Issue',   problem_id=payroll_p.id, defaults={'is_active': True})
        annual_sp,     _ = get_or_create(SubProblem, name='Annual Leave',  problem_id=leave_p.id,   defaults={'is_active': True})
        sick_sp,       _ = get_or_create(SubProblem, name='Sick Leave',    problem_id=leave_p.id,   defaults={'is_active': True})
        job_sp,        _ = get_or_create(SubProblem, name='Job Posting',   problem_id=recruit_p.id, defaults={'is_active': True})
        onboard_sp,    _ = get_or_create(SubProblem, name='Onboarding',    problem_id=recruit_p.id, defaults={'is_active': True})
        db.session.flush()

        for sp, cats in [
            (pay_salary_sp, ['Payment Delay', 'Wrong Amount', 'Deduction Query']),
            (pay_bonus_sp,  ['Not Received', 'Wrong Calculation']),
            (annual_sp,     ['New Application', 'Cancellation', 'Balance Query']),
            (sick_sp,       ['New Application', 'Extension Request']),
            (job_sp,        ['Status Update', 'Interview Schedule']),
            (onboard_sp,    ['Document Submission', 'System Access']),
        ]:
            for cat_name in cats:
                cat, _ = get_or_create(Category, name=cat_name, sub_problem_id=sp.id,
                                       defaults={'is_active': True})
                db.session.flush()

        # --------------------------------------------------------------------
        # Finance
        # --------------------------------------------------------------------
        reimb_p,  _ = get_or_create(Problem, name='Reimbursement', department_id=fin_dept.id, defaults={'is_active': True})
        invoice_p,_ = get_or_create(Problem, name='Invoice',       department_id=fin_dept.id, defaults={'is_active': True})
        budget_p, _ = get_or_create(Problem, name='Budget',        department_id=fin_dept.id, defaults={'is_active': True})
        db.session.flush()

        travel_sp, _  = get_or_create(SubProblem, name='Travel Expense',   problem_id=reimb_p.id,   defaults={'is_active': True})
        medical_sp, _ = get_or_create(SubProblem, name='Medical Expense',  problem_id=reimb_p.id,   defaults={'is_active': True})
        vendor_sp, _  = get_or_create(SubProblem, name='Vendor Invoice',   problem_id=invoice_p.id, defaults={'is_active': True})
        cust_inv_sp, _= get_or_create(SubProblem, name='Customer Invoice', problem_id=invoice_p.id, defaults={'is_active': True})
        db.session.flush()

        for sp, cats in [
            (travel_sp,   ['Pending Reimbursement', 'Rejected Claim', 'Wrong Amount']),
            (medical_sp,  ['Claim Submission', 'Status Check', 'Rejected']),
            (vendor_sp,   ['Approval Pending', 'Payment Delay', 'Duplicate Invoice']),
            (cust_inv_sp, ['Dispute', 'Credit Note Request', 'Correction']),
        ]:
            for cat_name in cats:
                get_or_create(Category, name=cat_name, sub_problem_id=sp.id, defaults={'is_active': True})
                db.session.flush()

        # --------------------------------------------------------------------
        # Operations
        # --------------------------------------------------------------------
        logistics_p, _ = get_or_create(Problem, name='Logistics',    department_id=ops_dept.id, defaults={'is_active': True})
        procure_p,   _ = get_or_create(Problem, name='Procurement',  department_id=ops_dept.id, defaults={'is_active': True})
        db.session.flush()

        delivery_sp, _ = get_or_create(SubProblem, name='Delivery',        problem_id=logistics_p.id, defaults={'is_active': True})
        returns_sp,  _ = get_or_create(SubProblem, name='Returns',         problem_id=logistics_p.id, defaults={'is_active': True})
        po_sp,       _ = get_or_create(SubProblem, name='Purchase Order',  problem_id=procure_p.id,   defaults={'is_active': True})
        vendor2_sp,  _ = get_or_create(SubProblem, name='Vendor Issue',    problem_id=procure_p.id,   defaults={'is_active': True})
        db.session.flush()

        for sp, cats in [
            (delivery_sp, ['Delayed Delivery', 'Damaged Shipment', 'Wrong Item']),
            (returns_sp,  ['Return Processing', 'Refund Status']),
            (po_sp,       ['Approval Pending', 'PO Status', 'Amendment']),
            (vendor2_sp,  ['Vendor Registration', 'Quality Issue', 'Contract']),
        ]:
            for cat_name in cats:
                get_or_create(Category, name=cat_name, sub_problem_id=sp.id, defaults={'is_active': True})
                db.session.flush()

        # --------------------------------------------------------------------
        # Facilities
        # --------------------------------------------------------------------
        maint_p,  _ = get_or_create(Problem, name='Maintenance', department_id=fac_dept.id, defaults={'is_active': True})
        security_p, _=get_or_create(Problem, name='Security',   department_id=fac_dept.id, defaults={'is_active': True})
        space_p,  _ = get_or_create(Problem, name='Workspace',  department_id=fac_dept.id, defaults={'is_active': True})
        db.session.flush()

        elec_sp,  _ = get_or_create(SubProblem, name='Electrical', problem_id=maint_p.id,   defaults={'is_active': True})
        plumb_sp, _ = get_or_create(SubProblem, name='Plumbing',   problem_id=maint_p.id,   defaults={'is_active': True})
        card_sp,  _ = get_or_create(SubProblem, name='Access Card',problem_id=security_p.id, defaults={'is_active': True})
        cctv_sp,  _ = get_or_create(SubProblem, name='CCTV',       problem_id=security_p.id, defaults={'is_active': True})
        seat_sp,  _ = get_or_create(SubProblem, name='Seating',    problem_id=space_p.id,   defaults={'is_active': True})
        db.session.flush()

        for sp, cats in [
            (elec_sp,  ['Power Outage', 'AC Not Working', 'Light Repair', 'Generator']),
            (plumb_sp, ['Water Leak', 'Blockage', 'Tap Issue']),
            (card_sp,  ['New Card Request', 'Lost Card', 'Deactivate Card', 'Access Level Change']),
            (cctv_sp,  ['Camera Not Working', 'Recording Issue', 'New Camera Request']),
            (seat_sp,  ['New Seat Allocation', 'Desk Issue', 'Locker Request']),
        ]:
            for cat_name in cats:
                get_or_create(Category, name=cat_name, sub_problem_id=sp.id, defaults={'is_active': True})
                db.session.flush()

        db.session.commit()
        print('  Problem hierarchy committed.')

        # ====================================================================
        # CUSTOM FORM TEMPLATES
        # ====================================================================
        print('\n-- Custom Form Templates -------------------------------------')

        def make_template(name, dept, prob, fields_spec):
            """fields_spec: list of (label, field_name, ftype, options, placeholder, required, order)"""
            tmpl = FormTemplate.query.filter_by(name=name).first()
            if tmpl:
                print(f'  SKIP  {name}')
                return tmpl
            tmpl = FormTemplate(name=name, department_id=dept.id if dept else None,
                                problem_id=prob.id if prob else None, is_active=True)
            db.session.add(tmpl)
            db.session.flush()
            for label, field_name, ftype, opts, placeholder, required, order in fields_spec:
                f = FormField(
                    template_id=tmpl.id, label=label, field_name=field_name,
                    field_type=ftype,
                    options=json.dumps(opts) if opts else None,
                    placeholder=placeholder, is_required=required, order=order, is_active=True,
                )
                db.session.add(f)
            db.session.flush()
            print(f'  CREATE {name}')
            return tmpl

        # IT — Hardware template
        make_template('IT Hardware Details', it_dept, hw_p, [
            ('Asset Tag',      'asset_tag',      'text',     None, 'e.g. AST-00123',   True,  1),
            ('Serial Number',  'serial_no',      'text',     None, 'e.g. SN-XXXX',     False, 2),
            ('Device Location','device_location','dropdown', ['Head Office', 'Branch - Mumbai', 'Branch - Delhi', 'WFH', 'Warehouse'], None, True, 3),
            ('Purchase Date',  'purchase_date',  'date',     None, '',                 False, 4),
            ('Warranty Status','warranty',       'dropdown', ['Under Warranty', 'Out of Warranty', 'Extended Warranty', 'Unknown'], None, False, 5),
        ])

        # IT — Software template
        make_template('IT Software Details', it_dept, sw_p, [
            ('Software Name',  'software_name',  'text',     None, 'e.g. Microsoft Office', True, 1),
            ('Version',        'version',        'text',     None, 'e.g. 16.0',         False, 2),
            ('Error Code',     'error_code',     'text',     None, 'e.g. 0x80070005',   False, 3),
            ('License Type',   'license_type',   'dropdown', ['Individual', 'Shared', 'Concurrent', 'OEM', 'Volume'], None, False, 4),
            ('Steps to Reproduce', 'steps',      'textarea', None, 'Describe steps …',  False, 5),
        ])

        # HR — Payroll template
        make_template('HR Payroll Details', hr_dept, payroll_p, [
            ('Employee ID',    'emp_id',          'text',     None, 'e.g. EMP-0042',    True,  1),
            ('Pay Period',     'pay_period',      'dropdown', ['January', 'February', 'March', 'April', 'May',
                                                               'June', 'July', 'August', 'September',
                                                               'October', 'November', 'December'], None, True, 2),
            ('Expected Amount','expected_amount', 'number',   None, '',                 True,  3),
            ('Received Amount','received_amount', 'number',   None, '',                 False, 4),
            ('Bank Account',   'bank_account',    'text',     None, 'Last 4 digits only', False, 5),
        ])

        # Finance — Reimbursement template
        make_template('Finance Reimbursement Details', fin_dept, reimb_p, [
            ('Invoice / Bill Number', 'invoice_no',   'text',   None, 'e.g. INV-2026-0045', True, 1),
            ('Expense Amount (₹)',    'amount',        'number', None, '',               True,  2),
            ('Date of Expense',       'expense_date',  'date',   None, '',               True,  3),
            ('Purpose',               'purpose',       'dropdown', ['Business Travel', 'Client Entertainment',
                                                                     'Office Supplies', 'Medical', 'Training', 'Other'],
                                                                     None, True, 4),
            ('Supporting Documents',  'docs_attached', 'checkbox', None, '', False, 5),
        ])

        # Facilities — Maintenance template
        make_template('Facilities Maintenance Details', fac_dept, maint_p, [
            ('Building / Floor',  'location',      'dropdown', ['Building A - GF', 'Building A - 1F',
                                                                  'Building A - 2F', 'Building B - GF',
                                                                  'Building B - 1F', 'Canteen', 'Parking'], None, True, 1),
            ('Room / Desk No.',   'room_no',       'text',    None, 'e.g. A-102',       False, 2),
            ('Urgency Level',     'urgency',       'dropdown', ['Normal', 'Urgent', 'Emergency'], None, True, 3),
            ('Affected Equipment','affected_equip','text',    None, 'e.g. AC unit #3',  False, 4),
            ('Best Time to Visit','visit_time',    'dropdown', ['Morning (9–12)', 'Afternoon (12–3)', 'Evening (3–6)', 'After hours'], None, False, 5),
        ])

        db.session.commit()
        print('  Custom form templates committed.')

        # ====================================================================
        # USERS
        # ====================================================================
        print('\n-- Users & Agents -------------------------------------------')

        def make_user(email, username, first, last, role, dept, password='Demo@1234'):
            u = User.query.filter_by(email=email).first()
            if u:
                print(f'  SKIP  {email}')
                return u
            u = User(email=email, username=username, first_name=first, last_name=last,
                     role_id=role.id, department_id=dept.id if dept else None, is_active=True)
            u.set_password(password)
            db.session.add(u)
            db.session.flush()
            print(f'  CREATE  {email}  ({role.name})')
            return u

        # Agents
        ag_rahul   = make_user('agent@citykart.com',   'agent1',    'Rahul',   'Sharma',   agent_role, it_dept,  'agent123')  # existing
        ag_pooja   = make_user('pooja@citykart.com',   'pooja.iyer','Pooja',   'Iyer',     agent_role, it_dept)
        ag_vishal  = make_user('vishal@citykart.com',  'vishal.nair','Vishal', 'Nair',     agent_role, hr_dept)
        ag_ananya  = make_user('ananya@citykart.com',  'ananya.r',  'Ananya',  'Reddy',    agent_role, fin_dept)
        ag_suresh  = make_user('suresh@citykart.com',  'suresh.k',  'Suresh',  'Kumar',    agent_role, ops_dept)
        ag_meena   = make_user('meena@citykart.com',   'meena.p',   'Meena',   'Pillai',   agent_role, fac_dept)

        # End Users
        eu_amit    = make_user('amit@citykart.com',    'amit.kumar','Amit',    'Kumar',    user_role, it_dept)
        eu_sneha   = make_user('sneha@citykart.com',   'sneha.p',   'Sneha',   'Patel',    user_role, hr_dept)
        eu_rajan   = make_user('rajan@citykart.com',   'rajan.v',   'Rajan',   'Verma',    user_role, fin_dept)
        eu_kavitha = make_user('kavitha@citykart.com', 'kavitha.n', 'Kavitha', 'Nair',     user_role, ops_dept)
        eu_mohammed= make_user('mohammed@citykart.com','mohammed.a','Mohammed','Ali',      user_role, fac_dept)
        eu_deepika = make_user('deepika@citykart.com', 'deepika.s', 'Deepika', 'Singh',    user_role, it_dept)
        eu_arjun   = make_user('arjun@citykart.com',   'arjun.g',   'Arjun',   'Gupta',    user_role, hr_dept)
        eu_user    = User.query.filter_by(username='user1').first()   # from base seed

        db.session.commit()
        print('  Users committed.')

        # ====================================================================
        # HELPER — create a ticket with full trimmings
        # ====================================================================

        def make_ticket(title, desc, dept, problem, sub_problem, category,
                        priority, status, creator, assignee,
                        created_days_ago=3,
                        messages=None,          # list of (user, content, is_internal, hours_after_create)
                        custom_fields=None,     # dict {field_label: value}
                        resolved_days_ago=None,
                        closed_days_ago=None):

            existing = Ticket.query.filter_by(title=title).first()
            if existing:
                print(f'  SKIP  {existing.ticket_id}  {title[:50]}')
                return existing

            created_at = utc(days_ago=created_days_ago)
            ticket_id  = Ticket.generate_ticket_id()

            ticket = Ticket(
                ticket_id=ticket_id,
                title=title,
                description=desc,
                department_id=dept.id,
                problem_id=problem.id if problem else None,
                sub_problem_id=sub_problem.id if sub_problem else None,
                category_id=category.id if category else None,
                priority=priority,
                status=status,
                created_by=creator.id,
                assigned_to=assignee.id if assignee else None,
                created_at=created_at,
                updated_at=created_at,
            )
            if resolved_days_ago is not None:
                ticket.resolved_at = utc(days_ago=resolved_days_ago)
            if closed_days_ago is not None:
                ticket.closed_at = utc(days_ago=closed_days_ago)

            db.session.add(ticket)
            db.session.flush()

            # Activity log — created
            db.session.add(TicketActivityLog(
                ticket_pk=ticket.id, user_id=creator.id,
                action='created',
                details=f'Ticket {ticket_id} created.',
                created_at=created_at,
            ))
            # Status history — created
            db.session.add(TicketStatusHistory(
                ticket_pk=ticket.id, user_id=creator.id,
                old_status=None, new_status='Open',
                remarks='Ticket created', changed_at=created_at,
            ))

            # Status transitions for non-Open tickets
            if status not in ('Open',):
                t_at = created_at + timedelta(hours=1)
                db.session.add(TicketStatusHistory(
                    ticket_pk=ticket.id, user_id=assignee.id if assignee else creator.id,
                    old_status='Open', new_status=status if status == 'InProgress' else 'InProgress',
                    remarks='Picked up', changed_at=t_at,
                ))
                db.session.add(TicketActivityLog(
                    ticket_pk=ticket.id, user_id=assignee.id if assignee else creator.id,
                    action='status_changed', details=f'Open → InProgress',
                    created_at=t_at,
                ))
                if status not in ('InProgress',):
                    t2_at = created_at + timedelta(hours=4)
                    db.session.add(TicketStatusHistory(
                        ticket_pk=ticket.id, user_id=assignee.id if assignee else creator.id,
                        old_status='InProgress', new_status=status,
                        remarks='', changed_at=t2_at,
                    ))
                    db.session.add(TicketActivityLog(
                        ticket_pk=ticket.id, user_id=assignee.id if assignee else creator.id,
                        action='status_changed', details=f'InProgress → {status}',
                        created_at=t2_at,
                    ))

            # Messages
            if messages:
                for msg_user, content, is_internal, hours_after in messages:
                    msg_at = created_at + timedelta(hours=hours_after)
                    msg = TicketMessage(
                        ticket_pk=ticket.id, user_id=msg_user.id,
                        content=content, is_internal=is_internal,
                        created_at=msg_at,
                    )
                    db.session.add(msg)

            # Custom fields — look up field by label
            if custom_fields:
                # find matching template
                template = (FormTemplate.query
                            .filter_by(department_id=dept.id,
                                       problem_id=problem.id if problem else None,
                                       is_active=True)
                            .first())
                if not template:
                    template = FormTemplate.query.filter_by(
                        department_id=dept.id, problem_id=None, is_active=True
                    ).first()
                if template:
                    for fld in template.get_active_fields():
                        if fld.label in custom_fields:
                            db.session.add(TicketFieldValue(
                                ticket_pk=ticket.id,
                                field_id=fld.id,
                                value=custom_fields[fld.label],
                            ))

            db.session.flush()

            # SLA
            try:
                from app.sla.engine import initialize_ticket_sla
                initialize_ticket_sla(ticket)
            except Exception:
                pass

            print(f'  CREATE  {ticket_id}  [{status:10}]  {title[:55]}')
            return ticket

        # ====================================================================
        # TICKETS
        # ====================================================================
        print('\n-- Tickets --------------------------------------------------')

        # Lookup some categories for convenience
        screen_cat   = Category.query.filter_by(name='Screen Damage').first()
        bat_cat      = Category.query.filter_by(name='Battery Replacement').first()
        access_cat   = Category.query.filter_by(name='Access Issue').first()
        login_cat    = Category.query.filter_by(name='Login Issue').first()
        no_inet_cat  = Category.query.filter_by(name='No Internet').first()
        vpn_conn_cat = Category.query.filter_by(name='Cannot Connect').first()
        pay_delay_cat= Category.query.filter_by(name='Payment Delay').first()
        wrong_amt_cat= Category.query.filter_by(name='Wrong Amount').first()
        salary_cat   = Category.query.filter_by(name='Payment Delay').first()
        pend_reimb_cat = Category.query.filter_by(name='Pending Reimbursement').first()
        power_cat    = Category.query.filter_by(name='Power Outage').first()
        ac_cat       = Category.query.filter_by(name='AC Not Working').first()
        card_new_cat = Category.query.filter_by(name='New Card Request').first()
        delay_del_cat= Category.query.filter_by(name='Delayed Delivery').first()
        po_cat       = Category.query.filter_by(name='Approval Pending').first()

        # -- OPEN tickets (5) -------------------------------------------------
        make_ticket(
            'Laptop screen flickering on Amit Kumar laptop',
            'The laptop screen flickers every few minutes making it hard to work. Happens on battery and AC power.',
            it_dept, hw_p, laptop_sp, screen_cat,
            'High', 'Open', eu_amit, None,
            created_days_ago=1,
            custom_fields={'Asset Tag': 'AST-00421', 'Device Location': 'Head Office', 'Warranty Status': 'Under Warranty'},
        )
        make_ticket(
            'Unable to connect to VPN from home',
            'Getting "Authentication Failed" error when trying to connect to office VPN. Was working fine last week.',
            it_dept, nw_p, vpn_sp, vpn_conn_cat,
            'High', 'Open', eu_deepika, None,
            created_days_ago=1,
        )
        make_ticket(
            'Salary not credited for April 2026',
            'My salary for April 2026 has not been credited to my bank account. The payroll portal shows "Processed" but bank shows no credit.',
            hr_dept, payroll_p, pay_salary_sp, salary_cat,
            'Critical', 'Open', eu_sneha, None,
            created_days_ago=0,
            custom_fields={'Employee ID': 'EMP-0218', 'Pay Period': 'April', 'Expected Amount': '85000'},
        )
        make_ticket(
            'New access card request for joining employee',
            'New joiner Priya Mehta (EMP-0301) requires an access card for Building A and server room.',
            fac_dept, security_p, card_sp, card_new_cat,
            'Medium', 'Open', eu_mohammed, None,
            created_days_ago=2,
            custom_fields={'Building / Floor': 'Building A - GF', 'Urgency Level': 'Normal'},
        )
        make_ticket(
            'Purchase Order PO-2026-0892 pending approval for 5 days',
            'PO-2026-0892 for printer cartridges (₹12,450) has been pending finance approval for 5 days. Need urgent clearance.',
            ops_dept, procure_p, po_sp, po_cat,
            'Medium', 'Open', eu_kavitha, None,
            created_days_ago=5,
        )

        # -- IN PROGRESS tickets (6) -------------------------------------------
        make_ticket(
            'ERP system very slow during morning hours',
            'The ERP system becomes extremely slow between 9 AM and 11 AM. Page loads take 3–4 minutes. All users in finance affected.',
            it_dept, sw_p, erp_sp, login_cat,
            'Critical', 'InProgress', eu_rajan, ag_rahul,
            created_days_ago=3,
            messages=[
                (ag_rahul, 'Hi Rajan, I have escalated this to the server team. We are checking the DB load.', False, 2),
                (eu_rajan, 'Thank you. The issue is still occurring today morning as well.', False, 5),
                (ag_rahul, 'We have identified high query load from a batch job. Rescheduling it to off-hours.', False, 6),
            ],
            custom_fields={'Software Name': 'SAP ERP', 'Version': '6.0 EHP8', 'License Type': 'Volume'},
        )
        make_ticket(
            'Office WiFi not working in 2nd floor conference rooms',
            'All three conference rooms on 2nd floor have no WiFi connectivity since yesterday. Wired connection works fine.',
            it_dept, nw_p, wifi_sp, Category.query.filter_by(name='Cannot Connect').first(),
            'High', 'InProgress', eu_amit, ag_pooja,
            created_days_ago=2,
            messages=[
                (ag_pooja, 'Checked the access points — AP-201 appears to be offline. Contacting Cisco support.', False, 3),
                (eu_amit,  'Any update? We have a client meeting tomorrow in the conference room.', False, 6),
                (ag_pooja, 'Cisco engineer is visiting tomorrow morning. I will expedite.', False, 7),
                (ag_pooja, 'Internal note: AP-201 needs firmware rollback. Test env ready.', True, 8),
            ],
        )
        make_ticket(
            'Reimbursement for January travel expenses pending',
            'I submitted my January travel reimbursement on 10-Feb. The amount is ₹23,400. Status shows "Under Review" for over 60 days.',
            fin_dept, reimb_p, travel_sp, pend_reimb_cat,
            'Medium', 'InProgress', eu_rajan, ag_ananya,
            created_days_ago=7,
            messages=[
                (ag_ananya, 'Hi Rajan, I have received your claim. Reviewing the bills.', False, 2),
                (eu_rajan, 'Please also check the hotel receipt — I have added it to the portal.', False, 4),
                (ag_ananya, 'Found a discrepancy in the hotel bill. Can you re-upload a clearer scan?', False, 5),
            ],
            custom_fields={'Invoice / Bill Number': 'TRV-JAN-2026-0042', 'Expense Amount (₹)': '23400',
                           'Purpose': 'Business Travel', 'Supporting Documents': 'true'},
        )
        make_ticket(
            'AC not working in IT server room — temperature rising',
            'The AC unit in the server room has stopped working. Temperature is rising above safe thresholds. URGENT.',
            fac_dept, maint_p, elec_sp, ac_cat,
            'Critical', 'InProgress', eu_mohammed, ag_meena,
            created_days_ago=1,
            messages=[
                (ag_meena, 'On-site technician has been dispatched. ETA 2 hours.', False, 1),
                (ag_meena, 'Technician onsite — compressor failure confirmed. Replacement unit ordered.', False, 3),
                (eu_mohammed, 'Server room temp is 28°C now. How long will this take?', False, 4),
                (ag_meena, 'Replacement unit arrives tomorrow morning. Emergency portable unit placed tonight.', False, 5),
            ],
            custom_fields={'Building / Floor': 'Building A - 1F', 'Room / Desk No.': 'Server Room SR-01',
                           'Urgency Level': 'Emergency', 'Affected Equipment': 'AC Unit #2 - 2 Ton Split'},
        )
        make_ticket(
            'Delivery of office stationery order delayed by 10 days',
            'Order #ORD-2026-0155 for office stationery was supposed to arrive on 5-May. Still not received.',
            ops_dept, logistics_p, delivery_sp, delay_del_cat,
            'Low', 'InProgress', eu_kavitha, ag_suresh,
            created_days_ago=12,
            messages=[
                (ag_suresh, 'Contacted the vendor. Delay due to port congestion. New ETA: 18-May.', False, 2),
                (eu_kavitha, 'That is 3 more days. We are running critically low on printer paper.', False, 3),
                (ag_suresh, 'Arranging emergency local purchase for paper. Will update.', False, 4),
            ],
        )
        make_ticket(
            'HR system access not given to new joinees',
            'Three new employees who joined on 1-May still do not have HR system login credentials.',
            hr_dept, recruit_p, onboard_sp, Category.query.filter_by(name='System Access').first(),
            'High', 'InProgress', eu_arjun, ag_vishal,
            created_days_ago=4,
            messages=[
                (ag_vishal, 'Raised the request with IT. Accounts should be ready by EOD.', False, 2),
                (eu_arjun,  'Still pending for 2 of the 3 employees.', False, 24),
                (ag_vishal, 'AD provisioning done for all 3. Sending credentials now.', False, 26),
            ],
        )

        # -- HOLD tickets (3) -------------------------------------------------
        make_ticket(
            'Outlook not syncing emails for past 3 days',
            'Outlook shows "Disconnected" status. Tried restarting, re-adding account — issue persists. Needs new SSL cert possibly.',
            it_dept, sw_p, email_sp, access_cat,
            'High', 'Hold', eu_deepika, ag_pooja,
            created_days_ago=6,
            messages=[
                (ag_pooja,  'Investigating — this seems related to the Exchange cert renewal. Ticket #INC-445 filed with Microsoft.', False, 4),
                (eu_deepika,'I cannot send or receive emails at all. This is blocking my work.', False, 5),
                (ag_pooja,  'Placed on hold pending Microsoft response. ETA 48 hours.', False, 6),
            ],
            custom_fields={'Software Name': 'Microsoft Outlook', 'Version': '2021', 'License Type': 'Individual'},
        )
        make_ticket(
            'Wrong deduction in February payslip',
            'Extra ₹4,500 deducted under "Miscellaneous" category in Feb payslip. No explanation provided.',
            hr_dept, payroll_p, pay_salary_sp, wrong_amt_cat,
            'Medium', 'Hold', eu_sneha, ag_vishal,
            created_days_ago=10,
            messages=[
                (ag_vishal, 'Requested payroll team to review the deduction. Awaiting their response.', False, 2),
                (eu_sneha,  'This has been pending for a week. Can you escalate?', False, 72),
                (ag_vishal, 'Escalated to payroll manager. Ticket on hold pending audit.', False, 74),
            ],
            custom_fields={'Employee ID': 'EMP-0218', 'Pay Period': 'February', 'Expected Amount': '85000', 'Received Amount': '80500'},
        )
        make_ticket(
            'Vendor invoice INV-2026-003 approval blocked',
            'Invoice from ABC Supplies (₹1,28,000) stuck in approval queue. Vendor is threatening to halt supply.',
            fin_dept, invoice_p, vendor_sp, pay_delay_cat,
            'High', 'Hold', eu_rajan, ag_ananya,
            created_days_ago=8,
            messages=[
                (ag_ananya, 'GM Finance approval needed. Sent reminder — awaiting sign-off.', False, 3),
                (eu_rajan,  'Vendor has sent a legal notice now. Please escalate.', False, 48),
                (ag_ananya, 'CFO has been notified. On hold for executive approval.', True, 49),
            ],
            custom_fields={'Invoice / Bill Number': 'INV-2026-003', 'Expense Amount (₹)': '128000', 'Purpose': 'Office Supplies'},
        )

        # -- RESOLVED tickets (5) ----------------------------------------------
        make_ticket(
            'Printer not printing — paper jam in HP LaserJet',
            'HP LaserJet MFP in accounts section showing paper jam error. Paper removed but error persists.',
            it_dept, hw_p, printer_sp, Category.query.filter_by(name='Paper Jam').first(),
            'Low', 'Resolved', eu_amit, ag_rahul,
            created_days_ago=10, resolved_days_ago=9,
            messages=[
                (ag_rahul, 'Cleared roller sensor jam and reset printer. Please test.', False, 2),
                (eu_amit,  'Working now! Thank you.', False, 3),
            ],
            custom_fields={'Asset Tag': 'AST-00312', 'Device Location': 'Head Office', 'Warranty Status': 'Out of Warranty'},
        )
        make_ticket(
            'New employee laptop setup for Kiran Rao',
            'New joiner Kiran Rao (EMP-0299) needs laptop configured with office apps, VPN and email.',
            it_dept, hw_p, laptop_sp, bat_cat,
            'Medium', 'Resolved', admin_user, ag_rahul,
            created_days_ago=8, resolved_days_ago=7,
            messages=[
                (ag_rahul, 'Laptop imaged with standard SOE. Office 365, VPN client and antivirus installed.', False, 3),
                (ag_rahul, 'Handed over to Kiran Rao. User confirmed all applications working.', False, 5),
                (admin_user,'Marking as resolved.', False, 6),
            ],
        )
        make_ticket(
            'Annual leave balance incorrect — shows 0 days remaining',
            'The HR portal shows 0 annual leave days remaining for me. I have 12 days remaining as per my records.',
            hr_dept, leave_p, annual_sp, Category.query.filter_by(name='Balance Query').first(),
            'Medium', 'Resolved', eu_arjun, ag_vishal,
            created_days_ago=15, resolved_days_ago=13,
            messages=[
                (ag_vishal, 'Checked with HR system team. Data migration error during system upgrade affected some records.', False, 2),
                (ag_vishal, 'Leave balance corrected to 12 days. Please check the portal.', False, 5),
                (eu_arjun,  'Confirmed — balance is showing correctly now. Thank you!', False, 6),
            ],
            custom_fields={'Employee ID': 'EMP-0211'},
        )
        make_ticket(
            'Power failure in Building B ground floor for 2 hours',
            'Power went out in Building B GF at 10 AM. All workstations and lights are off.',
            fac_dept, maint_p, elec_sp, power_cat,
            'Critical', 'Resolved', eu_mohammed, ag_meena,
            created_days_ago=20, resolved_days_ago=20,
            messages=[
                (ag_meena,   'Electrician on site. Main circuit breaker tripped. Resetting now.', False, 0),
                (ag_meena,   'Power restored at 10:45 AM. Root cause: overloaded circuit. Load balancing scheduled.', False, 1),
                (eu_mohammed,'Power is back. Thank you for the quick resolution!', False, 2),
            ],
            custom_fields={'Building / Floor': 'Building B - GF', 'Urgency Level': 'Emergency'},
        )
        make_ticket(
            'Medical reimbursement claim for March hospitalisation',
            'Claiming ₹45,000 for hospitalisation at Apollo Hospital in March. All bills submitted on portal.',
            fin_dept, reimb_p, medical_sp, Category.query.filter_by(name='Claim Submission').first(),
            'Medium', 'Resolved', eu_sneha, ag_ananya,
            created_days_ago=25, resolved_days_ago=20,
            messages=[
                (ag_ananya, 'Documents verified. Claim approved by HR. Processing payment.', False, 5),
                (ag_ananya, 'Amount ₹42,800 processed (₹2,200 non-eligible as per policy). Will reflect in next payroll.', False, 7),
                (eu_sneha,  'Amount received. Thank you. Could you send me the policy document on non-eligible items?', False, 8),
                (ag_ananya, 'Sent the policy PDF to your email. Marking resolved.', False, 9),
            ],
            custom_fields={'Invoice / Bill Number': 'MED-MAR-2026-009', 'Expense Amount (₹)': '45000',
                           'Purpose': 'Medical', 'Supporting Documents': 'true'},
        )

        # -- CLOSED tickets (4) -----------------------------------------------
        make_ticket(
            'Desktop replacement for Accounts team',
            'Two desktop PCs in accounts are more than 6 years old. Requesting replacement with new systems.',
            it_dept, hw_p, desktop_sp, Category.query.filter_by(name='Replacement').first(),
            'Low', 'Closed', eu_rajan, ag_pooja,
            created_days_ago=60, resolved_days_ago=52, closed_days_ago=45,
            messages=[
                (ag_pooja,  'PO raised for 2 new desktop units. Procurement tracking #PO-2026-0211.', False, 5),
                (ag_pooja,  'New desktops delivered and configured. Handed over to accounts team.', False, 12),
                (eu_rajan,  'Both machines working perfectly. Thanks!', False, 13),
            ],
        )
        make_ticket(
            'Office phone extension 2045 not ringing',
            'The desk phone at extension 2045 does not ring for incoming calls. Outgoing calls work fine.',
            fac_dept, maint_p, elec_sp, Category.query.filter_by(name='Light Repair').first(),
            'Low', 'Closed', eu_kavitha, ag_meena,
            created_days_ago=45, resolved_days_ago=43, closed_days_ago=40,
            messages=[
                (ag_meena, 'IT telecoms team checked — phone config issue. Reset ring settings.', False, 3),
                (eu_kavitha,'Phone working now. Thank you!', False, 4),
            ],
        )
        make_ticket(
            'Salary advance request — family emergency',
            'Requesting ₹30,000 salary advance due to family medical emergency. Will be deducted over 3 months.',
            hr_dept, payroll_p, pay_bonus_sp, Category.query.filter_by(name='Not Received').first(),
            'High', 'Closed', eu_arjun, ag_vishal,
            created_days_ago=30, resolved_days_ago=27, closed_days_ago=25,
            messages=[
                (ag_vishal, 'Advance request approved by HR manager. Finance team processing.', False, 4),
                (ag_vishal, 'Amount of ₹30,000 credited to your account. Deduction of ₹10,000/month starts from June.', False, 6),
                (eu_arjun,  'Received. Thank you for the quick processing.', False, 7),
            ],
            custom_fields={'Employee ID': 'EMP-0211', 'Pay Period': 'May', 'Expected Amount': '30000'},
        )
        make_ticket(
            'Vendor registration for TechCorp Pvt Ltd',
            'New vendor TechCorp Pvt Ltd needs to be registered in the procurement system for IT supply contracts.',
            ops_dept, procure_p, vendor2_sp, Category.query.filter_by(name='Vendor Registration').first(),
            'Low', 'Closed', eu_kavitha, ag_suresh,
            created_days_ago=40, resolved_days_ago=35, closed_days_ago=30,
            messages=[
                (ag_suresh, 'Documents verified. GST cert, PAN, and bank details collected. Registration submitted.', False, 5),
                (ag_suresh, 'TechCorp registered as approved vendor. Vendor code: VND-0892.', False, 8),
                (eu_kavitha,'Registration complete. Thank you!', False, 9),
            ],
        )

        # -- REJECTED tickets (3) ----------------------------------------------
        make_ticket(
            'Request for 4K curved monitor — productivity upgrade',
            'Requesting a 4K curved monitor (32 inch) for better productivity while working on design projects.',
            it_dept, hw_p, desktop_sp, Category.query.filter_by(name='Replacement').first(),
            'Low', 'Rejected', eu_deepika, ag_pooja,
            created_days_ago=14,
            messages=[
                (ag_pooja,  'Request reviewed. Standard issue monitors are 24" 1080p. 4K curved monitors are not in budget allocation for non-design roles.', False, 4),
                (eu_deepika,'I do work on graphics. Can this be escalated to my manager?', False, 5),
                (ag_pooja,  'Escalated to manager. Rejected — insufficient business justification for the budget exception.', False, 8),
            ],
        )
        make_ticket(
            'Reimbursement claim for personal gym membership',
            'Requesting reimbursement for gym membership (₹6,000/year) as part of wellness policy.',
            fin_dept, reimb_p, travel_sp, Category.query.filter_by(name='Rejected Claim').first(),
            'Low', 'Rejected', eu_rajan, ag_ananya,
            created_days_ago=20,
            messages=[
                (ag_ananya, 'Reviewed with HR. Personal gym memberships are not covered under the wellness reimbursement policy.', False, 3),
                (eu_rajan,  'I was informed by my manager that it is covered?', False, 4),
                (ag_ananya, 'Confirmed with HR policy document Section 4.2 — only corporate gym tie-ups are covered. Rejecting claim.', False, 5),
            ],
        )
        make_ticket(
            'Request for standing desk and ergonomic chair',
            'Requesting a standing desk and Herman Miller ergonomic chair for workspace upgrade (₹85,000).',
            fac_dept, space_p, seat_sp, Category.query.filter_by(name='New Seat Allocation').first(),
            'Medium', 'Rejected', eu_mohammed, ag_meena,
            created_days_ago=25,
            messages=[
                (ag_meena, 'Request received. Budget for FY2026 furniture is exhausted. Can consider in Q1 FY2027.', False, 5),
                (eu_mohammed,'This is important for my back condition (have medical certificate).', False, 6),
                (ag_meena, 'Re-evaluated with medical certificate. Ergonomic chair approved, standing desk deferred to next FY.', False, 8),
                (ag_meena, 'Correction — both items rejected by facilities manager due to budget. Will re-raise in April 2027.', False, 10),
            ],
        )

        # -- REOPENED tickets (2) ----------------------------------------------
        make_ticket(
            'Internet speed very slow — 2 Mbps instead of 100 Mbps',
            'Office internet speed is 2 Mbps since last upgrade. All users affected. Speed test confirmed.',
            it_dept, nw_p, inet_sp, no_inet_cat,
            'Critical', 'Reopened', eu_amit, ag_rahul,
            created_days_ago=20,
            messages=[
                (ag_rahul,  'ISP contacted. They fixed a misconfiguration on the switch. Speed restored to 100 Mbps.', False, 5),
                (eu_amit,   'Speed was good for 2 days but has dropped again to ~5 Mbps.', False, 72),
                (ag_rahul,  'Reopening ticket. ISP will send a senior engineer.', False, 73),
                (ag_rahul,  'Internal note: ISP SLA breach documented. Compensation claim being filed.', True, 74),
            ],
        )
        make_ticket(
            'ERP login locked — password reset not working',
            'ERP account locked after 3 failed attempts. Password reset email not being received.',
            it_dept, sw_p, erp_sp, login_cat,
            'High', 'Reopened', eu_deepika, ag_pooja,
            created_days_ago=12,
            messages=[
                (ag_pooja,  'Account unlocked. Reset email sent. Please try now.', False, 2),
                (eu_deepika,'I logged in successfully. Marking resolved.', False, 3),
                (eu_deepika,'Account locked again. Same issue after 3 days.', False, 75),
                (ag_pooja,  'Reopening. Investigating possible brute-force attempts on the account.', False, 76),
                (ag_pooja,  'Internal: IP restriction being added. Awaiting security team sign-off.', True, 77),
            ],
            custom_fields={'Software Name': 'SAP ERP', 'Version': '6.0 EHP8', 'License Type': 'Volume'},
        )

        db.session.commit()
        print('\n  All tickets committed.')

        # ====================================================================
        # KNOWLEDGE BASE
        # ====================================================================
        print('\n-- Knowledge Base --------------------------------------------')

        def make_kb_cat(name, slug, desc, order):
            c, created = get_or_create(KBCategory, slug=slug,
                                       defaults={'name': name, 'description': desc,
                                                 'order': order, 'is_active': True})
            if not created:
                print(f'  SKIP  KB Cat: {name}')
            else:
                print(f'  CREATE KB Cat: {name}')
            db.session.flush()
            return c

        def make_kb_article(title, slug, content, cat, tags, published=True):
            a = KBArticle.query.filter_by(slug=slug).first()
            if a:
                print(f'  SKIP  KB Article: {title}')
                return a
            a = KBArticle(title=title, slug=slug, content=content,
                          category_id=cat.id, author_id=admin_user.id,
                          tags=tags, is_published=published, views=0)
            db.session.add(a)
            db.session.flush()
            print(f'  CREATE KB Article: {title}')
            return a

        kb_it   = make_kb_cat('IT Self-Service',      'it-self-service',      'Common IT issues you can solve yourself.',   1)
        kb_hr   = make_kb_cat('HR Policies & Guides', 'hr-policies',          'Leave, payroll and HR policy guides.',        2)
        kb_fin  = make_kb_cat('Finance & Accounts',   'finance-accounts',     'Reimbursement, invoice and payment guides.',  3)
        kb_fac  = make_kb_cat('Facilities & Admin',   'facilities-admin',     'Workspace, access and maintenance FAQs.',     4)
        kb_gen  = make_kb_cat('General Guides',       'general-guides',       'General CKSM usage and company policies.',    5)

        make_kb_article(
            'How to Reset Your Windows Password',
            'how-to-reset-windows-password',
            '''If your Windows account is locked or you have forgotten your password, follow these steps:

1. On the login screen, click "I forgot my PIN" or "Reset Password".
2. Verify your identity using the Microsoft Authenticator app or recovery email.
3. Set a new password — it must be at least 12 characters with uppercase, lowercase, number and special character.
4. If the above does not work, contact IT Helpdesk via CKSM and raise a ticket under IT > Security > Account Security > Password Reset.

Note: IT will never ask for your current password. Beware of phishing attempts.''',
            kb_it, 'password,windows,login,reset', True,
        )
        make_kb_article(
            'Connecting to Office VPN from Home',
            'connecting-to-office-vpn',
            '''To access office resources from home, you need to connect via the Cisco AnyConnect VPN client.

Steps:
1. Open Cisco AnyConnect on your laptop.
2. Enter the server address: vpn.citykart.com
3. Use your office email and Windows password to authenticate.
4. Accept the Duo MFA push notification on your mobile.
5. You are now connected. All traffic routes through the office network.

Troubleshooting:
- "Authentication Failed": Your password may have expired. Reset it first on the office network.
- "Connection Timed Out": Check your home internet connection. Try a different network.
- "Certificate Error": Reinstall the VPN client from Software Center.

For persistent issues, raise a ticket: IT > Network > VPN > Cannot Connect.''',
            kb_it, 'vpn,remote work,cisco,anyconnect', True,
        )
        make_kb_article(
            'How to Submit a Reimbursement Claim',
            'how-to-submit-reimbursement-claim',
            '''All reimbursement claims must be submitted within 30 days of the expense date.

Steps:
1. Log in to the Employee Self-Service portal.
2. Go to Finance > Reimbursement > New Claim.
3. Select the expense category: Travel, Medical, Training, etc.
4. Upload all original bills/receipts (PDF or clear photo).
5. Enter the amount and date for each bill.
6. Submit the claim.

Approval flow:
- Claims up to ₹5,000: Direct Manager approval
- Claims ₹5,001–₹25,000: Department Head approval
- Claims above ₹25,000: Finance Controller approval

Payment is processed with the next payroll cycle (typically by the 5th of the following month).

Important: Personal expenses (gym, entertainment, personal travel) are NOT eligible for reimbursement.''',
            kb_fin, 'reimbursement,finance,claim,expense', True,
        )
        make_kb_article(
            'Annual Leave Policy — FY 2026-27',
            'annual-leave-policy-fy2026',
            '''Annual Leave Entitlement:
- Confirmed employees: 18 days per year
- Employees in probation: 9 days per year (pro-rated)
- Senior staff (5+ years): 21 days per year

Leave Carry-Forward:
- Maximum 10 days can be carried forward to next FY.
- Balance beyond 10 days lapses on 31st March.

Leave Application Process:
1. Submit leave request in HR portal at least 3 working days in advance.
2. Manager approval required for leaves of 1–3 days.
3. HR Head approval required for leaves exceeding 3 consecutive days.

Long Leave (Medical/Maternity/Paternity):
- Medical leave up to 15 days (with certificate).
- Maternity leave: 26 weeks for first 2 children.
- Paternity leave: 5 days.

For leave balance queries, raise an HR ticket: HR > Leave Management > Annual Leave > Balance Query.''',
            kb_hr, 'leave,annual leave,policy,HR', True,
        )
        make_kb_article(
            'How to Raise a Support Ticket in CKSM',
            'how-to-raise-a-support-ticket',
            '''CKSM (Citykart Service Management) is the official helpdesk platform for all IT, HR, Finance and Facilities requests.

Steps to raise a ticket:
1. Log in to CKSM at https://cksm.citykart.com.
2. Click "New Ticket" in the top navigation bar.
3. Select the Department (IT / HR / Finance / Operations / Facilities).
4. Choose the relevant Problem, Sub-Problem and Category from the dropdown menus.
5. Enter a clear Title and detailed Description.
6. Set Priority: Critical (system down), High (major impact), Medium (work-around available), Low (minor).
7. Attach any supporting documents or screenshots.
8. Click Submit.

Ticket Status meanings:
- Open: Ticket received, not yet assigned.
- InProgress: Agent actively working on it.
- Hold: Waiting for third-party or approval.
- Resolved: Issue fixed. Please confirm within 3 days or it auto-closes.
- Closed: Ticket complete.
- Rejected: Request not fulfilled (see agent notes for reason).
- Reopened: Issue recurred after resolution.

SLA targets:
- Critical: First response 1 hour, Resolution 4 hours
- High: First response 2 hours, Resolution 8 hours
- Medium: First response 4 hours, Resolution 24 hours
- Low: First response 8 hours, Resolution 48 hours''',
            kb_gen, 'cksm,helpdesk,ticket,guide,how-to', True,
        )

        db.session.commit()
        print('  Knowledge Base committed.')

        # ====================================================================
        # SLA policies for new departments
        # ====================================================================
        print('\n-- SLA Policies ----------------------------------------------')
        for dept, short in [(ops_dept, 'Ops'), (fac_dept, 'Fac'), (hr_dept, 'HR'), (fin_dept, 'Fin')]:
            for priority, fr, res in [('Critical', 1.0, 4.0), ('High', 2.0, 8.0),
                                       ('Medium', 4.0, 24.0), ('Low', 8.0, 48.0)]:
                name = f'{short} – {priority}'
                pol = SLAPolicy.query.filter_by(name=name).first()
                if not pol:
                    db.session.add(SLAPolicy(
                        name=name, department_id=dept.id, priority=priority,
                        first_response_hours=fr, resolution_hours=res,
                        use_business_hours=True, is_active=True,
                    ))
                    print(f'  CREATE  {name}')
        db.session.commit()
        print('  SLA policies committed.')

        # ====================================================================
        # PRIORITY RULES
        # ====================================================================
        print('\n-- Priority Rules --------------------------------------------')

        from app.models.priority_rule import PriorityRule, PriorityRuleGroup, PriorityRuleCondition

        def make_priority_rule(name, set_priority, eval_order, groups_spec):
            """
            groups_spec: list of lists of (field, operator, value)
              - value is an integer FK for entity fields (department/problem/etc.)
              - value is a string for the 'priority' field
            Each inner list = one AND-group. Outer list = OR between groups.
            """
            if PriorityRule.query.filter_by(name=name).first():
                print(f'  SKIP  {name}')
                return
            rule = PriorityRule(
                name=name,
                set_priority=set_priority,
                priority_order=eval_order,
                is_active=True,
                stop_on_match=True,
            )
            db.session.add(rule)
            db.session.flush()
            for g_idx, conditions in enumerate(groups_spec):
                group = PriorityRuleGroup(rule_id=rule.id, group_order=g_idx)
                db.session.add(group)
                db.session.flush()
                for c_idx, (field, operator, value) in enumerate(conditions):
                    cond = PriorityRuleCondition(
                        group_id=group.id,
                        field=field,
                        operator=operator,
                        value_id=value if field != 'priority' else None,
                        value_str=value if field == 'priority' else None,
                        condition_order=c_idx,
                    )
                    db.session.add(cond)
            db.session.flush()
            print(f'  CREATE  [{set_priority:8}]  {name}')

        # --- Critical rules (evaluated first) ---
        make_priority_rule(
            'IT – Security Issues → Critical', 'Critical', 10,
            [[('department', 'is', it_dept.id), ('problem', 'is', sec_p.id)]]
        )
        make_priority_rule(
            'HR – Payroll Issues → Critical', 'Critical', 20,
            [[('department', 'is', hr_dept.id), ('problem', 'is', payroll_p.id)]]
        )

        # --- High rules ---
        make_priority_rule(
            'IT – Hardware Issues → High', 'High', 30,
            [[('department', 'is', it_dept.id), ('problem', 'is', hw_p.id)]]
        )
        make_priority_rule(
            'IT – Network Issues → High', 'High', 40,
            [[('department', 'is', it_dept.id), ('problem', 'is', nw_p.id)]]
        )
        make_priority_rule(
            'Finance – Invoice Issues → High', 'High', 50,
            [[('department', 'is', fin_dept.id), ('problem', 'is', invoice_p.id)]]
        )
        make_priority_rule(
            'Facilities – Maintenance → High', 'High', 60,
            [[('department', 'is', fac_dept.id), ('problem', 'is', maint_p.id)]]
        )
        make_priority_rule(
            'Facilities – Security → High', 'High', 70,
            [[('department', 'is', fac_dept.id), ('problem', 'is', security_p.id)]]
        )

        # --- Medium rules ---
        make_priority_rule(
            'IT – Software Issues → Medium', 'Medium', 80,
            [[('department', 'is', it_dept.id), ('problem', 'is', sw_p.id)]]
        )
        make_priority_rule(
            'HR – Leave Management → Medium', 'Medium', 90,
            [[('department', 'is', hr_dept.id), ('problem', 'is', leave_p.id)]]
        )
        make_priority_rule(
            'Finance – Reimbursement → Medium', 'Medium', 100,
            [[('department', 'is', fin_dept.id), ('problem', 'is', reimb_p.id)]]
        )
        make_priority_rule(
            'Operations – All Issues → Medium', 'Medium', 110,
            [[('department', 'is', ops_dept.id)]]
        )

        # --- Low rules ---
        make_priority_rule(
            'HR – Recruitment → Low', 'Low', 120,
            [[('department', 'is', hr_dept.id), ('problem', 'is', recruit_p.id)]]
        )
        make_priority_rule(
            'HR – Benefits → Low', 'Low', 130,
            [[('department', 'is', hr_dept.id), ('problem', 'is', benefit_p.id)]]
        )
        make_priority_rule(
            'Finance – Budget → Low', 'Low', 140,
            [[('department', 'is', fin_dept.id), ('problem', 'is', budget_p.id)]]
        )

        db.session.commit()
        print('  Priority rules committed.')

        # ====================================================================
        # ASSIGNMENT RULES
        # ====================================================================
        print('\n-- Assignment Rules ------------------------------------------')

        from app.models.assignment_rule import AssignmentRule, AssignmentRuleGroup, AssignmentRuleCondition

        def make_assignment_rule(name, agent_user, eval_order, groups_spec):
            """
            groups_spec: list of lists of (field, operator, value_id)
            Each inner list = one AND-group. Outer list = OR between groups.
            """
            if AssignmentRule.query.filter_by(name=name).first():
                print(f'  SKIP  {name}')
                return
            rule = AssignmentRule(
                name=name,
                assigned_to_id=agent_user.id,
                priority=eval_order,
                is_active=True,
                stop_on_match=True,
            )
            db.session.add(rule)
            db.session.flush()
            for g_idx, conditions in enumerate(groups_spec):
                group = AssignmentRuleGroup(rule_id=rule.id, group_order=g_idx)
                db.session.add(group)
                db.session.flush()
                for c_idx, (field, operator, value_id) in enumerate(conditions):
                    cond = AssignmentRuleCondition(
                        group_id=group.id,
                        field=field,
                        operator=operator,
                        value_id=value_id,
                        condition_order=c_idx,
                    )
                    db.session.add(cond)
            db.session.flush()
            print(f'  CREATE  {name}  →  {agent_user.full_name}')

        # IT Hardware / Network / Security → Rahul Sharma
        make_assignment_rule(
            'IT Hardware / Network / Security → Rahul Sharma',
            ag_rahul, 1,
            [
                [('department', 'is', it_dept.id), ('problem', 'is', hw_p.id)],
                [('department', 'is', it_dept.id), ('problem', 'is', nw_p.id)],
                [('department', 'is', it_dept.id), ('problem', 'is', sec_p.id)],
            ]
        )
        # IT Software → Pooja Iyer
        make_assignment_rule(
            'IT Software → Pooja Iyer',
            ag_pooja, 2,
            [
                [('department', 'is', it_dept.id), ('problem', 'is', sw_p.id)],
            ]
        )
        # HR → Vishal Nair
        make_assignment_rule(
            'HR Department → Vishal Nair',
            ag_vishal, 3,
            [
                [('department', 'is', hr_dept.id)],
            ]
        )
        # Finance → Ananya Reddy
        make_assignment_rule(
            'Finance Department → Ananya Reddy',
            ag_ananya, 4,
            [
                [('department', 'is', fin_dept.id)],
            ]
        )
        # Operations → Suresh Kumar
        make_assignment_rule(
            'Operations Department → Suresh Kumar',
            ag_suresh, 5,
            [
                [('department', 'is', ops_dept.id)],
            ]
        )
        # Facilities → Meena Pillai
        make_assignment_rule(
            'Facilities Department → Meena Pillai',
            ag_meena, 6,
            [
                [('department', 'is', fac_dept.id)],
            ]
        )

        db.session.commit()
        print('  Assignment rules committed.')

        # ====================================================================
        # FINAL SUMMARY
        # ====================================================================
        total_tickets = Ticket.query.count()
        total_users   = User.query.count()
        total_agents  = User.query.join(Role).filter(Role.name == 'Agent').count()
        total_kb      = KBArticle.query.filter_by(is_published=True).count()

        print('\n==============================================================')
        print('  Demo seed complete!')
        print(f'  Departments : {Department.query.count()}')
        print(f'  Problems    : {Problem.query.count()}')
        print(f'  SubProblems : {SubProblem.query.count()}')
        print(f'  Categories  : {Category.query.count()}')
        print(f'  SubCategories:{SubCategory.query.count()}')
        print(f'  Form Templates: {FormTemplate.query.count()} (with fields)')
        print(f'  Total Users : {total_users}  (Agents: {total_agents})')
        print(f'  Total Tickets: {total_tickets}')
        print(f'  KB Articles : {total_kb}')
        print()
        print('  Ticket status breakdown:')
        for status in ['Open', 'InProgress', 'Hold', 'Resolved', 'Closed', 'Rejected', 'Reopened']:
            n = Ticket.query.filter_by(status=status).count()
            print(f'    {status:12} {n}')
        print()
        print('  Login credentials (password for all demo users: Demo@1234):')
        print('    Admin  : admin@citykart.com  / admin123')
        print('    Agents : pooja@citykart.com, vishal@citykart.com,')
        print('             ananya@citykart.com, suresh@citykart.com, meena@citykart.com')
        print('    Users  : amit@citykart.com, sneha@citykart.com, rajan@citykart.com,')
        print('             kavitha@citykart.com, mohammed@citykart.com,')
        print('             deepika@citykart.com, arjun@citykart.com')
        print('==============================================================\n')


if __name__ == '__main__':
    seed_demo()
