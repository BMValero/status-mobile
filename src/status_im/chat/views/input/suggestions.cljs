(ns status-im.chat.views.input.suggestions
  (:require-macros [status-im.utils.views :refer [defview letsubs]])
  (:require [re-frame.core :as re-frame]
            [status-im.ui.components.react :as react]
            [status-im.chat.styles.input.suggestions :as style]
            [status-im.chat.views.input.animations.expandable :as expandable]
            [status-im.chat.commands.core :as commands]
            [status-im.i18n :as i18n]
            [taoensso.timbre :as log]))

(defn suggestion-item [{:keys [on-press name description last? accessibility-label]}]
  [react/touchable-highlight (cond-> {:on-press on-press}
                               accessibility-label (assoc :accessibility-label accessibility-label))
   [react/view style/item-suggestion-container
    [react/text {:style style/item-suggestion-name}
     name]
    [react/text {:style           style/item-suggestion-description
                 :number-of-lines 2}
     description]]])

(defview suggestions-view []
  (letsubs [available-commands [:get-available-commands]]
    [expandable/expandable-view {:key :suggestions}
     [react/view
      [react/scroll-view {:keyboard-should-persist-taps :always
                          :bounces                      false}
       (when (seq available-commands)
         (map-indexed
          (fn [i {:keys [type] :as command}]
            ^{:key i}
            [suggestion-item {:on-press            #(re-frame/dispatch [:select-chat-input-command command nil])
                              :name                (commands/command-name type)
                              :description         (commands/command-description type)
                              :last?               (= i (dec (count available-commands)))
                              :accessibility-label (commands/accessibility-label type)}])
          available-commands))]]]))
