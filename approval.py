# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from functools import wraps

from trytond.model import ModelView, Workflow
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.i18n import gettext
from trytond.exceptions import UserError

__all__ = ['ApprovalRequest']


def set_purchase_approval_state(func):
    @wraps(func)
    def wrapper(cls, requests):
        pool = Pool()
        Purchase = pool.get('purchase.purchase')
        with Transaction().set_context(_check_access=False):
            purchases = [r.document for r in cls.browse(requests)
                if isinstance(r.document, Purchase)]
        func(cls, requests)
        with Transaction().set_context(_check_access=False):
            if purchases:
                Purchase.set_approval_state(purchases)
    return wrapper


class ApprovalRequest(metaclass=PoolMeta):
    __name__ = 'approval.request'

    @classmethod
    def __setup__(cls):
        super(ApprovalRequest, cls).__setup__()

    @classmethod
    def _get_document(cls):
        return super(ApprovalRequest, cls)._get_document() + [
            'purchase.purchase',
            ]

    @classmethod
    @ModelView.button
    @Workflow.transition('approved')
    @set_purchase_approval_state
    def approve(cls, requests):
        pool = Pool()
        Purchase = pool.get('purchase.purchase')
        for request in requests:
            if (isinstance(request.document, Purchase)
                    and request.document.state != 'quotation'):
                raise UserError(gettext(
                        'purchase_approval.approve_no_quotation',
                        request=request.rec_name,
                        purchase=request.document.rec_name))
        super(ApprovalRequest, cls).approve(requests)

    @classmethod
    @ModelView.button
    @Workflow.transition('rejected')
    @set_purchase_approval_state
    def reject(cls, requests):
        pool = Pool()
        Purchase = pool.get('purchase.purchase')
        for request in requests:
            if (isinstance(request.document, Purchase)
                    and request.document.state != 'quotation'):
                raise UserError(gettext('purchase_approval.reject_no_quotation',
                    request=request.rec_name,
                    purchase=request.document.rec_name))
        super(ApprovalRequest, cls).reject(requests)

    @classmethod
    @ModelView.button
    @Workflow.transition('cancelled')
    @set_purchase_approval_state
    def cancel(cls, requests):
        pool = Pool()
        Purchase = pool.get('purchase.purchase')
        for request in requests:
            if (isinstance(request.document, Purchase)
                    and request.document.state not in ('draft', 'quotation')):
                raise UserError(gettext(
                        'purchase_approval.cancel_no_quotation_draft_purchase',
                        request=request.rec_name,
                        purchase=request.document.rec_name))
        super(ApprovalRequest, cls).cancel(requests)

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Purchase = pool.get('purchase.purchase')
        purchases = []
        for vals in vlist:
            document = vals.get('document')
            if isinstance(document, Purchase):
                purchases.append(document)
            elif (isinstance(document, str)
                    and document.startswith('purchase.purchase,')):
                purchases.append(Purchase(int(document[18:])))
        res = super(ApprovalRequest, cls).create(vlist)
        if purchases:
            Purchase.set_approval_state(purchases)
        return res

    @classmethod
    def write(cls, *args):
        pool = Pool()
        Purchase = pool.get('purchase.purchase')
        purchases = []
        actions = iter(args)
        for records, values in zip(actions, actions):
            purchases += [r.document for r in records
                if isinstance(r.document, Purchase)]
            if 'document' in values:
                document = values['document']
                if isinstance(document, Purchase):
                    purchases.append(document)
                elif (isinstance(document, str)
                        and document.startswith('purchase.purchase,')):
                    purchases.append(Purchase(int(document[18:])))
        super(ApprovalRequest, cls).write(*args)
        if purchases:
            Purchase.set_approval_state(purchases)

    @classmethod
    @set_purchase_approval_state
    def delete(cls, requests):
        super(ApprovalRequest, cls).delete(requests)
