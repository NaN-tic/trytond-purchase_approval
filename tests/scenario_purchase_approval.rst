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

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install purchase_approval::

    >>> Module = Model.get('ir.module.module')
    >>> purchase_module, = Module.find([('name', '=', 'purchase_approval')])
    >>> Module.install([purchase_module.id], config.context)
    >>> Wizard('ir.module.module.install_upgrade').execute('upgrade')

Create company::

    >>> Currency = Model.get('currency.currency')
    >>> CurrencyRate = Model.get('currency.currency.rate')
    >>> currencies = Currency.find([('code', '=', 'USD')])
    >>> if not currencies:
    ...     currency = Currency(name='U.S. Dollar', symbol='$', code='USD',
    ...         rounding=Decimal('0.01'), mon_grouping='[3, 3, 0]',
    ...         mon_decimal_point='.', mon_thousands_sep=',')
    ...     currency.save()
    ...     CurrencyRate(date=today + relativedelta(month=1, day=1),
    ...         rate=Decimal('1.0'), currency=currency).save()
    ... else:
    ...     currency, = currencies
    >>> Company = Model.get('company.company')
    >>> Party = Model.get('party.party')
    >>> company_config = Wizard('company.company.config')
    >>> company_config.execute('company')
    >>> company = company_config.form
    >>> party = Party(name='Dunder Mifflin')
    >>> party.save()
    >>> company.party = party
    >>> company.currency = currency
    >>> company_config.execute('add')
    >>> company, = Company.find([])

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

    >>> AccountTemplate = Model.get('account.account.template')
    >>> Account = Model.get('account.account')
    >>> Journal = Model.get('account.journal')
    >>> account_template, = AccountTemplate.find([('parent', '=', None)])
    >>> create_chart = Wizard('account.create_chart')
    >>> create_chart.execute('account')
    >>> create_chart.form.account_template = account_template
    >>> create_chart.form.company = company
    >>> create_chart.execute('create_account')
    >>> receivable, = Account.find([
    ...         ('kind', '=', 'receivable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> payable, = Account.find([
    ...         ('kind', '=', 'payable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> expense, = Account.find([
    ...         ('kind', '=', 'expense'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> create_chart.form.account_receivable = receivable
    >>> create_chart.form.account_payable = payable
    >>> create_chart.execute('create_properties')

Create parties::

    >>> Party = Model.get('party.party')
    >>> supplier = Party(name='Supplier')
    >>> supplier.save()

Create payment term::

    >>> PaymentTerm = Model.get('account.invoice.payment_term')
    >>> PaymentTermLine = Model.get('account.invoice.payment_term.line')
    >>> payment_term = PaymentTerm(name='Direct')
    >>> payment_term_line = PaymentTermLine(type='remainder', days=0)
    >>> payment_term.lines.append(payment_term_line)
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

    >>> purchase.click('confirm')
    Traceback (most recent call last):
        ...
    UserError: ('UserError', (u'The purchase "1" cannot be confirmed because it doesn\'t have any accepted Approval Request.', ''))

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
