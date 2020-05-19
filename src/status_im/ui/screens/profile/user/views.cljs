(ns status-im.ui.screens.profile.user.views
  (:require [re-frame.core :as re-frame]
            [reagent.core :as reagent]
            [status-im.i18n :as i18n]
            [quo.core :as quo]
            [status-im.ui.components.colors :as colors]
            [status-im.multiaccounts.core :as multiaccounts]
            [status-im.ui.components.common.common :as components.common]
            [status-im.ui.components.copyable-text :as copyable-text]
            [status-im.ui.components.list-selection :as list-selection]
            [status-im.ui.components.qr-code-viewer.views :as qr-code-viewer]
            [status-im.ui.components.react :as react]
            [status-im.ui.screens.profile.user.styles :as styles]
            [status-im.utils.platform :as platform]
            [status-im.utils.config :as config]
            [status-im.utils.gfycat.core :as gfy]
            [status-im.utils.universal-links.core :as universal-links]
            [status-im.ui.components.profile-header.view :as profile-header])
  (:require-macros [status-im.utils.views :as views]))

(views/defview share-chat-key []
  (views/letsubs [{:keys [address ens-name]}     [:popover/popover]
                  width                          (reagent/atom nil)]
    (let [link (universal-links/generate-link :user :external (or ens-name address))]
      [react/view {:on-layout #(reset! width (-> ^js % .-nativeEvent .-layout .-width))}
       [react/view {:style {:padding-top 16 :padding-horizontal 16}}
        (when @width
          [qr-code-viewer/qr-code-view (- @width 32) address])
        (when ens-name
          [react/view
           [copyable-text/copyable-text-view
            {:label           :t/ens-username
             :container-style {:margin-top 12 :margin-bottom 4}
             :copied-text     ens-name}
            [react/nested-text
             {:style               {:line-height 22 :font-size 15
                                    :font-family "monospace"}
              :accessibility-label :ens-username}
             ens-name]]
           [react/view {:height           1 :margin-top 12 :margin-horizontal -16
                        :background-color colors/gray-lighter}]])
        [copyable-text/copyable-text-view
         {:label           :t/chat-key
          :container-style {:margin-top 12 :margin-bottom 4}
          :copied-text     address}
         [react/text {:number-of-lines     1
                      :ellipsize-mode      :middle
                      :accessibility-label :chat-key
                      :style               {:line-height 22 :font-size 15
                                            :font-family "monospace"}}
          address]]]
       [react/view styles/share-link-button
        [quo/button
         {:on-press            #(list-selection/open-share {:message link})
          :accessibility-label :share-my-contact-code-button}
         (i18n/label :t/share-link)]]])))

(defn tribute-to-talk-item
  [opts]
  [quo/list-item
   (merge {:title               (i18n/label :t/tribute-to-talk)
           :accessibility-label :notifications-button
           :on-press            #(re-frame/dispatch
                                  [:tribute-to-talk.ui/menu-item-pressed])}
          opts)])

(defn content []
  (let [{:keys [preferred-name
                mnemonic
                keycard-pairing
                notifications-enabled?]}
        @(re-frame/subscribe [:multiaccount])
        active-contacts-count @(re-frame/subscribe [:contacts/active-count])
        tribute-to-talk       @(re-frame/subscribe [:tribute-to-talk/profile])
        registrar             @(re-frame/subscribe [:ens.stateofus/registrar])]
    [:<>
     [quo/list-item
      (cond-> {:title                (or (when registrar preferred-name)
                                         (i18n/label :t/ens-usernames))
               :subtitle             (if registrar
                                       (if preferred-name
                                         (i18n/label :t/ens-your-your-name)
                                         (i18n/label :t/ens-usernames-details))
                                       (i18n/label :t/ens-network-restriction))
               :subtitle-max-lines   (if registrar
                                       (if preferred-name 1 2)
                                       1)
               :accessibility-label  :ens-button
               :container-margin-top 8
               :disabled             (not registrar)
               :chevron              true
               :icon                 :main-icons/username}
        registrar
        (assoc :on-press #(re-frame/dispatch [:navigate-to :ens-main registrar])))]
   ;; TODO replace this with list-item config map
   ;; left it as it is because not sure how to enable it for testing
     (when tribute-to-talk [tribute-to-talk-item tribute-to-talk])
     [quo/list-item
      {:title               (i18n/label :t/contacts)
       :icon                :main-icons/in-contacts
       :accessibility-label :contacts-button
       :accessory           :text
       :accessory-text      (if (pos? active-contacts-count)
                              (str active-contacts-count)
                              (i18n/label :t/none))
       :chevron             true
       :on-press            #(re-frame/dispatch [:navigate-to :contacts-list])}]
     [react/view {:padding-top 16}
      [quo/list-header (i18n/label :t/settings)]]
     [quo/list-item
      {:icon                :main-icons/security
       :title               (i18n/label :t/privacy-and-security)
       :accessibility-label :privacy-and-security-settings-button
       :chevron             true
       :accessory           (when mnemonic
                              [components.common/counter {:size 22} 1])
       :on-press            #(re-frame/dispatch [:navigate-to :privacy-and-security])}]
     [quo/list-item
      {:icon                :main-icons/appearance
       :title               (i18n/label :t/appearance)
       :accessibility-label :appearance-settings-button
       :chevron             true
       :on-press            #(re-frame/dispatch [:navigate-to :appearance])}]
     (when (and platform/android?
                config/local-notifications?)
       [quo/list-item
        {:icon                :main-icons/notification
         :title               (i18n/label :t/notifications)
         :accessibility-label :notifications-button
         :active              notifications-enabled?
         :on-press            #(re-frame/dispatch
                                [:multiaccounts.ui/notifications-switched (not notifications-enabled?)])
         :accessory           :switch}])
     [quo/list-item
      {:icon                :main-icons/mobile
       :title               (i18n/label :t/sync-settings)
       :accessibility-label :sync-settings-button
       :chevron             true
       :on-press            #(re-frame/dispatch [:navigate-to :sync-settings])}]
     (when (and (or platform/android?
                    config/keycard-test-menu-enabled?)
                config/hardwallet-enabled?
                keycard-pairing)
       [quo/list-item
        {:icon                :main-icons/keycard
         :title               (i18n/label :t/keycard)
         :accessibility-label :keycard-button
         :chevron             true
         :on-press            #(re-frame/dispatch [:navigate-to :keycard-settings])}])
     [quo/list-item
      {:icon                :main-icons/settings-advanced
       :title               (i18n/label :t/advanced)
       :accessibility-label :advanced-button
       :chevron             true
       :on-press            #(re-frame/dispatch [:navigate-to :advanced-settings])}]
     [quo/list-item
      {:icon                :main-icons/help
       :title               (i18n/label :t/need-help)
       :accessibility-label :help-button
       :chevron             true
       :on-press            #(re-frame/dispatch [:navigate-to :help-center])}]
     [quo/list-item
      {:icon                :main-icons/info
       :title               (i18n/label :t/about-app)
       :accessibility-label :about-button
       :chevron             true
       :on-press            #(re-frame/dispatch [:navigate-to :about-app])}]
     [react/view {:padding-vertical 24}
      [quo/list-item
       {:icon                :main-icons/log-out
        :title               (i18n/label :t/sign-out)
        :accessibility-label :log-out-button
        :theme               :negative
        :on-press
        #(re-frame/dispatch [:multiaccounts.logout.ui/logout-pressed])}]]]))

(defn my-profile []
  (fn []
    (let [{:keys [public-key ens-verified preferred-name]
           :as   account} @(re-frame/subscribe [:multiaccount])
          on-share        #(re-frame/dispatch [:show-popover
                                               {:view     :share-chat-key
                                                :address  public-key
                                                :ens-name preferred-name}])]
      [react/view {:style {:flex 1}}
       [quo/animated-header
        {:right-accessories [{:icon     :main-icons/share
                              :on-press on-share}]
         :use-insets        true
         :extended-header   (profile-header/extended-header
                             {:on-press on-share
                              :title    (multiaccounts/displayed-name account)
                              :photo    (multiaccounts/displayed-photo account)
                              :subtitle (if (and ens-verified public-key)
                                          (gfy/generate-gfy public-key)
                                          public-key)})}
        [content]]])))
