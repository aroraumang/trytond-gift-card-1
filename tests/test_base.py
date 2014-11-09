# -*- coding: utf-8 -*-
"""
    test_base

    :copyright: (C) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import sys
import os
DIR = os.path.abspath(os.path.normpath(os.path.join(
    __file__, '..', '..', '..', '..', '..', 'trytond'
)))
if os.path.isdir(DIR):
    sys.path.insert(0, os.path.dirname(DIR))
from datetime import date, datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from trytond.tests.test_tryton import POOL, USER
import trytond.tests.test_tryton
from trytond.transaction import Transaction
from nereid.testing import NereidTestCase


class TestBase(NereidTestCase):
    """
    Base Test Case for gift card
    """

    def setUp(self):
        """
        Set up data used in the tests.
        this method is called before each test function execution.
        """
        trytond.tests.test_tryton.install_module('gift_card')

        self.Currency = POOL.get('currency.currency')
        self.Company = POOL.get('company.company')
        self.Party = POOL.get('party.party')
        self.User = POOL.get('res.user')
        self.Country = POOL.get('country.country')
        self.SubDivision = POOL.get('country.subdivision')
        self.Sequence = POOL.get('ir.sequence')
        self.Account = POOL.get('account.account')
        self.GiftCard = POOL.get('gift_card.gift_card')
        self.SaleShop = POOL.get('sale.shop')
        self.PriceList = POOL.get('product.price_list')
        self.StockLocation = POOL.get('stock.location')
        self.NereidWebsite = POOL.get('nereid.website')
        self.NereidUser = POOL.get('nereid.user')
        self.Language = POOL.get('ir.lang')
        self.Locale = POOL.get('nereid.website.locale')

        self.templates = {
            'shopping-cart.jinja':
                'Cart:{{ cart.id }},{{get_cart_size()|round|int}},'
                '{{cart.sale.total_amount}}',
            'product.jinja':
                '{{ product.name }}',
            'catalog/gift-card.html':
                '{{ product.id }}',
        }

    def _create_fiscal_year(self, date_=None, company=None):
        """
        Creates a fiscal year and requried sequences
        """
        FiscalYear = POOL.get('account.fiscalyear')
        Sequence = POOL.get('ir.sequence')
        SequenceStrict = POOL.get('ir.sequence.strict')
        Company = POOL.get('company.company')

        if date_ is None:
            date_ = datetime.utcnow().date()

        if company is None:
            company, = Company.search([], limit=1)

        invoice_sequence, = SequenceStrict.create([{
            'name': '%s' % date.year,
            'code': 'account.invoice',
            'company': company,
        }])
        fiscal_year, = FiscalYear.create([{
            'name': '%s' % date_.year,
            'start_date': date_ + relativedelta(month=1, day=1),
            'end_date': date_ + relativedelta(month=12, day=31),
            'company': company,
            'post_move_sequence': Sequence.create([{
                'name': '%s' % date_.year,
                'code': 'account.move',
                'company': company,
            }])[0],
            'out_invoice_sequence': invoice_sequence,
            'in_invoice_sequence': invoice_sequence,
            'out_credit_note_sequence': invoice_sequence,
            'in_credit_note_sequence': invoice_sequence,
        }])
        FiscalYear.create_period([fiscal_year])
        return fiscal_year

    def _create_coa_minimal(self, company):
        """Create a minimal chart of accounts
        """
        AccountTemplate = POOL.get('account.account.template')
        Account = POOL.get('account.account')

        account_create_chart = POOL.get(
            'account.create_chart', type="wizard"
        )

        account_template, = AccountTemplate.search(
            [('parent', '=', None)]
        )

        session_id, _, _ = account_create_chart.create()
        create_chart = account_create_chart(session_id)
        create_chart.account.account_template = account_template
        create_chart.account.company = company
        create_chart.transition_create_account()

        receivable, = Account.search([
            ('kind', '=', 'receivable'),
            ('company', '=', company),
        ])
        payable, = Account.search([
            ('kind', '=', 'payable'),
            ('company', '=', company),
        ])
        create_chart.properties.company = company
        create_chart.properties.account_receivable = receivable
        create_chart.properties.account_payable = payable
        create_chart.transition_create_properties()

    def _get_account_by_kind(self, kind, company=None, silent=True):
        """Returns an account with given spec

        :param kind: receivable/payable/expense/revenue
        :param silent: dont raise error if account is not found
        """
        Account = POOL.get('account.account')
        Company = POOL.get('company.company')

        if company is None:
            company, = Company.search([], limit=1)

        accounts = Account.search([
            ('kind', '=', kind),
            ('company', '=', company)
        ], limit=1)
        if not accounts and not silent:
            raise Exception("Account not found")
        return accounts[0] if accounts else False

    def _create_payment_term(self):
        """Create a simple payment term with all advance
        """
        PaymentTerm = POOL.get('account.invoice.payment_term')

        return PaymentTerm.create([{
            'name': 'Direct',
            'lines': [('create', [{'type': 'remainder'}])]
        }])[0]

    def setup_defaults(self):
        """
        Setup the defaults
        """
        User = POOL.get('res.user')
        Uom = POOL.get('product.uom')

        self.usd, = self.Currency.create([{
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        }])

        with Transaction().set_context(company=None):
            self.party, = self.Party.create([{
                'name': 'Openlabs',
                'addresses': [('create', [{
                    'city': 'Melbourne',
                }])],
            }])
            self.company, = self.Company.create([{
                'party': self.party.id,
                'currency': self.usd
            }])

        User.write(
            [User(USER)], {
                'main_company': self.company.id,
                'company': self.company.id,
            }
        )

        self._create_coa_minimal(company=self.company.id)
        self.account_revenue = self._get_account_by_kind('revenue')
        self.account_expense = self._get_account_by_kind('expense')
        self.payment_term = self._create_payment_term()
        self._create_fiscal_year()

        self.party1, = self.Party.create([{
            'name': 'Test party',
            'addresses': [('create', [{
                'city': 'Melbourne',
            }])],
        }])
        self.party2, = self.Party.create([{
            'name': 'Guest party',
            'addresses': [('create', [{
                'city': 'Noida',
            }])],
        }])

        self.uom, = Uom.search([('name', '=', 'Unit')])

        self.product = self.create_product()

        # Create a Sale Shop
        self.price_list, = self.PriceList.create([{
            'name': 'Test Price List',
            'company': self.company.id,
        }])
        with Transaction().set_context(company=self.company.id):
            self.shop, = self.SaleShop.create([{
                'name': 'Test Shop',
                'address': self.company.party.addresses[0].id,
                'payment_term': self.payment_term,
                'price_list': self.price_list,
                'warehouse': self.StockLocation.search([
                    ('type', '=', 'warehouse')
                ])[0],
            }])

        User.write(
            [User(USER)], {
                'shops': [('add', [self.shop.id])],
                'shop': self.shop.id,
            }
        )

        # Create users and assign the pricelists to them
        self.guest_user, = self.NereidUser.create([{
            'party': self.party2.id,
            'display_name': 'Guest User',
            'email': 'guest@openlabs.co.in',
            'password': 'password',
            'company': self.company.id,
        }])
        self.registered_user, = self.NereidUser.create([{
            'party': self.party1.id,
            'display_name': 'Registered User',
            'email': 'email@example.com',
            'password': 'password',
            'company': self.company.id,
        }])
        en_us, = self.Language.search([('code', '=', 'en_US')])
        self.locale_en_us, = self.Locale.create([{
            'code': 'en_US',
            'language': en_us.id,
            'currency': self.usd.id,
        }])
        self.create_website()

    def create_product(
        self, type='goods', mode='physical', is_gift_card=False,
        allow_open_amount=False
    ):
        """
        Create default product
        """
        Template = POOL.get('product.template')

        values = {
            'name': 'product',
            'type': type,
            'list_price': Decimal('20'),
            'cost_price': Decimal('5'),
            'default_uom': self.uom.id,
            'salable': True,
            'sale_uom': self.uom.id,
            'account_revenue': self.account_revenue.id,
            'products': [
                ('create', [{
                    'code': 'Test Product'
                }])
            ]
        }

        if is_gift_card:
            values.update({
                'is_gift_card': True,
                'gift_card_delivery_mode': mode,
            })

            if not allow_open_amount:
                values.update({
                    'gift_card_prices': [
                        ('create', [{
                            'price': 500,
                        }, {
                            'price': 600,
                        }])
                    ]
                })
            else:
                values.update({
                    'allow_open_amount': True,
                    'gc_min': 100,
                    'gc_max': 400
                })

        return Template.create([values])[0].products[0]

    def create_payment_gateway(self, method='gift_card'):
        """
        Create payment gateway
        """
        PaymentGateway = POOL.get('payment_gateway.gateway')
        Journal = POOL.get('account.journal')

        today = date.today()

        sequence, = self.Sequence.create([{
            'name': 'PM-%s' % today.year,
            'code': 'account.journal',
            'company': self.company.id
        }])

        self.account_cash, = self.Account.search([
            ('kind', '=', 'other'),
            ('name', '=', 'Main Cash'),
            ('company', '=', self.company.id)
        ])

        self.cash_journal, = Journal.create([{
            'name': 'Cash Journal',
            'code': 'cash',
            'type': 'cash',
            'credit_account': self.account_cash.id,
            'debit_account': self.account_cash.id,
            'sequence': sequence.id,
        }])

        gateway = PaymentGateway(
            name='Gift Card',
            journal=self.cash_journal,
            provider='self',
            method=method,
        )
        gateway.save()
        return gateway

    def create_website(self):
        """
        Creates a website. Since the fields required to make this could
        change depending on modules installed and this is a base test case
        the creation is separated to another method
        """
        return self.NereidWebsite.create([{
            'name': 'localhost',
            'shop': self.shop,
            'company': self.company.id,
            'application_user': USER,
            'default_locale': self.locale_en_us.id,
            'guest_user': self.guest_user,
        }])

    def login(self, client, username, password, assert_=True):
        """
        Tries to login.
        .. note::
            This method MUST be called within a context
        :param client: Instance of the test client
        :param username: The username, usually email
        :param password: The password to login
        :param assert_: Boolean value to indicate if the login has to be
                        ensured. If the login failed an assertion error would
                        be raised
        """
        rv = client.post(
            '/login', data={
                'email': username,
                'password': password,
            }
        )
        if assert_:
            self.assertEqual(rv.status_code, 302)
        return rv
