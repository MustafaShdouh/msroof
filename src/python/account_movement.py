"""Cash effects on an explicitly owned account, using existing monetary syntax."""
import re
from .money_syntax import RULES, currency, number, bare_amount

POLICY = RULES['accountMovement']
MONEY = '(?:' + currency + r'\s*' + number + '|' + number + r'\s*' + currency + '|' + bare_amount + ')'


def compile_effect(key):
    if any(p.count('{money}') > 1 or re.compile(p).groups for p in POLICY[key]):
        raise ValueError('Account templates permit one money placeholder and no captures')
    patterns = [p.replace('{money}', MONEY).replace('{owner}', POLICY['owner']) for p in POLICY[key]]
    return re.compile('|'.join('(?:'+p+')' for p in patterns), re.I | re.ASCII)


DEBIT = compile_effect('debitTemplates')
CREDIT = compile_effect('creditTemplates')


def has_account_debit(text):
    return bool(DEBIT.search(text))


def has_account_credit(text):
    return bool(CREDIT.search(text))


def bare_account_spans(text):
    """Use the same account-role templates as completion and direction."""
    for pattern in (DEBIT, CREDIT):
        for match in pattern.finditer(text):
            for group in range(1, len(match.groups()) + 1, 2):
                if match[group] is not None:
                    yield dict(start=match.start(group), end=match.end(group), contextStart=match.start(),
                               resolution='default_ambiguous' if match[group+1] else 'default_missing')
