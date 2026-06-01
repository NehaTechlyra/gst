"""
Test file for Bank Reconciliation feature
Run tests with: python manage.py test bank.tests
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from datetime import date

from bank.models import Bank, BankReconciliation, BankStatementEntry, SystemEntry
from bank.reconciliation_utils import BankStatementParser, ReconciliationMatcher
from company_settings.models import CompanyBankAccount
from company.models import Company
from journal.models import JournalEntry, JournalLine
from chart_of_accounts.models import ChartOfAccounts


class BankReconciliationParserTestCase(TestCase):
    """Test CSV parsing functionality"""
    
    def test_parse_valid_csv(self):
        """Test parsing valid CSV content"""
        csv_content = """Date,Description,Amount
2026-03-01,Opening Balance,50000
2026-03-05,Customer Deposit,15000
2026-03-10,Vendor Payment,-8500
"""
        parser = BankStatementParser(csv_content.encode())
        
        self.assertEqual(len(parser.entries), 3)
        self.assertEqual(parser.entries[0]['amount'], Decimal('50000'))
        self.assertFalse(parser.errors)
    
    def test_parse_various_date_formats(self):
        """Test parsing different date formats"""
        csv_content = """Date,Description,Amount
2026-03-01,Format1,1000
03-01-2026,Format2,2000
03/01/2026,Format3,3000
"""
        parser = BankStatementParser(csv_content.encode())
        
        self.assertEqual(len(parser.entries), 3)
    
    def test_parse_with_currency_symbols(self):
        """Test parsing amounts with currency symbols"""
        csv_content = """Date,Description,Amount
2026-03-01,Test,$1,000.00
"""
        parser = BankStatementParser(csv_content.encode())
        
        self.assertEqual(len(parser.entries), 1)
        self.assertEqual(parser.entries[0]['amount'], Decimal('1000.00'))


class BankReconciliationLogicTestCase(TestCase):
    """Test reconciliation matching logic"""
    
    def setUp(self):
        """Set up test data"""
        # Create user
        self.user = User.objects.create_user(username='testuser', password='pass123')
        
        # Create company
        self.company = Company.objects.create(
            name='Test Company',
            legal_name='Test Company Ltd'
        )
        
        # Create bank
        self.bank = Bank.objects.create(bank_name='Test Bank')
        
        # Create bank account
        self.account = CompanyBankAccount.objects.create(
            company=self.company,
            bank=self.bank,
            account_name='Test Account',
            account_number='1234567890'
        )
        
        # Create reconciliation
        self.reconciliation = BankReconciliation.objects.create(
            company_bank_account=self.account,
            statement_start_date=date(2026, 3, 1),
            statement_end_date=date(2026, 3, 31),
            statement_balance=Decimal('50000.00'),
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_create_statement_entry(self):
        """Test creating bank statement entry"""
        entry = BankStatementEntry.objects.create(
            reconciliation=self.reconciliation,
            transaction_date=date(2026, 3, 5),
            description='Test Deposit',
            amount=Decimal('15000.00')
        )
        
        self.assertEqual(entry.reconciliation, self.reconciliation)
        self.assertEqual(entry.amount, Decimal('15000.00'))
        self.assertFalse(entry.is_matched)
    
    def test_reconciliation_balance_calculation(self):
        """Test balance calculation"""
        # Create multiple entries
        BankStatementEntry.objects.create(
            reconciliation=self.reconciliation,
            transaction_date=date(2026, 3, 5),
            description='Deposit',
            amount=Decimal('15000.00')
        )
        
        BankStatementEntry.objects.create(
            reconciliation=self.reconciliation,
            transaction_date=date(2026, 3, 10),
            description='Withdrawal',
            amount=Decimal('-5000.00')
        )
        
        # Total should be 10000
        total = sum(e.amount for e in self.reconciliation.statement_entries.all())
        self.assertEqual(total, Decimal('10000.00'))
    
    def test_gap_calculation(self):
        """Test reconciliation gap calculation"""
        self.reconciliation.statement_balance = Decimal('50000.00')
        self.reconciliation.system_balance = Decimal('45000.00')
        gap = self.reconciliation.statement_balance - self.reconciliation.system_balance
        
        self.assertEqual(gap, Decimal('5000.00'))
    
    def test_is_reconciled_property(self):
        """Test is_reconciled property"""
        self.reconciliation.reconciliation_gap = Decimal('0.00')
        self.assertTrue(self.reconciliation.is_reconciled)
        
        self.reconciliation.reconciliation_gap = Decimal('100.00')
        self.assertFalse(self.reconciliation.is_reconciled)


class BankReconciliationPermissionTestCase(TestCase):
    """Test permission handling"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(username='testuser', password='pass123')
        self.other_user = User.objects.create_user(username='otheruser', password='pass123')
        self.client = Client()
    
    def test_login_required(self):
        """Test that login is required"""
        response = self.client.get(reverse('reconciliation_list'))
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_logged_in_user_access(self):
        """Test that logged-in users can access"""
        self.client.login(username='testuser', password='pass123')
        response = self.client.get(reverse('reconciliation_list'))
        
        self.assertEqual(response.status_code, 200)
