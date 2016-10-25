# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from datetime import datetime

from trytond.model import ModelView, Workflow, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval

__all__ = ['Purchase']


class Purchase:
    __name__ = 'purchase.purchase'
    __metaclass__ = PoolMeta
    approval_group = fields.Many2One('approval.group', 'Approval Group',
        domain=[
            ['OR',
                ('model', '=', None),
                ('model.model', '=', 'purchase.purchase')],
            ],
        states={
            'required': ~Eval('state').in_(['draft', 'cancel']),
            'readonly': Eval('state') != 'draft',
            }, depends=['state'])
    approval_requests = fields.One2Many('approval.request', 'document',
        'Approval Requests', readonly=True)
    approval_state = fields.Selection([
            ('none', 'None'),
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ], 'Approval State', readonly=True, required=True)
    blockers = fields.Function(fields.Many2Many('res.user', None, None,
            'Blockers'),
        'get_blockers', searcher='search_blockers')

    @classmethod
    def __setup__(cls):
        super(Purchase, cls).__setup__()
        cls._error_messages.update({
                'missing_approval': (
                    'The purchase "%s" cannot be confirmed because it '
                    'doesn\'t have any accepted Approval Request.'),
                })

    @staticmethod
    def default_approval_state():
        return 'none'

    def get_approval_state(self):
        '''
        Return the approval state for the purchase.
        '''
        if not self.approval_requests or all(r.state == 'cancelled'
                for r in self.approval_requests):
            return 'none'
        state = 'pending'
        for request in self.approval_requests:
            if request.state == 'approved':
                return 'approved'
            elif request.state == 'rejected':
                state = 'rejected'
        return state

    @classmethod
    def set_approval_state(cls, purchases):
        '''
        Set the approval state.
        '''
        to_write = []
        for purchase in purchases:
            state = purchase.get_approval_state()
            if purchase.approval_state != state:
                to_write.extend(([purchase], {
                            'approval_state': state,
                            }))
        if to_write:
            cls.write(*to_write)

    def get_blockers(self, name):
        blockers = set()
        for request in self.approval_requests:
            for user in request.group.users:
                blockers.add(user.id)
        return list(blockers)

    @classmethod
    def search_blockers(cls, name, clause):
        return [('approval_requests.group.users.id',) + tuple(clause[1:])]

    @classmethod
    @ModelView.button
    @Workflow.transition('draft')
    def draft(cls, purchases):
        pool = Pool()
        Request = pool.get('approval.request')
        super(Purchase, cls).draft(purchases)
        if purchases:
            requests = Request.search([
                    ('document.id', 'in', [p.id for p in purchases],
                        'purchase.purchase'),
                    ('state', 'in', ('pending', 'approved')),
                    ])
            if requests:
                Request.cancel(requests)

    @classmethod
    @ModelView.button
    @Workflow.transition('quotation')
    def quote(cls, purchases):
        pool = Pool()
        Request = pool.get('approval.request')
        super(Purchase, cls).quote(purchases)
        to_create = []
        for purchase in purchases:
            if not purchase.approval_group:
                continue  # it will failg the states
            request = purchase._get_approval_request()
            if request:
                to_create.append(request._save_values)
        if to_create:
            Request.create(to_create)

    def _get_approval_request(self):
        pool = Pool()
        Request = pool.get('approval.request')
        return Request(
            document=self,
            group=self.approval_group,
            request_date=datetime.now())

    @classmethod
    @ModelView.button
    @Workflow.transition('confirmed')
    def confirm(cls, purchases):
        for purchase in purchases:
            if purchase.approval_state != 'approved':
                cls.raise_user_error('missing_approval', (purchase.rec_name,))
        super(Purchase, cls).confirm(purchases)

    @classmethod
    def copy(cls, purchases, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default['approval_requests'] = None
        default['approval_state'] = 'none'
        return super(Purchase, cls).copy(purchases, default=default)
