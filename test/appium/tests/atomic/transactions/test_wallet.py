import random
import string

from support.utilities import get_merged_txs_list
from tests import marks, unique_password
from tests.base_test_case import SingleDeviceTestCase, MultipleDeviceTestCase
from tests.users import transaction_senders, basic_user, wallet_users, ens_user_ropsten, transaction_recipients, ens_user
from views.send_transaction_view import SendTransactionView
from views.sign_in_view import SignInView


@marks.transaction
class TestTransactionWalletSingleDevice(SingleDeviceTestCase):

    @marks.testrail_id(5308)
    @marks.critical
    def test_send_eth_from_wallet_to_address_incorrect_password(self):
        recipient = basic_user
        sender = transaction_senders['P']
        sign_in = SignInView(self.driver)
        home = sign_in.recover_access(sender['passphrase'], password=unique_password)
        wallet = home.wallet_button.click()
        wallet.set_up_wallet()
        wallet.accounts_status_account.click()
        transaction_amount = wallet.get_unique_amount()

        wallet.just_fyi("Checking that can't send transaction with wrong password")
        send_transaction = wallet.send_transaction_button.click()
        send_transaction.amount_edit_box.click()
        send_transaction.amount_edit_box.set_value(transaction_amount)
        send_transaction.set_recipient_address('0x%s' % recipient['address'])
        send_transaction.sign_transaction_button.click()
        send_transaction.sign_with_password.click_until_presence_of_element(send_transaction.enter_password_input)
        send_transaction.enter_password_input.click()
        send_transaction.enter_password_input.send_keys('wrong_password')
        send_transaction.sign_button.click()
        if send_transaction.element_by_text_part('Transaction sent').is_element_displayed():
            self.driver.fail('Transaction was sent with a wrong password')

        wallet.just_fyi("Fix password and sign transaction")
        send_transaction.enter_password_input.clear()
        send_transaction.enter_password_input.send_keys(unique_password)
        send_transaction.sign_button.click()
        wallet.ok_button.wait_and_click()

        wallet.just_fyi('Check that transaction is appeared in transaction history')
        wallet.find_transaction_in_history(amount=transaction_amount)

        wallet.just_fyi('Check logcat for sensitive data')
        values_in_logcat = wallet.find_values_in_logcat(password=unique_password)
        if values_in_logcat:
            self.driver.fail(values_in_logcat)

    @marks.testrail_id(6237)
    @marks.high
    def test_fetching_balance_after_offline(self):
        sender = wallet_users['E']
        sign_in_view = SignInView(self.driver)

        sign_in_view.just_fyi('Restore account with funds offline')
        sign_in_view.toggle_airplane_mode()
        sign_in_view.recover_access(sender['passphrase'])
        home_view = sign_in_view.get_home_view()
        wallet_view = home_view.wallet_button.click()
        wallet_view.set_up_wallet()

        sign_in_view.just_fyi('Go back to online and check that balance is updated')
        sign_in_view.toggle_airplane_mode()
        wallet_view.wait_balance_is_changed('ETH')
        wallet_view.scan_tokens('STT')
        initial_amount_STT = wallet_view.get_asset_amount_by_name('STT')

        sign_in_view.just_fyi('Send some tokens to other account')
        recipient = "0x" + basic_user['address']
        sending_amount = wallet_view.get_unique_amount()
        asset = 'STT'
        wallet_view.accounts_status_account.click_until_presence_of_element(wallet_view.send_transaction_button)
        wallet_view.send_transaction(asset_name=asset, amount=sending_amount, recipient=recipient,
                                     sign_transaction=True)
        sign_in_view.toggle_airplane_mode()
        self.network_api.wait_for_confirmation_of_transaction(basic_user['address'], sending_amount, token=True)

        sign_in_view.just_fyi('Change that balance is updated')
        sign_in_view.toggle_airplane_mode()

        sign_in_view.just_fyi('Check that transaction is appeared in transaction history')
        wallet_view.wait_balance_is_changed('STT', initial_amount_STT)
        wallet_view.find_transaction_in_history(amount=sending_amount, asset='STT')

    @marks.testrail_id(5461)
    @marks.medium
    def test_send_eth_from_wallet_incorrect_address(self):
        recipient = basic_user
        sender = wallet_users['B']
        sign_in_view = SignInView(self.driver)
        sign_in_view.recover_access(sender['passphrase'])
        home_view = sign_in_view.get_home_view()
        wallet_view = home_view.wallet_button.click()
        wallet_view.set_up_wallet()
        wallet_view.accounts_status_account.click()
        send_transaction = wallet_view.send_transaction_button.click()
        send_transaction.amount_edit_box.click()
        transaction_amount = send_transaction.get_unique_amount()
        send_transaction.amount_edit_box.set_value(transaction_amount)
        send_transaction.chose_recipient_button.click()
        for address in (recipient['public_key'], '0xDE709F2102306220921060314715629080E2fB77'):
            send_transaction.enter_recipient_address_input.set_value(address)
            send_transaction.enter_recipient_address_input.click()
            send_transaction.done_button.click()
            if send_transaction.set_max_button.is_element_displayed():
                self.driver.fail('Can proceed with wrong address %s in recipient' % address)

    @marks.testrail_id(5350)
    @marks.critical
    def test_send_token_with_7_decimals(self):
        sender = transaction_senders['S']
        recipient = basic_user
        sign_in_view = SignInView(self.driver)
        sign_in_view.recover_access(sender['passphrase'])
        home_view = sign_in_view.get_home_view()
        wallet_view = home_view.wallet_button.click()
        wallet_view.wait_balance_is_changed(asset='ADI', scan_tokens=True)
        wallet_view.accounts_status_account.click()
        amount = '0.000%s' % str(random.randint(100, 999)) + '1'
        wallet_view.send_transaction(amount=amount,
                                     recipient='0x%s' % recipient['address'],
                                     asset_name='ADI')
        transaction = wallet_view.find_transaction_in_history(amount=amount, asset='ADI', return_hash=True)
        self.network_api.find_transaction_by_hash(transaction)


    @marks.testrail_id(5412)
    @marks.high
    def test_insufficient_funds_wallet_positive_balance(self):
        sender = wallet_users['E']
        sign_in_view = SignInView(self.driver)
        sign_in_view.recover_access(sender['passphrase'])
        wallet_view = sign_in_view.wallet_button.click()
        wallet_view.set_up_wallet()
        [wallet_view.wait_balance_is_changed(asset) for asset in ['ETH', 'STT']]
        eth_value = wallet_view.get_asset_amount_by_name('ETH')
        stt_value = wallet_view.get_asset_amount_by_name('STT')
        if eth_value == 0 or stt_value == 0:
            self.driver.fail('No funds!')
        wallet_view.accounts_status_account.click()
        send_transaction = wallet_view.send_transaction_button.click()
        send_transaction.amount_edit_box.set_value(round(eth_value + 1))
        error_text = send_transaction.element_by_text('Insufficient funds')
        if not error_text.is_element_displayed():
            self.errors.append(
                "'Insufficient funds' error is not shown when sending %s ETH from wallet with balance %s" % (
                    round(eth_value + 1), eth_value))
        send_transaction.select_asset_button.click()
        send_transaction.asset_by_name('STT').scroll_to_element()
        send_transaction.asset_by_name('STT').click()
        send_transaction.amount_edit_box.set_value(round(stt_value + 1))
        if not error_text.is_element_displayed():
            self.errors.append(
                "'Insufficient funds' error is not shown when sending %s STT from wallet with balance %s" % (
                    round(stt_value + 1), stt_value))
        self.errors.verify_no_errors()

    @marks.testrail_id(5314)
    @marks.critical
    def test_can_see_balance_and_all_transactions_history_on_cellular(self):
        address = wallet_users['D']['address']
        passphrase = wallet_users['D']['passphrase']

        ropsten_txs = self.network_api.get_transactions(address)
        ropsten_tokens = self.network_api.get_token_transactions(address)
        expected_txs_list = get_merged_txs_list(ropsten_txs, ropsten_tokens)
        sign_in = SignInView(self.driver)
        sign_in.switch_to_mobile(before_login=True)
        home = sign_in.recover_access(passphrase=passphrase)

        wallet = home.wallet_button.click()
        wallet.set_up_wallet()
        for asset in ('ETH', 'MDS', 'STT'):
            wallet.wait_balance_is_changed(asset)
        wallet.swipe_up()
        wallet.accounts_status_account.click()
        transaction = wallet.transaction_history_button.click()
        if not wallet.element_by_translation_id("transactions-history-empty").is_element_displayed():
            self.errors.append("Transaction history was loaded automatically on mobila data!")
        wallet.pull_to_refresh()
        if wallet.element_by_translation_id("transactions-history-empty").is_element_displayed():
            wallet.pull_to_refresh()
        status_tx_number = transaction.transactions_table.get_transactions_number()
        if status_tx_number < 1:
            self.driver.fail('No transactions found')

        for n in range(status_tx_number):
            transactions_details = transaction.transactions_table.transaction_by_index(n).click()
            tx_hash = transactions_details.get_transaction_hash()
            tx_from = transactions_details.get_sender_address()
            tx_to = transactions_details.get_recipient_address()
            if tx_from != expected_txs_list[tx_hash]['from']:
                self.errors.append('Transactions senders do not match!')
            if tx_to != expected_txs_list[tx_hash]['to']:
                self.errors.append('Transactions recipients do not match!')
            transactions_details.close_button.click()

        self.errors.verify_no_errors()

    @marks.testrail_id(5429)
    @marks.medium
    def test_set_currency(self):
        sign_in_view = SignInView(self.driver)
        user_currency = 'Euro (EUR)'
        sign_in_view.create_user()
        wallet_view = sign_in_view.wallet_button.click()
        wallet_view.set_currency(user_currency)
        if not wallet_view.element_by_text_part('EUR').is_element_displayed(20):
            self.driver.fail('EUR currency is not displayed')

    @marks.testrail_id(5407)
    @marks.medium
    def test_offline_can_login_cant_send_transaction(self):
        home = SignInView(self.driver).create_user()
        wallet = home.wallet_button.click()
        wallet.set_up_wallet()
        wallet.toggle_airplane_mode()
        wallet.accounts_status_account.click_until_presence_of_element(wallet.send_transaction_button)
        send_transaction = wallet.send_transaction_button.click()
        send_transaction.set_recipient_address('0x%s' % basic_user['address'])
        send_transaction.amount_edit_box.set_value("0")
        send_transaction.confirm()
        send_transaction.sign_transaction_button.click()
        if send_transaction.sign_with_password.is_element_displayed():
            self.driver.fail("Sign transaction button is active in offline mode")
        self.driver.close_app()
        self.driver.launch_app()
        SignInView(self.driver).sign_in()
        home.home_button.wait_for_visibility_of_element()
        home.connection_offline_icon.wait_for_visibility_of_element(20)


    @marks.testrail_id(6225)
    @marks.transaction
    @marks.medium
    def test_send_funds_between_accounts_in_multiaccount_instance(self):
        sign_in_view = SignInView(self.driver)
        sign_in_view.create_user()
        wallet_view = sign_in_view.wallet_button.click()
        wallet_view.set_up_wallet()
        status_account_address = wallet_view.get_wallet_address()[2:]
        self.network_api.get_donate(status_account_address, external_faucet=True)
        wallet_view.wait_balance_is_changed()
        account_name = 'subaccount'
        wallet_view.add_account(account_name)

        wallet_view.just_fyi("Send transaction to new account")
        wallet_view.accounts_status_account.click()
        initial_balance = self.network_api.get_balance(status_account_address)

        transaction_amount = '0.003%s' % str(random.randint(10000, 99999)) + '1'
        wallet_view.send_transaction(account_name=account_name,
                                     amount=transaction_amount)
        self.network_api.wait_for_confirmation_of_transaction(status_account_address, transaction_amount)
        self.network_api.verify_balance_is_updated(str(initial_balance), status_account_address)

        wallet_view.just_fyi("Verifying previously sent transaction in new account")
        wallet_view.close_button.click()
        wallet_view.get_account_by_name(account_name).click()
        wallet_view.send_transaction_button.click()
        wallet_view.close_send_transaction_view_button.click()
        balance_after_receiving_tx = float(wallet_view.get_asset_amount_by_name('ETH'))
        expected_balance = self.network_api.get_rounded_balance(balance_after_receiving_tx, transaction_amount)
        if balance_after_receiving_tx != expected_balance:
            self.driver.fail('New account balance %s does not match expected %s after receiving a transaction' % (
                balance_after_receiving_tx, transaction_amount))

        wallet_view.just_fyi("Sending eth from new account to main account")
        updated_balance = self.network_api.get_balance(status_account_address)
        transaction_amount_1 = round(float(transaction_amount) * 0.2, 12)
        wallet_view.send_transaction(account_name=wallet_view.status_account_name,
                                                        amount=transaction_amount_1,
                                                        default_gas_price=True)
        wallet_view.close_button.click()
        sub_account_address = wallet_view.get_wallet_address(account_name)[2:]
        self.network_api.wait_for_confirmation_of_transaction(status_account_address, transaction_amount)
        self.network_api.verify_balance_is_updated(updated_balance, status_account_address)
        wallet_view.find_transaction_in_history(amount=transaction_amount)
        wallet_view.find_transaction_in_history(amount=format(float(transaction_amount_1),'.11f').rstrip('0'))

        wallet_view.just_fyi("Check transactions on subaccount")
        self.network_api.verify_balance_is_updated(updated_balance, status_account_address)

        wallet_view.just_fyi("Verify total ETH on main wallet view")
        self.network_api.wait_for_confirmation_of_transaction(status_account_address, transaction_amount_1)
        self.network_api.verify_balance_is_updated((updated_balance + transaction_amount_1), status_account_address)
        wallet_view.close_button.click()
        balance_of_sub_account = float(self.network_api.get_balance(sub_account_address)) / 1000000000000000000
        balance_of_status_account = float(self.network_api.get_balance(status_account_address)) / 1000000000000000000
        wallet_view.scan_tokens()
        total_eth_from_two_accounts = float(wallet_view.get_asset_amount_by_name('ETH'))
        expected_balance = self.network_api.get_rounded_balance(total_eth_from_two_accounts,
                                                                (balance_of_status_account + balance_of_sub_account))

        if total_eth_from_two_accounts != expected_balance:
            self.driver.fail('Total wallet balance %s != of Status account (%s) + SubAccount (%s)' % (
                total_eth_from_two_accounts, balance_of_status_account, balance_of_sub_account))

    @marks.testrail_id(6235)
    @marks.medium
    def test_can_change_account_settings(self):
        sign_in_view = SignInView(self.driver)
        sign_in_view.create_user()
        wallet_view = sign_in_view.wallet_button.click()
        wallet_view.set_up_wallet()
        status_account_address = wallet_view.get_wallet_address()
        wallet_view.get_account_options_by_name().click()

        wallet_view.just_fyi('open Account Settings screen and check that all elements are shown')
        wallet_view.account_settings_button.click()
        for text in 'On Status tree', status_account_address, "m/44'/60'/0'/0/0":
            if not wallet_view.element_by_text(text).is_element_displayed():
                self.errors.append("'%s' text is not shown on Account Settings screen!" % text)

        wallet_view.just_fyi('change account name/color and verified applied changes')
        account_name = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        wallet_view.account_name_input.clear()
        wallet_view.account_name_input.send_keys(account_name)
        wallet_view.account_color_button.select_color_by_position(1)
        wallet_view.apply_settings_button.click()
        wallet_view.element_by_text('This device').scroll_to_element()
        wallet_view.close_button.click()
        wallet_view.close_button.click()
        account_button = wallet_view.get_account_by_name(account_name)
        if not account_button.is_element_displayed():
            self.driver.fail('Account name was not changed')
        if not account_button.color_matches('multi_account_color.png'):
            self.driver.fail('Account color does not match expected')

        self.errors.verify_no_errors()

    @marks.testrail_id(6282)
    @marks.medium
    def test_can_scan_eip_681_links(self):
        sign_in_view = SignInView(self.driver)
        sign_in_view.recover_access(transaction_senders['C']['passphrase'])
        wallet_view = sign_in_view.wallet_button.click()
        wallet_view.wait_balance_is_changed()
        send_transaction_view = SendTransactionView(self.driver)

        sign_in_view.just_fyi("Setting up wallet")
        wallet_view.accounts_status_account.click_until_presence_of_element(wallet_view.send_transaction_button)
        send_transaction = wallet_view.send_transaction_button.click()
        send_transaction.set_recipient_address('0x%s' % basic_user['address'])
        send_transaction.amount_edit_box.set_value("0")
        send_transaction.confirm()
        send_transaction.sign_transaction_button.click()
        wallet_view.set_up_wallet_when_sending_tx()
        wallet_view.cancel_button.click()
        wallet_view.close_button.click()

        url_data = {
            'ens_for_receiver': {
                'url': 'ethereum:0xc55cf4b03948d7ebc8b9e8bad92643703811d162@3/transfer?address=nastya.stateofus.eth&uint256=1e-1',
                'data':{
                    'asset': 'STT',
                    'amount': '0.1',
                    'address': '0x58d8…F2ff',
                },
            },
            'gas_settings': {
                'url': 'ethereum:0x3d597789ea16054a084ac84ce87f50df9198f415@3?value=1e16&gasPrice=1000000000&gasLimit=100000',
                'data': {
                    'amount': '0.01',
                    'asset': 'ETHro',
                    'address': '0x3D59…F415',
                    'gas_limit': '100000',
                    'gas_price': '1',
                },
            },
            'payment_link': {
                'url': 'ethereum:pay-0xc55cf4b03948d7ebc8b9e8bad92643703811d162@3/transfer?address=0x3d597789ea16054a084ac84ce87f50df9198f415&uint256=1e1',
                'data': {
                    'amount': '10',
                    'asset': 'STT',
                    'address': '0x3D59…F415',
                },
            },
            'validation_amount_too_presize': {
                'url': 'ethereum:0xc55cf4b03948d7ebc8b9e8bad92643703811d162@3/transfer?address=0x101848D5C5bBca18E6b4431eEdF6B95E9ADF82FA&uint256=1e-19',
                'data': {
                    'amount': '1e-19',
                    'asset': 'STT',
                    'address': '0x1018…82FA',

                },
                'send_transaction_validation_error': 'Amount is too precise',
            },
            'validation_amount_too_big': {
                'url': 'ethereum:0x101848D5C5bBca18E6b4431eEdF6B95E9ADF82FA@3?value=1e25',
                'data': {
                    'amount': '10000000',
                    'asset': 'ETHro',
                    'address': '0x1018…82FA',

                },
                'send_transaction_validation_error': 'Insufficient funds',
            },
            'validation_wrong_chain_id': {
                'url': 'ethereum:0x101848D5C5bBca18E6b4431eEdF6B95E9ADF82FA?value=1e17',
                'error': 'Network does not match',
                'data': {
                    'amount': '0.1',
                    'asset': 'ETHro',
                    'address': '0x1018…82FA',
                },
            },
            'validation_wrong_address': {
                'url': 'ethereum:0x744d70fdbe2ba4cf95131626614a1763df805b9e@3/transfer?address=blablabla&uint256=1e10',
                'error': 'Invalid address',
            },
        }

        for key in url_data:
            wallet_view.just_fyi('Checking %s case' % key)
            wallet_view.scan_qr_button.click()
            if wallet_view.allow_button.is_element_displayed():
                wallet_view.allow_button.click()
            wallet_view.enter_qr_edit_box.scan_qr(url_data[key]['url'])
            if url_data[key].get('error'):
                if not wallet_view.element_by_text_part(url_data[key]['error']).is_element_displayed():
                    self.errors.append('Expected error %s is not shown' % url_data[key]['error'])
                wallet_view.ok_button.click()
            if url_data[key].get('data'):
                if 'gas' in key:
                    actual_data = send_transaction_view.get_values_from_send_transaction_bottom_sheet(gas=True)
                else:
                    actual_data = send_transaction_view.get_values_from_send_transaction_bottom_sheet()
                difference_in_data = url_data[key]['data'].items() - actual_data.items()
                if difference_in_data:
                    self.errors.append(
                        'In %s case returned value does not match expected in %s' % (key, repr(difference_in_data)))
                if url_data[key].get('send_transaction_validation_error'):
                    error = url_data[key]['send_transaction_validation_error']
                    if not wallet_view.element_by_text_part(error).is_element_displayed():
                        self.errors.append(
                            'Expected error %s is not shown' % error)
                if wallet_view.close_send_transaction_view_button.is_element_displayed():
                    wallet_view.close_send_transaction_view_button.wait_and_click()
                else:
                    wallet_view.cancel_button.wait_and_click()

        self.errors.verify_no_errors()

    @marks.testrail_id(6208)
    @marks.high
    def test_send_transaction_with_custom_token(self):
        contract_address = '0x101848D5C5bBca18E6b4431eEdF6B95E9ADF82FA'
        name = 'Weenus 💪'
        symbol = 'WEENUS'
        decimals = '18'
        sign_in_view = SignInView(self.driver)
        sign_in_view.recover_access(wallet_users['B']['passphrase'])
        wallet_view = sign_in_view.wallet_button.click()
        wallet_view.set_up_wallet()
        wallet_view.multiaccount_more_options.click()
        wallet_view.manage_assets_button.click()
        token_view = wallet_view.add_custom_token_button.click()
        token_view.contract_address_input.send_keys(contract_address)
        if token_view.name_input.text != name:
            self.errors.append('Name for custom token was not set')
        if token_view.symbol_input.text != symbol:
            self.errors.append('Symbol for custom token was not set')
        if token_view.decimals_input.text != decimals:
            self.errors.append('Decimals for custom token was not set')
        token_view.add_button.click()
        token_view.close_button.click()
        wallet_view.asset_by_name(symbol).scroll_to_element()
        if not wallet_view.asset_by_name(symbol).is_element_displayed():
            self.errors.append('Custom token is not shown on Wallet view')
        wallet_view.accounts_status_account.scroll_to_element(direction='up')
        wallet_view.accounts_status_account.click()
        recipient = "0x" + basic_user['address']
        amount = '0.000%s' % str(random.randint(10000, 99999)) + '1'
        wallet_view.send_transaction(asset_name=symbol, amount=amount, recipient=recipient)
        # TODO: disabled due to 10838
        # transactions_view = wallet_view.transaction_history_button.click()
        # transactions_view.transactions_table.find_transaction(amount=amount, asset=symbol)

        self.errors.verify_no_errors()

    @marks.testrail_id(6328)
    @marks.critical
    def test_send_transaction_set_recipient_options(self):
        home = SignInView(self.driver).recover_access(wallet_users['D']['passphrase'])
        nickname = 'my_some_nickname'
        account_name = 'my_acc_name'
        account_address = '0x8c2E3Cd844848E79cFd4671cE45C12F210b630d7'
        recent_add_to_fav_name = 'my_Recent_STT'
        recent_add_to_fav_address = '0x58d8c3d70ce4fa4b9fb10a665c8712238746f2ff'
        ens_status = ens_user_ropsten
        ens_other = ens_user
        basic_add_to_fav_name = 'my_basic_address'

        home.just_fyi('Add new account and new ENS contact for recipient')
        chat = home.add_contact(ens_status['ens'])
        chat.chat_options.click()
        chat.view_profile_button.click_until_presence_of_element(chat.remove_from_contacts)
        chat.set_nickname(nickname)
        chat.close_button.click()
        wallet = home.wallet_button.click()
        wallet.set_up_wallet()
        wallet.add_account(account_name=account_name)
        wallet.accounts_status_account.click()
        send_tr = wallet.send_transaction_button.click()

        send_tr.just_fyi('Set one of my accounts')
        send_tr.chose_recipient_button.click()
        send_tr.element_by_translation_id("my-accounts").click()
        send_tr.element_by_text(account_name).click()
        if send_tr.enter_recipient_address_text.text != send_tr.get_formatted_recipient_address(account_address):
            self.errors.append('Added account is not resolved as recipient')

        send_tr.just_fyi('Set contract address from recent and check smart contract error')
        send_tr.chose_recipient_button.click()
        send_tr.element_by_translation_id("recent").click()
        send_tr.element_by_text('↓ 1000 MDS').click()
        if not send_tr.element_by_translation_id("warning-sending-to-contract-descr").is_element_displayed():
            self.driver.fail('No warning is shown at attempt to set as recipient smart contract')
        send_tr.ok_button.click()
        send_tr.element_by_text('↑ 0.001 ETHro').scroll_and_click()
        send_tr.add_to_favorites(recent_add_to_fav_name)
        wallet.element_by_translation_id("recent").click()

        send_tr.just_fyi('Scan invalid QR')
        send_tr.scan_qr_code_button.click()
        send_tr.allow_button.click(1)
        wallet.enter_qr_edit_box.scan_qr('something%s' % basic_user['address'])
        if not send_tr.element_by_text_part('Invalid address').is_element_displayed(10):
            self.driver.fail('No error is shown at attempt to scan invalid address')
        wallet.ok_button.click()

        send_tr.just_fyi('Scan code, add it to favorites and recheck that it is preserved')
        send_tr.scan_qr_code_button.click()
        wallet.enter_qr_edit_box.scan_qr(basic_user['address'])
        send_tr.add_to_favorites(basic_add_to_fav_name)
        send_tr.element_by_translation_id("favourites").scroll_and_click()
        for name in (recent_add_to_fav_name, basic_add_to_fav_name):
            wallet.element_by_text(name).scroll_to_element()

        send_tr.element_by_text(recent_add_to_fav_name).scroll_and_click()
        if str(send_tr.enter_recipient_address_text.text).lower() != send_tr.get_formatted_recipient_address(
                recent_add_to_fav_address):
            self.errors.append('Recent address that was added to favourites was not resolved correctly')

        send_tr.just_fyi('Set contact')
        send_tr.chose_recipient_button.click()
        send_tr.element_by_translation_id("contacts").scroll_and_click()
        send_tr.element_by_text(nickname).scroll_and_click()
        send_tr.recipient_done.click()
        if send_tr.enter_recipient_address_text.text != send_tr.get_formatted_recipient_address(ens_status['address']):
            self.errors.append('ENS from contact is not resolved as recipient')

        send_tr.just_fyi('Set different ENS options')
        send_tr.set_recipient_address(ens_other['ens_another_domain'])
        if send_tr.enter_recipient_address_text.text != send_tr.get_formatted_recipient_address(ens_other['address']):
            self.errors.append('ENS address on another domain is not resolved as recipient')
        send_tr.set_recipient_address('%s.stateofus.eth' % ens_status['ens'])
        if send_tr.enter_recipient_address_text.text != send_tr.get_formatted_recipient_address(ens_status['address']):
            self.errors.append('ENS address on stateofus.eth is not resolved as recipient')

        send_tr.just_fyi('Check search and set address from search')
        send_tr.chose_recipient_button.click()
        send_tr.search_by_keyword(ens_status['ens'][:2])
        if not send_tr.element_by_text('@' + ens_status['ens']).is_element_displayed():
            self.errors.append('ENS address from contacts is not shown in search')
        send_tr.cancel_button.click()
        send_tr.search_by_keyword('my')
        for name in (nickname, account_name, recent_add_to_fav_name, basic_add_to_fav_name):
            if not send_tr.element_by_text(name).is_element_displayed():
                self.errors.append('%s is not shown in search when searching by namepart' % name)
        send_tr.element_by_text(basic_add_to_fav_name).click()
        if send_tr.enter_recipient_address_text.text != send_tr.get_formatted_recipient_address('0x' + basic_user['address']):
            self.errors.append('QR scanned address that was added to favourites was not resolved correctly')

        self.errors.verify_no_errors()


    @marks.testrail_id(5437)
    @marks.medium
    def test_validation_amount_errors(self):
        sender = wallet_users['C']
        sign_in_view = SignInView(self.driver)

        errors = {'send_transaction_screen': {
                    'too_precise': 'Amount is too precise. Max number of decimals is 7.',
                    'insufficient_funds': 'Insufficient funds'
                    },
                  'sending_screen': {
                    'Amount': 'Insufficient funds',
                    'Network fee': 'Not enough ETH for gas'
                    },
                  'gas_prices': {
                    '1.0000000009': 'Invalid number',
                    '0.0000000009': 'Min 1 wei',
                    '-1': 'Min 1 wei'
                   },
                  'gas_limit': {
                    '20999': 'Min 21000 units',
                    '21000.1': 'Invalid number',
                    '-21000': 'Min 21000 units'
                   }
                  }
        warning = 'Warning %s is not shown on %s'

        sign_in_view.recover_access(sender['passphrase'])
        wallet_view = sign_in_view.wallet_button.click()
        wallet_view.set_up_wallet()
        wallet_view.accounts_status_account.click()

        screen = 'send transaction screen from wallet'
        sign_in_view.just_fyi('Checking %s on %s' % (errors['send_transaction_screen']['too_precise'], screen))
        initial_amount_ADI = wallet_view.get_asset_amount_by_name('ADI')
        send_transaction = wallet_view.send_transaction_button.click()
        adi_button = send_transaction.asset_by_name('ADI')
        send_transaction.select_asset_button.click_until_presence_of_element(send_transaction.eth_asset_in_select_asset_bottom_sheet_button)
        adi_button.click()
        send_transaction.amount_edit_box.click()
        amount = '0.000%s' % str(random.randint(100000, 999999)) + '1'
        send_transaction.amount_edit_box.set_value(amount)
        if not send_transaction.element_by_text(errors['send_transaction_screen']['too_precise']).is_element_displayed():
            self.errors.append(warning % (errors['send_transaction_screen']['too_precise'], screen))

        sign_in_view.just_fyi('Checking %s on %s' % (errors['send_transaction_screen']['insufficient_funds'], screen))
        send_transaction.amount_edit_box.clear()
        send_transaction.amount_edit_box.set_value(str(initial_amount_ADI) + '1')
        if not send_transaction.element_by_text(errors['send_transaction_screen']['insufficient_funds']).is_element_displayed():
            self.errors.append(warning % (errors['send_transaction_screen']['insufficient_funds'], screen))
        wallet_view.close_send_transaction_view_button.click()
        wallet_view.close_button.click()

        screen = 'sending screen from wallet'
        sign_in_view.just_fyi('Checking %s on %s' % (errors['sending_screen']['Network fee'], screen))
        account_name = 'new'
        wallet_view.add_account(account_name)
        wallet_view.get_account_by_name(account_name).click()
        wallet_view.send_transaction_button.click()
        send_transaction.amount_edit_box.set_value('0')
        send_transaction.set_recipient_address(ens_user_ropsten['ens'])
        send_transaction.next_button.click()
        if not send_transaction.validation_error_element.is_element_displayed(10):
            self.errors.append('Validation icon is not shown when testing %s on %s' % (errors['sending_screen']['Network fee'],screen))
        send_transaction.get_validation_icon().click()
        # TODO: disbled until redo of Network fee validation element
        # if not send_transaction.element_by_text_part(errors['sending_screen']['Network fee']).is_element_displayed(10):
        #     self.errors.append(warning % (errors['sending_screen']['Network fee'],screen))
        send_transaction.sign_with_password.click()
        if send_transaction.enter_password_input.is_element_displayed():
            self.errors.append('Sign button is active when not enough ETH for gas')

        sign_in_view.just_fyi('check validation for Gas Limit and Gas Price')
        send_transaction.network_fee_button.click_until_presence_of_element(send_transaction.gas_limit_input)
        for key in errors['gas_prices']:
            send_transaction.gas_price_input.clear()
            send_transaction.gas_price_input.send_keys(key)
            if not send_transaction.element_by_text(errors['gas_prices'][key]).is_element_displayed():
                self.errors.append("With %s Gas Price value there is no %s error displayed" % (key, errors['gas_prices'][key]))
        send_transaction.gas_price_input.clear()
        send_transaction.gas_price_input.send_keys('0.1')
        for key in errors['gas_limit']:
            send_transaction.gas_limit_input.clear()
            send_transaction.gas_limit_input.send_keys(key)
            if not send_transaction.element_by_text(errors['gas_limit'][key]).is_element_displayed():
                self.errors.append("With %s Gas Limit value there is no %s error displayed" % (key, errors['gas_limit'][key]))
        send_transaction.gas_limit_input.clear()
        send_transaction.gas_limit_input.send_keys('21000')
        send_transaction.update_fee_button.click_until_absense_of_element(send_transaction.update_fee_button)
        if send_transaction.validation_error_element.is_element_displayed():
            self.errors.append('Warning about insufficient funds for gas is shown after updating transaction fee')
        send_transaction.cancel_button.click()

        screen = 'sending screen from DApp'
        sign_in_view.just_fyi('Checking %s on %s' % (errors['sending_screen']['Network fee'], screen))
        home_view = wallet_view.home_button.click()
        dapp_view = sign_in_view.dapp_tab_button.click()
        dapp_view.select_account_button.click()
        dapp_view.select_account_by_name(account_name).wait_for_element(30)
        dapp_view.select_account_by_name(account_name).click()
        status_test_dapp = home_view.open_status_test_dapp()
        status_test_dapp.wait_for_d_aap_to_load()
        status_test_dapp.transactions_button.click_until_presence_of_element(
            status_test_dapp.send_two_tx_in_batch_button)
        status_test_dapp.send_two_tx_in_batch_button.click()
        if not send_transaction.validation_error_element.is_element_displayed(10):
            self.errors.append(warning % (errors['sending_screen']['Network fee'],screen))
        self.errors.verify_no_errors()


class TestTransactionWalletMultipleDevice(MultipleDeviceTestCase):

    @marks.testrail_id(6330)
    @marks.medium
    def test_can_send_all_tokens_via_max_option(self):
        sender = transaction_senders['V']
        receiver = transaction_recipients['K']
        self.create_drivers(2)
        device_1, device_2 = SignInView(self.drivers[0]), SignInView(self.drivers[1])

        device_1_home, device_2_home = device_1.recover_access(sender['passphrase']), \
                                       device_2.recover_access(receiver['passphrase'])

        wallet_view_serder = device_1_home.wallet_button.click()
        wallet_view_serder.set_up_wallet()
        wallet_view_receiver = device_2_home.wallet_button.click()
        wallet_view_receiver.set_up_wallet()

        if wallet_view_receiver.asset_by_name('STT').is_element_present(10):
            initial_balance = wallet_view_receiver.get_asset_amount_by_name("STT")
        else:
            initial_balance = '0'

        device_1.just_fyi("Sending token amount to device who will use Set Max option for token")
        amount = '0.012345678912345678'
        wallet_view_serder.accounts_status_account.click()
        wallet_view_serder.send_transaction(asset_name='STT', amount=amount, recipient=receiver['address'])
        wallet_view_receiver.wait_balance_is_changed(asset='STT', initial_balance=initial_balance, scan_tokens=True)
        wallet_view_receiver.accounts_status_account.click()

        device_1.just_fyi("Send all tokens via Set Max option")
        send_transaction_view = wallet_view_receiver.send_transaction_button.click()
        send_transaction_view.select_asset_button.click()
        asset_name = 'STT'
        asset_button = send_transaction_view.asset_by_name(asset_name)
        send_transaction_view.select_asset_button.click_until_presence_of_element(
            send_transaction_view.eth_asset_in_select_asset_bottom_sheet_button)
        asset_button.click()
        send_transaction_view.set_max_button.click()
        send_transaction_view.set_recipient_address(sender['address'])
        send_transaction_view.sign_transaction_button.click()
        send_transaction_view.sign_transaction()
        wallet_view_receiver.close_button.click()
        initial_balance = float(initial_balance) + float(amount)
        wallet_view_receiver.wait_balance_is_changed(asset='STT', initial_balance=str(initial_balance), scan_tokens=True)
