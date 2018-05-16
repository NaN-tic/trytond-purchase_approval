==========================
Purchase Approval Scenario
==========================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> today = datetime.date.today()
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax, create_tax_code
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company

Install product_cost_plan Module::

    >>> config = activate_modules('purchase_approval')


Create company::

    >>> _ = create_company()
    >>> company = get_company()
    >>> tax_identifier = company.party.identifiers.new()
    >>> tax_identifier.type = 'eu_vat'
    >>> tax_identifier.code = 'BE0897290877'
    >>> company.party.save()

Reload the context::

    >>> User = Model.get('res.user')
    >>> Group = Model.get('res.group')
    >>> config._context = User.get_preferences(True, config.context)

Create purchase user::

    >>> purchase_user = User()
    >>> purchase_user.name = 'Purchase'
    >>> purchase_user.login = 'purchase'
    >>> purchase_user.main_company = company
    >>> purchase_group, = Group.find([('name', '=', 'Purchase')])
    >>> purchase_user.groups.append(purchase_group)
    >>> approval_group, = Group.find([('name', '=', 'Approval')])
    >>> purchase_user.groups.append(approval_group)
    >>> purchase_user.save()

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> receivable = accounts['receivable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> account_tax = accounts['tax']
    >>> account_cash = accounts['cash']

Create parties::

    >>> Party = Model.get('party.party')
    >>> supplier = Party(name='Supplier')
    >>> supplier.save()

Create payment term::

    >>> PaymentTerm = Model.get('account.invoice.payment_term')
    >>> payment_term = PaymentTerm(name='Term')
    >>> line = payment_term.lines.new(type='percent', ratio=Decimal('.5'))
    >>> delta, = line.relativedeltas
    >>> delta.days = 20
    >>> line = payment_term.lines.new(type='remainder')
    >>> delta = line.relativedeltas.new(days=40)
    >>> payment_term.save()

Create approval group:

    >>> ApprovalGroup = Model.get('approval.group')
    >>> approval_group = ApprovalGroup(name='test')
    >>> approval_group.users.append(purchase_user)
    >>> approval_group.save()

Create a purchase::

    >>> config.user = purchase_user.id
    >>> Purchase = Model.get('purchase.purchase')
    >>> purchase = Purchase()
    >>> purchase.party = supplier
    >>> purchase.payment_term = payment_term
    >>> purchase.approval_group = approval_group
    >>> purchase.invoice_method = 'manual'
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.account = expense
    >>> purchase_line.description = 'Line 1'
    >>> purchase_line.quantity = 1.0
    >>> purchase_line.unit_price = Decimal(60)
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.account = expense
    >>> purchase_line.description = 'Line 1'
    >>> purchase_line.quantity = 2.0
    >>> purchase_line.unit_price = Decimal(40)
    >>> purchase.save()
    >>> purchase.state
    u'draft'

Check approval state::

    >>> purchase.approval_requests
    []
    >>> purchase.approval_state
    u'none'

Quote purchase and check request is created::

    >>> purchase.click('quote')
    >>> len(purchase.approval_requests)
    1
    >>> purchase.approval_state
    u'pending'

Check purchase can not be confirmed::

    >>> purchase.click('confirm') # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    UserError: ...

Move to draft the purchase and check request is cancelled::

    >>> purchase.click('draft')
    >>> len(purchase.approval_requests)
    1
    >>> purchase.approval_requests[0].state
    u'cancelled'
    >>> purchase.approval_state
    u'none'

Quote purchase and check a new pending request is created::

    >>> purchase.click('quote')
    >>> purchase.state
    u'quotation'
    >>> len(purchase.approval_requests)
    2
    >>> sorted(r.state for r in purchase.approval_requests)
    [u'cancelled', u'pending']
    >>> purchase.approval_state
    u'pending'

Reject the pending request::

    >>> pending_request, = [r for r in purchase.approval_requests
    ...     if r.state == 'pending']
    >>> pending_request.click('reject')
    >>> purchase.reload()
    >>> purchase.approval_state
    u'rejected'

Move to draft the purchase and check request is still rejected::

    >>> purchase.click('draft')
    >>> len(purchase.approval_requests)
    2
    >>> sorted(r.state for r in purchase.approval_requests)
    [u'cancelled', u'rejected']
    >>> purchase.approval_state
    u'rejected'

Quote purchase and check a new pending request is created::

    >>> purchase.click('quote')
    >>> len(purchase.approval_requests)
    3
    >>> sorted(r.state for r in purchase.approval_requests)
    [u'cancelled', u'pending', u'rejected']
    >>> purchase.approval_state
    u'rejected'

Approve the pending request::

    >>> pending_request, = [r for r in purchase.approval_requests
    ...     if r.state == 'pending']
    >>> pending_request.click('approve')
    >>> purchase.reload()
    >>> purchase.approval_state
    u'approved'

Move to draft the purchase and check approved request is cancelled::

    >>> purchase.click('draft')
    >>> len(purchase.approval_requests)
    3
    >>> sorted(r.state for r in purchase.approval_requests)
    [u'cancelled', u'cancelled', u'rejected']
    >>> purchase.approval_state
    u'rejected'

Quote purchase and check a new pending request is created::

    >>> purchase.click('quote')
    >>> len(purchase.approval_requests)
    4
    >>> sorted(r.state for r in purchase.approval_requests)
    [u'cancelled', u'cancelled', u'pending', u'rejected']
    >>> purchase.approval_state
    u'rejected'

Approve the pending request::

    >>> pending_request, = [r for r in purchase.approval_requests
    ...     if r.state == 'pending']
    >>> pending_request.click('approve')
    >>> purchase.reload()
    >>> purchase.approval_state
    u'approved'

Check purchase can be confirmed::

    >>> purchase.click('confirm')
    >>> purchase.state
    u'confirmed'
