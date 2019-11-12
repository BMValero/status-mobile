(ns status-im.ui.screens.profile.group-chat.views
  (:require-macros [status-im.utils.views :refer [defview letsubs]])
  (:require [status-im.utils.platform :as platform]
            [status-im.constants :as constants]
            [status-im.ui.screens.profile.group-chat.styles :as styles]
            [status-im.ui.components.react :as react]
            [status-im.ui.screens.profile.components.styles :as profile.components.styles]
            [status-im.ui.screens.profile.components.views :as profile.components]
            [status-im.ui.components.contact.contact :as contact]
            [status-im.ui.components.list.views :as list]
            [status-im.ui.components.colors :as colors]
            [status-im.ui.components.status-bar.view :as status-bar]
            [status-im.ui.components.toolbar.view :as toolbar]
            [re-frame.core :as re-frame]
            [status-im.ui.components.common.styles :as common.styles]
            [status-im.i18n :as i18n]
            [status-im.utils.utils :as utils]
            [status-im.ui.components.list-item.views :as list-item]))

(defn group-chat-profile-toolbar [admin?]
  [toolbar/toolbar {}
   toolbar/default-nav-back
   nil
   (when admin?
     [toolbar/text-action {:handler #(re-frame/dispatch [:group-chat-profile/start-editing])
                           :accessibility-label :edit-button}
      (i18n/label :t/edit)])])

(defn group-chat-profile-edit-toolbar []
  [toolbar/toolbar {}
   nil
   nil
   [toolbar/text-action {:handler   #(re-frame/dispatch [:group-chats.ui/save-pressed])
                         :accessibility-label :done-button}
    (i18n/label :t/done)]])

(defn member-actions [chat-id member us-admin?]
  (concat
   [{:action #(re-frame/dispatch [(if platform/desktop? :show-profile-desktop :chat.ui/show-profile) (:public-key member)])
     :label  (i18n/label :t/view-profile)}]
   (when-not (:admin? member)
     [{:action #(re-frame/dispatch [:group-chats.ui/remove-member-pressed chat-id (:public-key member)])
       :label  (i18n/label :t/remove-from-chat)}])
   (when (and us-admin?
              (not (:admin? member)))
     [{:action #(re-frame/dispatch [:group-chats.ui/make-admin-pressed chat-id (:public-key member)])
       :label  (i18n/label :t/make-admin)}])))

(defn render-member [chat-id {:keys [name public-key] :as member} admin? current-user-identity]
  [react/view {:padding-vertical 10}
   [contact/contact-view
    {:contact             member
     :extend-options      (member-actions chat-id member admin?)
     :info                (when (:admin? member)
                            (i18n/label :t/group-chat-admin))
     :extend-title        name
     :extended?           (and admin?
                               (not= public-key current-user-identity))
     :accessibility-label :member-item
     :inner-props         {:accessibility-label :member-name-text}
     :on-press            (when (not= public-key current-user-identity)
                            #(re-frame/dispatch [(if platform/desktop? :show-profile-desktop :chat.ui/show-profile) public-key]))}]])

(defview chat-group-members-view [chat-id admin? current-user-identity]
  (letsubs [members [:contacts/current-chat-contacts]]
    (when (seq members)
      [list/flat-list {:data      members
                       :key-fn    :address
                       :render-fn #(render-member chat-id % admin? current-user-identity)}])))

(defn members-list [chat-id admin? current-user-identity]
  [react/view
   [list-item/list-item {:title :t/members-title :type :section-header}]
   [chat-group-members-view chat-id admin? current-user-identity]])

(defview group-chat-profile []
  (letsubs [{:keys [admins chat-id] :as current-chat} [:chats/current-chat]
            editing?     [:group-chat-profile/editing?]
            members      [:contacts/current-chat-contacts]
            changed-chat [:group-chat-profile/profile]
            current-pk   [:multiaccount/public-key]]
    (when current-chat
      (let [shown-chat            (merge current-chat changed-chat)
            admin?                (get admins current-pk)
            allow-adding-members? (and admin?
                                       (< (count members) constants/max-group-chat-participants))]
        [react/view profile.components.styles/profile
         [status-bar/status-bar]
         ;;TODO doesn't work, needs to be fixed
         ;(if editing?
           ;[group-chat-profile-edit-toolbar]
         [group-chat-profile-toolbar false];admin?]
         [react/scroll-view
          [react/view profile.components.styles/profile-form
           [profile.components/group-header-display shown-chat]
           [react/view {:height 20}]
           (when allow-adding-members?
             [list-item/list-item
              {:title    :t/add-members
               :icon     :main-icons/add
               :theme    :action
               :on-press #(re-frame/dispatch [:navigate-to :add-participants-toggle-list])}])
           [list-item/list-item
            {:title               :t/clear-history
             :icon                :main-icons/close
             :theme               :action
             :on-press            #(re-frame/dispatch [:chat.ui/clear-history-pressed])
             :accessibility-label :clear-history-button}]
           [list-item/list-item
            {:title               :t/delete-chat
             :icon                :main-icons/arrow-left
             :theme               :action
             :on-press            #(re-frame/dispatch [:group-chats.ui/remove-chat-pressed chat-id])
             :accessibility-label :delete-chat-button}]
           [members-list chat-id admin? (first admins) current-pk]]]]))))
