import random

from tests import transaction_users, transaction_users_wallet, marks, common_password
from tests.base_test_case import SingleDeviceTestCase, MultipleDeviceTestCase
from views.sign_in_view import SignInView


@marks.transaction
class TestTransactionWalletSingleDevice(SingleDeviceTestCase):

    @marks.testrail_id(766)
    @marks.smoke_1
    def test_send_eth_from_wallet_to_contact(self):
        recipient = transaction_users['F_USER']
        sender = transaction_users['E_USER']
        sign_in_view = SignInView(self.driver)
        sign_in_view.recover_access(sender['passphrase'], sender['password'])
        home_view = sign_in_view.get_home_view()
        home_view.add_contact(recipient['public_key'])
        home_view.get_back_to_home_view()
        wallet_view = home_view.wallet_button.click()
        wallet_view.set_up_wallet()
        send_transaction = wallet_view.send_transaction_button.click()
        send_transaction.amount_edit_box.click()
        transaction_amount = send_transaction.get_unique_amount()
        send_transaction.amount_edit_box.set_value(transaction_amount)
        send_transaction.confirm()
        send_transaction.chose_recipient_button.click()
        send_transaction.recent_recipients_button.click()
        recent_recipient = send_transaction.element_by_text(recipient['username'])
        send_transaction.recent_recipients_button.click_until_presence_of_element(recent_recipient)
        recent_recipient.click()
        send_transaction.sign_transaction_button.click()
        send_transaction.enter_password_input.click()
        send_transaction.send_as_keyevent(sender['password'])
        send_transaction.sign_transaction_button.click()
        send_transaction.got_it_button.click()
        self.network_api.find_transaction_by_unique_amount(sender['address'], transaction_amount)

    @marks.testrail_id(767)
    @marks.smoke_1
    def test_send_eth_from_wallet_to_address(self):
        recipient = transaction_users['E_USER']
        sender = transaction_users['F_USER']
        sign_in_view = SignInView(self.driver)
        sign_in_view.recover_access(sender['passphrase'], sender['password'])
        home_view = sign_in_view.get_home_view()
        wallet_view = home_view.wallet_button.click()
        wallet_view.set_up_wallet()
        send_transaction = wallet_view.send_transaction_button.click()
        send_transaction.amount_edit_box.click()
        transaction_amount = send_transaction.get_unique_amount()
        send_transaction.amount_edit_box.set_value(transaction_amount)
        send_transaction.confirm()
        send_transaction.chose_recipient_button.click()
        send_transaction.enter_recipient_address_button.click()
        send_transaction.enter_recipient_address_input.set_value(recipient['address'])
        send_transaction.done_button.click()
        send_transaction.sign_transaction_button.click()
        send_transaction.enter_password_input.click()
        send_transaction.send_as_keyevent(sender['password'])
        send_transaction.sign_transaction_button.click()
        send_transaction.got_it_button.click()
        self.network_api.find_transaction_by_unique_amount(sender['address'], transaction_amount)

    @marks.testrail_id(1430)
    @marks.smoke_1
    def test_send_stt_from_wallet(self):
        sender = transaction_users_wallet['A_USER']
        recipient = transaction_users_wallet['B_USER']
        sign_in_view = SignInView(self.driver)
        sign_in_view.recover_access(sender['passphrase'], sender['password'])
        home_view = sign_in_view.get_home_view()
        home_view.add_contact(recipient['public_key'])
        home_view.get_back_to_home_view()
        wallet_view = home_view.wallet_button.click()
        wallet_view.set_up_wallet()
        send_transaction = wallet_view.send_transaction_button.click()
        stt_button = send_transaction.asset_by_name('STT')
        send_transaction.select_asset_button.click_until_presence_of_element(stt_button)
        stt_button.click()
        send_transaction.amount_edit_box.click()
        amount = send_transaction.get_unique_amount()
        send_transaction.amount_edit_box.set_value(amount)
        send_transaction.confirm()
        send_transaction.chose_recipient_button.click()
        send_transaction.enter_recipient_address_button.click()
        send_transaction.enter_recipient_address_input.set_value(recipient['address'])
        send_transaction.done_button.click()
        send_transaction.sign_transaction_button.click()
        send_transaction.enter_password_input.send_keys(sender['password'])
        send_transaction.sign_transaction_button.click()
        send_transaction.got_it_button.click()
        self.network_api.find_transaction_by_unique_amount(recipient['address'], amount, token=True)

    @marks.testrail_id(2164)
    def test_transaction_wrong_password_wallet(self):
        recipient = transaction_users['E_USER']
        sender = transaction_users['F_USER']
        sign_in_view = SignInView(self.driver)
        sign_in_view.recover_access(sender['passphrase'], sender['password'])
        home_view = sign_in_view.get_home_view()
        wallet_view = home_view.wallet_button.click()
        wallet_view.set_up_wallet()
        send_transaction = wallet_view.send_transaction_button.click()
        send_transaction.amount_edit_box.click()
        transaction_amount = send_transaction.get_unique_amount()
        send_transaction.amount_edit_box.set_value(transaction_amount)
        send_transaction.confirm()
        send_transaction.chose_recipient_button.click()
        send_transaction.enter_recipient_address_button.click()
        send_transaction.enter_recipient_address_input.set_value(recipient['address'])
        send_transaction.done_button.click()
        send_transaction.sign_transaction_button.click()
        send_transaction.enter_password_input.click()
        send_transaction.enter_password_input.send_keys('wrong_password')
        send_transaction.sign_transaction_button.click()
        send_transaction.find_full_text('Wrong password', 20)

    @marks.testrail_id(1452)
    def test_transaction_appears_in_history(self):
        recipient = transaction_users['B_USER']
        sign_in_view = SignInView(self.driver)
        sign_in_view.create_user()
        home_view = sign_in_view.get_home_view()
        transaction_amount = home_view.get_unique_amount()
        sender_public_key = home_view.get_public_key()
        sender_address = home_view.public_key_to_address(sender_public_key)
        home_view.home_button.click()
        self.network_api.get_donate(sender_address)
        wallet_view = home_view.wallet_button.click()
        wallet_view.set_up_wallet()
        wallet_view.wait_balance_changed_on_wallet_screen()
        send_transaction = wallet_view.send_transaction_button.click()
        send_transaction.amount_edit_box.click()
        send_transaction.amount_edit_box.set_value(transaction_amount)
        send_transaction.confirm()
        send_transaction.chose_recipient_button.click()
        send_transaction.enter_recipient_address_button.click()
        send_transaction.enter_recipient_address_input.set_value(recipient['address'])
        send_transaction.done_button.click()
        send_transaction.sign_transaction_button.click()
        send_transaction.enter_password_input.send_keys(common_password)
        send_transaction.sign_transaction_button.click()
        send_transaction.got_it_button.click()
        self.network_api.find_transaction_by_unique_amount(recipient['address'], transaction_amount)
        transactions_view = wallet_view.transaction_history_button.click()
        transactions_view.transactions_table.find_transaction(amount=transaction_amount)

    @marks.testrail_id(2163)
    def test_send_eth_from_wallet_incorrect_address(self):
        recipient = transaction_users['E_USER']
        sender = transaction_users['F_USER']
        sign_in_view = SignInView(self.driver)
        sign_in_view.recover_access(sender['passphrase'], sender['password'])
        home_view = sign_in_view.get_home_view()
        wallet_view = home_view.wallet_button.click()
        wallet_view.set_up_wallet()
        send_transaction = wallet_view.send_transaction_button.click()
        send_transaction.amount_edit_box.click()
        transaction_amount = send_transaction.get_unique_amount()
        send_transaction.amount_edit_box.set_value(transaction_amount)
        send_transaction.confirm()
        send_transaction.chose_recipient_button.click()
        send_transaction.enter_recipient_address_button.click()
        send_transaction.enter_recipient_address_input.set_value(recipient['public_key'])
        send_transaction.done_button.click()
        send_transaction.find_text_part('Invalid address:', 20)

    @marks.logcat
    @marks.testrail_id(3770)
    def test_logcat_send_transaction_from_wallet(self):
        sender = transaction_users['E_USER']
        recipient = transaction_users['F_USER']
        sign_in_view = SignInView(self.driver)
        sign_in_view.recover_access(sender['passphrase'], sender['password'])
        home_view = sign_in_view.get_home_view()
        wallet_view = home_view.wallet_button.click()
        wallet_view.set_up_wallet()
        send_transaction = wallet_view.send_transaction_button.click()
        send_transaction.amount_edit_box.click()
        transaction_amount = send_transaction.get_unique_amount()
        send_transaction.amount_edit_box.set_value(transaction_amount)
        send_transaction.confirm()
        send_transaction.chose_recipient_button.click()
        send_transaction.enter_recipient_address_button.click()
        send_transaction.enter_recipient_address_input.set_value(recipient['address'])
        send_transaction.done_button.click()
        send_transaction.sign_transaction_button.click()
        send_transaction.enter_password_input.click()
        send_transaction.send_as_keyevent(sender['password'])
        send_transaction.sign_transaction_button.click()
        send_transaction.got_it_button.click()
        send_transaction.check_no_value_in_logcat(sender['password'])

    @marks.testrail_id(3746)
    @marks.smoke_1
    def test_send_token_with_7_decimals(self):
        sender = transaction_users_wallet['A_USER']
        recipient = transaction_users_wallet['B_USER']
        sign_in_view = SignInView(self.driver)
        sign_in_view.recover_access(sender['passphrase'], sender['password'])
        home_view = sign_in_view.get_home_view()
        home_view.add_contact(recipient['public_key'])
        home_view.get_back_to_home_view()
        wallet_view = home_view.wallet_button.click()
        wallet_view.set_up_wallet()
        wallet_view.options_button.click()
        wallet_view.manage_assets_button.click()
        wallet_view.asset_checkbox_by_name('ADI').click()
        wallet_view.done_button.click()
        send_transaction = wallet_view.send_transaction_button.click()
        adi_button = send_transaction.asset_by_name('ADI')
        send_transaction.select_asset_button.click_until_presence_of_element(adi_button)
        adi_button.click()
        send_transaction.amount_edit_box.click()
        amount = '0.0%s' % random.randint(100000, 999999)
        send_transaction.amount_edit_box.set_value(amount)
        send_transaction.confirm()
        send_transaction.chose_recipient_button.click()
        send_transaction.enter_recipient_address_button.click()
        send_transaction.enter_recipient_address_input.set_value(recipient['address'])
        send_transaction.done_button.click()
        send_transaction.sign_transaction_button.click()
        send_transaction.enter_password_input.send_keys(sender['password'])
        send_transaction.sign_transaction_button.click()
        send_transaction.got_it_button.click()
        self.network_api.find_transaction_by_unique_amount(sender['address'], amount, token=True, decimals=7)

    @marks.testrail_id(3747)
    @marks.smoke_1
    def test_token_with_more_than_allowed_decimals(self):
        sender = transaction_users_wallet['A_USER']
        sign_in_view = SignInView(self.driver)
        sign_in_view.recover_access(sender['passphrase'], sender['password'])
        wallet_view = sign_in_view.wallet_button.click()
        wallet_view.set_up_wallet()
        wallet_view.options_button.click()
        wallet_view.manage_assets_button.click()
        wallet_view.asset_checkbox_by_name('ADI').click()
        wallet_view.done_button.click()
        send_transaction = wallet_view.send_transaction_button.click()
        adi_button = send_transaction.asset_by_name('ADI')
        send_transaction.select_asset_button.click_until_presence_of_element(adi_button)
        adi_button.click()
        send_transaction.amount_edit_box.click()
        amount = '0.0%s' % random.randint(1000000, 9999999)
        send_transaction.amount_edit_box.set_value(amount)
        error_text = 'Amount is too precise. Max number of decimals is 7.'
        if not send_transaction.element_by_text(error_text).is_element_displayed():
            self.errors.append('Warning about too precise amount is not shown when sending a transaction')
        send_transaction.back_button.click()
        wallet_view.receive_transaction_button.click()
        wallet_view.send_transaction_request.click()
        send_transaction.select_asset_button.click_until_presence_of_element(adi_button)
        adi_button.click()
        send_transaction.amount_edit_box.set_value(amount)
        error_text = 'Amount is too precise. Max number of decimals is 7.'
        if not send_transaction.element_by_text(error_text).is_element_displayed():
            self.errors.append('Warning about too precise amount is not shown when requesting a transaction')
        self.verify_no_errors()


@marks.transaction
class TestTransactionWalletMultipleDevice(MultipleDeviceTestCase):

    @marks.testrail_id(3761)
    @marks.smoke_1
    def test_transaction_message_sending_from_wallet(self):
        recipient = transaction_users['D_USER']
        sender = transaction_users['C_USER']
        self.create_drivers(2)
        device_1, device_2 = SignInView(self.drivers[0]), SignInView(self.drivers[1])
        home_1 = device_1.recover_access(passphrase=sender['passphrase'], password=sender['password'])
        home_2 = device_2.recover_access(passphrase=recipient['passphrase'], password=recipient['password'])

        chat_1 = home_1.add_contact(recipient['public_key'])
        chat_1.get_back_to_home_view()

        wallet_1 = home_1.wallet_button.click()
        wallet_1.set_up_wallet()
        send_transaction = wallet_1.send_transaction_button.click()
        send_transaction.amount_edit_box.click()
        amount = send_transaction.get_unique_amount()
        send_transaction.amount_edit_box.set_value(amount)
        send_transaction.confirm()
        send_transaction.chose_recipient_button.click()
        send_transaction.recent_recipients_button.click()
        send_transaction.element_by_text_part(recipient['username']).click()
        send_transaction.sign_transaction(sender['password'])

        wallet_1.home_button.click()
        home_1.get_chat_with_user(recipient['username']).click()
        if not chat_1.chat_element_by_text(amount).is_element_displayed():
            self.errors.append('Transaction message is not shown in 1-1 chat for the sender')
        chat_2 = home_2.get_chat_with_user(sender['username']).click()
        if not chat_2.chat_element_by_text(amount).is_element_displayed():
            self.errors.append('Transaction message is not shown in 1-1 chat for the recipient')
        self.verify_no_errors()
