# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool

from . import approval
from . import purchase


def register():
    Pool.register(
        approval.ApprovalRequest,
        purchase.Purchase,
        module='purchase_approval', type_='model')
