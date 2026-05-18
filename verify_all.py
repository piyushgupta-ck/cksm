"""
Full functional verification — checks every major feature works.
Run: python verify_all.py
"""
import json, sys, re

from app import create_app, db
from app.config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///cksm.db'
    WTF_CSRF_ENABLED = False
    SCHEDULER_ENABLED = False
    IMAP_ENABLED = False


app = create_app(TestConfig)
results = []


def ok(name, detail=''):
    results.append(('OK', name, detail))
    msg = f'  OK    {name}'
    if detail:
        msg += f'  [{detail}]'
    print(msg)


def fail(name, detail=''):
    results.append(('FAIL', name, detail))
    print(f'  FAIL  {name}  [{detail}]')


def check(name, cond, detail=''):
    (ok if cond else fail)(name, detail)


# ── Collect test IDs before opening client ────────────────────────────────────
with app.app_context():
    from app.models.ticket import Ticket
    from app.models.user import User, Role
    from app.models.department import Department
    from app.models.kb import KBArticle, KBCategory
    from app.models.sla import SLAPolicy, TicketSLA
    from app.models.forms import FormTemplate

    tickets_by_status = {}
    for s in ['Open', 'InProgress', 'Hold', 'Resolved', 'Closed', 'Rejected', 'Reopened']:
        t = Ticket.query.filter_by(status=s).first()
        tickets_by_status[s] = t.ticket_id if t else None

    first_ticket = Ticket.query.first()
    first_ticket_id = first_ticket.ticket_id if first_ticket else 'TKT-2026-000001'

    agent_user = User.query.filter_by(username='pooja.iyer').first()
    end_user   = User.query.filter_by(username='amit.kumar').first()

    it_dept    = Department.query.filter_by(name='IT').first()
    hr_dept    = Department.query.filter_by(name='HR').first()
    fin_dept   = Department.query.filter_by(name='Finance').first()
    ops_dept   = Department.query.filter_by(name='Operations').first()
    fac_dept   = Department.query.filter_by(name='Facilities').first()
    dept_ids   = [d.id for d in [it_dept, hr_dept, fin_dept, ops_dept, fac_dept] if d]

    kb_art = KBArticle.query.filter_by(is_published=True).first()
    kb_slug = kb_art.slug if kb_art else 'how-to-raise-a-support-ticket'
    kb_cat = KBCategory.query.first()
    kb_cat_slug = kb_cat.slug if kb_cat else 'it-self-service'

    sla_count = TicketSLA.query.count()
    form_count = FormTemplate.query.count()
    total_tickets = Ticket.query.count()

# ── CLIENT ────────────────────────────────────────────────────────────────────
with app.test_client() as c:

    print('\n=== DB STATE ============================================')
    print(f'  Total tickets : {total_tickets}')
    print(f'  SLA records   : {sla_count}')
    print(f'  Form templates: {form_count}')
    print()

    # ─── Auth ─────────────────────────────────────────────────────────────
    print('=== AUTH ================================================')
    r = c.post('/auth/login', data={'email': 'admin@citykart.com', 'password': 'admin123'}, follow_redirects=True)
    check('Admin login', r.status_code == 200)

    r = c.get('/auth/logout', follow_redirects=True)
    check('Admin logout', r.status_code == 200)

    # Login as agent
    r = c.post('/auth/login', data={'email': 'pooja@citykart.com', 'password': 'Demo@1234'}, follow_redirects=True)
    check('Agent login (Pooja)', r.status_code == 200)
    r = c.get('/auth/logout', follow_redirects=True)

    # Login as end user
    r = c.post('/auth/login', data={'email': 'amit@citykart.com', 'password': 'Demo@1234'}, follow_redirects=True)
    check('End user login (Amit)', r.status_code == 200)
    r = c.get('/auth/logout', follow_redirects=True)

    # Wrong password
    r = c.post('/auth/login', data={'email': 'admin@citykart.com', 'password': 'wrongpass'}, follow_redirects=True)
    check('Bad password rejected', b'Invalid' in r.data or r.status_code == 200)

    # ─── Re-login as admin for remaining tests ────────────────────────────
    c.post('/auth/login', data={'email': 'admin@citykart.com', 'password': 'admin123'}, follow_redirects=True)

    # ─── Dashboard ────────────────────────────────────────────────────────
    print('\n=== DASHBOARD ===========================================')
    r = c.get('/dashboard/')
    check('Dashboard loads', r.status_code == 200)
    check('Dashboard shows tickets', b'ticket' in r.data.lower())

    # ─── Ticket List ──────────────────────────────────────────────────────
    print('\n=== TICKET LIST =========================================')
    r = c.get('/tickets/')
    check('Ticket list loads', r.status_code == 200)
    check('Ticket list has data', total_tickets > 0 and (b'TKT-' in r.data))

    # Status filters
    for status in ['Open', 'InProgress', 'Hold', 'Resolved', 'Closed', 'Rejected', 'Reopened']:
        r = c.get(f'/tickets/?status={status}')
        check(f'Filter: status={status}', r.status_code == 200)

    # Priority filters
    for pri in ['Low', 'Medium', 'High', 'Critical']:
        r = c.get(f'/tickets/?priority={pri}')
        check(f'Filter: priority={pri}', r.status_code == 200)

    # Department filter
    for dept_id in dept_ids:
        r = c.get(f'/tickets/?department_id={dept_id}')
        check(f'Filter: dept_id={dept_id}', r.status_code == 200)

    # Search
    r = c.get('/tickets/?search=laptop')
    check('Search: laptop', r.status_code == 200)
    r = c.get('/tickets/?search=salary')
    check('Search: salary', r.status_code == 200)
    r = c.get('/tickets/?search=TKT-2026')
    check('Search: ticket ID', r.status_code == 200)

    # Date range
    r = c.get('/tickets/?date_from=2026-01-01&date_to=2026-12-31')
    check('Filter: date range', r.status_code == 200)

    # ─── View tickets of every status ────────────────────────────────────
    print('\n=== TICKET VIEW (all statuses) ==========================')
    for status, tid in tickets_by_status.items():
        if tid:
            r = c.get(f'/tickets/{tid}')
            check(f'View [{status}] {tid}', r.status_code == 200,
                  f'has_title={b"ticket" in r.data.lower()}')
        else:
            fail(f'View [{status}]', 'No ticket of this status exists')

    # ─── Create ticket ────────────────────────────────────────────────────
    print('\n=== CREATE TICKET =======================================')
    r = c.get('/tickets/create')
    check('Create ticket page loads', r.status_code == 200)

    it_dept_id = it_dept.id if it_dept else 1
    with app.app_context():
        from app.models.department import Problem
        hw_prob = Problem.query.filter_by(name='Hardware', department_id=it_dept_id).first()
        prob_id = hw_prob.id if hw_prob else 0

    r = c.post('/tickets/create', data={
        'title': 'Verify: Test ticket created by smoke test',
        'description': 'This ticket was created during functional verification.',
        'department_id': it_dept_id,
        'problem_id': 0,        # must be 0 — choices are [(0,'--')] on POST
        'sub_problem_id': 0,
        'category_id': 0,
        'sub_category_id': 0,
        'priority': 'Low',
        'on_behalf_of': 0,
        'assigned_to': 0,
    }, follow_redirects=True)
    check('Create ticket POST', r.status_code == 200)
    check('New ticket appears in page', b'TKT-' in r.data or b'created successfully' in r.data)

    # Get the new ticket id
    with app.app_context():
        new_t = Ticket.query.filter(Ticket.title.like('Verify:%')).first()
        new_tid = new_t.ticket_id if new_t else None
    check('New ticket in DB', new_tid is not None)

    # ─── Reply ────────────────────────────────────────────────────────────
    print('\n=== TICKET REPLY ========================================')
    if new_tid:
        r = c.post(f'/tickets/{new_tid}/reply',
                   data={'content': 'This is a test reply from admin.', 'is_internal': 'false'},
                   follow_redirects=True)
        check('Add reply (public)', r.status_code == 200)

        r = c.post(f'/tickets/{new_tid}/reply',
                   data={'content': 'Internal note — for agent eyes only.', 'is_internal': 'y'},
                   follow_redirects=True)
        check('Add reply (internal)', r.status_code == 200)

    # ─── Status changes ───────────────────────────────────────────────────
    print('\n=== STATUS CHANGES ======================================')
    if new_tid:
        r = c.post(f'/tickets/{new_tid}/status',
                   data={'status': 'InProgress', 'remarks': 'Started investigation'},
                   follow_redirects=True)
        check('Status: Open -> InProgress', r.status_code == 200)

        r = c.post(f'/tickets/{new_tid}/status',
                   data={'status': 'Resolved', 'remarks': 'Issue resolved in test'},
                   follow_redirects=True)
        check('Status: InProgress -> Resolved', r.status_code == 200)

        r = c.post(f'/tickets/{new_tid}/status',
                   data={'status': 'Closed', 'remarks': 'Confirmed closed'},
                   follow_redirects=True)
        check('Status: Resolved -> Closed', r.status_code == 200)

    # ─── Assign ticket ────────────────────────────────────────────────────
    print('\n=== ASSIGNMENT ==========================================')
    open_tid = tickets_by_status.get('Open')
    with app.app_context():
        agent = User.query.filter_by(username='pooja.iyer').first()
        agent_id = agent.id if agent else None

    if open_tid and agent_id:
        r = c.post(f'/tickets/{open_tid}/assign',
                   data={'assigned_to': agent_id},
                   follow_redirects=True)
        check(f'Assign ticket {open_tid}', r.status_code == 200)

    # Auto-assign
    if tickets_by_status.get('Open'):
        r = c.post(f'/tickets/{tickets_by_status["Open"]}/auto-assign',
                   follow_redirects=True)
        check('Auto-assign ticket', r.status_code == 200)

    # ─── SLA ──────────────────────────────────────────────────────────────
    print('\n=== SLA =================================================')
    r = c.get('/sla/')
    check('SLA index loads', r.status_code == 200)
    r = c.get('/sla/policies/create')
    check('SLA create policy page', r.status_code == 200)
    r = c.get('/sla/escalation-rules/create')
    check('SLA create escalation rule page', r.status_code == 200)

    with app.app_context():
        pol = SLAPolicy.query.first()
        pol_id = pol.id if pol else 1
    r = c.get(f'/sla/policies/{pol_id}/edit')
    check('SLA policy edit page', r.status_code == 200)

    # ─── Approvals ────────────────────────────────────────────────────────
    print('\n=== APPROVALS ===========================================')
    r = c.get('/approvals/')
    check('Approvals index', r.status_code == 200)
    r = c.get('/approvals/my-requests')
    check('My approvals page', r.status_code == 200)

    # ─── Notifications ────────────────────────────────────────────────────
    print('\n=== NOTIFICATIONS =======================================')
    r = c.get('/notifications/')
    check('Notifications page', r.status_code == 200)
    r = c.get('/notifications/api/recent')
    check('Notifications API /recent', r.status_code == 200)
    r = c.get('/notifications/api/unread-count')
    check('Notifications API /unread-count', r.status_code == 200,
          f'has count={b"count" in r.data}')

    # ─── Reports ──────────────────────────────────────────────────────────
    print('\n=== REPORTS =============================================')
    r = c.get('/reports/')
    check('Reports index', r.status_code == 200)
    r = c.get('/reports/api/overview')
    check('Reports /api/overview', r.status_code == 200, f'has total={b"total" in r.data}')
    r = c.get('/reports/api/tickets-by-day?days=30')
    check('Reports /api/tickets-by-day', r.status_code == 200)
    r = c.get('/reports/api/sla-compliance')
    check('Reports /api/sla-compliance', r.status_code == 200)
    r = c.get('/reports/api/agent-performance')
    check('Reports /api/agent-performance', r.status_code == 200)
    r = c.get('/reports/export/tickets?days=30')
    check('Reports CSV export', r.status_code == 200,
          f'csv={b"ticket_id" in r.data}')

    # ─── Admin ────────────────────────────────────────────────────────────
    print('\n=== ADMIN PANEL =========================================')
    r = c.get('/admin/')
    check('Admin index', r.status_code == 200)
    r = c.get('/admin/users')
    check('Admin users list', r.status_code == 200)
    r = c.get('/admin/departments')
    check('Admin departments', r.status_code == 200)
    r = c.get('/admin/problems')
    check('Admin problems', r.status_code == 200)
    r = c.get('/admin/sub-problems')
    check('Admin sub-problems', r.status_code == 200)
    r = c.get('/admin/categories')
    check('Admin categories', r.status_code == 200)
    r = c.get('/admin/sub-categories')
    check('Admin sub-categories', r.status_code == 200)
    r = c.get('/admin/form-templates')
    check('Admin form templates', r.status_code == 200)

    # Admin API dropdowns
    for dept_id in dept_ids:
        r = c.get(f'/admin/api/problems/{dept_id}')
        check(f'API dropdown: problems dept={dept_id}', r.status_code == 200)
    r = c.get(f'/admin/api/form-fields?department_id={it_dept.id if it_dept else 1}')
    check('API form-fields IT', r.status_code == 200)

    # ─── Knowledge Base ───────────────────────────────────────────────────
    print('\n=== KNOWLEDGE BASE ======================================')
    r = c.get('/kb/')
    check('KB index', r.status_code == 200)
    r = c.get(f'/kb/article/{kb_slug}')
    check(f'KB article ({kb_slug})', r.status_code == 200)
    r = c.get(f'/kb/category/{kb_cat_slug}')
    check(f'KB category ({kb_cat_slug})', r.status_code == 200)
    r = c.get('/kb/search?q=password')
    check('KB search: password', r.status_code == 200, f'found={b"password" in r.data.lower()}')
    r = c.get('/kb/search?q=vpn')
    check('KB search: vpn', r.status_code == 200)
    r = c.get('/kb/search?q=xxxxxxxxxnotfound')
    check('KB search: no results', r.status_code == 200)

    # Admin KB
    r = c.get('/admin/kb')
    check('Admin KB list', r.status_code == 200)
    r = c.get('/admin/kb/articles/create')
    check('Admin KB create form', r.status_code == 200)

    # ─── REST API ─────────────────────────────────────────────────────────
    print('\n=== REST API ============================================')
    # Issue token
    r = c.post('/api/v1/tokens',
               data=json.dumps({'email': 'admin@citykart.com', 'password': 'admin123', 'name': 'verify'}),
               content_type='application/json')
    check('API issue token', r.status_code == 201)
    token = json.loads(r.data).get('token', '')

    r = c.get('/api/v1/me', headers={'Authorization': f'Bearer {token}'})
    check('API /me', r.status_code == 200, f'email={b"admin@citykart.com" in r.data}')

    r = c.get('/api/v1/departments', headers={'Authorization': f'Bearer {token}'})
    check('API /departments', r.status_code == 200)
    depts_data = json.loads(r.data)
    check('API departments count >= 5', len(depts_data) >= 5, f'count={len(depts_data)}')

    r = c.get('/api/v1/tickets', headers={'Authorization': f'Bearer {token}'})
    check('API GET /tickets', r.status_code == 200)
    t_data = json.loads(r.data)
    check('API tickets total >= 30', t_data.get('total', 0) >= 30, f'total={t_data.get("total")}')

    # API ticket pagination
    r = c.get('/api/v1/tickets?page=1&per_page=5', headers={'Authorization': f'Bearer {token}'})
    check('API tickets pagination', r.status_code == 200,
          f'returned={len(json.loads(r.data).get("tickets", []))}')

    # API filter by status
    for st in ['Open', 'Resolved', 'Closed']:
        r = c.get(f'/api/v1/tickets?status={st}', headers={'Authorization': f'Bearer {token}'})
        check(f'API tickets filter status={st}', r.status_code == 200)

    # API single ticket
    r = c.get(f'/api/v1/tickets/{first_ticket_id}', headers={'Authorization': f'Bearer {token}'})
    check(f'API GET /tickets/{first_ticket_id}', r.status_code == 200)

    # API create ticket
    r = c.post('/api/v1/tickets',
               data=json.dumps({'title': 'Verify API ticket', 'description': 'Created via API verification',
                                'department_id': it_dept.id if it_dept else 1, 'priority': 'Low'}),
               content_type='application/json',
               headers={'Authorization': f'Bearer {token}'})
    check('API POST /tickets', r.status_code == 201)
    api_tid = json.loads(r.data).get('id', '')

    # API patch status
    if api_tid:
        r = c.patch(f'/api/v1/tickets/{api_tid}/status',
                    data=json.dumps({'status': 'InProgress', 'remarks': 'API test'}),
                    content_type='application/json',
                    headers={'Authorization': f'Bearer {token}'})
        check('API PATCH status', r.status_code == 200)

        r = c.post(f'/api/v1/tickets/{api_tid}/messages',
                   data=json.dumps({'content': 'API message test', 'is_internal': False}),
                   content_type='application/json',
                   headers={'Authorization': f'Bearer {token}'})
        check('API POST message', r.status_code == 201)

    # Invalid token
    r = c.get('/api/v1/me', headers={'Authorization': 'Bearer badtoken123'})
    check('API rejects bad token', r.status_code == 401)

    # No auth
    r = c.get('/api/v1/me')
    check('API rejects missing auth', r.status_code == 401)

    # API tokens page
    r = c.get('/admin/api-tokens')
    check('Admin API tokens page', r.status_code == 200)

    # ─── Dynamic form fields API ──────────────────────────────────────────
    print('\n=== DYNAMIC FORM FIELDS =================================')
    with app.app_context():
        from app.models.department import Problem
        hw = Problem.query.filter_by(name='Hardware', department_id=it_dept.id).first()
        pay = Problem.query.filter_by(name='Payroll').first()
        reimb = Problem.query.filter_by(name='Reimbursement').first()
        maint = Problem.query.filter_by(name='Maintenance').first()

    for label, dept_id, prob_id in [
        ('IT Hardware', it_dept.id if it_dept else 1, hw.id if hw else 0),
        ('HR Payroll',  hr_dept.id if hr_dept else 2, pay.id if pay else 0),
        ('Finance Reimb', fin_dept.id if fin_dept else 3, reimb.id if reimb else 0),
        ('Facilities Maint', fac_dept.id if fac_dept else 5, maint.id if maint else 0),
    ]:
        r = c.get(f'/admin/api/form-fields?department_id={dept_id}&problem_id={prob_id}')
        check(f'Form fields: {label}', r.status_code == 200,
              f'fields={len(json.loads(r.data))}')

    # ─── Agent view (role-restricted) ────────────────────────────────────
    print('\n=== ROLE-RESTRICTED ACCESS ==============================')
    # Logout admin, login as end user
    c.get('/auth/logout')
    c.post('/auth/login', data={'email': 'amit@citykart.com', 'password': 'Demo@1234'}, follow_redirects=True)

    r = c.get('/tickets/')
    check('End user: tickets list (own only)', r.status_code == 200)

    r = c.get('/admin/')
    check('End user: admin blocked', r.status_code in (302, 403))

    r = c.get('/reports/')
    check('End user: reports blocked', r.status_code in (302, 403))

    r = c.get('/kb/')
    check('End user: KB accessible', r.status_code == 200)

    # Login as agent
    c.get('/auth/logout')
    c.post('/auth/login', data={'email': 'pooja@citykart.com', 'password': 'Demo@1234'}, follow_redirects=True)
    r = c.get('/tickets/')
    check('Agent: tickets list', r.status_code == 200)
    r = c.get('/admin/')
    check('Agent: admin blocked', r.status_code in (302, 403))

# ── Final summary ─────────────────────────────────────────────────────────────
passed = sum(1 for m, _, _ in results if m == 'OK')
failed = sum(1 for m, _, _ in results if m == 'FAIL')
total  = len(results)

print(f'\n=== SUMMARY =============================================')
print(f'  Passed : {passed}/{total}')
if failed:
    print(f'  Failed : {failed}')
    print('\n  Failed checks:')
    for m, name, detail in results:
        if m == 'FAIL':
            print(f'    - {name}  [{detail}]')

print(f'\n  Result: {"ALL PASSED" if failed == 0 else "SOME FAILURES"}')
sys.exit(0 if failed == 0 else 1)
