(ns quo2.components.reacts
  (:require [quo2.components.text :as quo2-text]
            [quo.react-native :as rn]
            [quo.theme :as theme]
            [quo2.foundations.colors :as colors]
            [status-im.ui.components.icons.icons :as icons]))

(def reaction-styling
  {:flex-direction :row
   :justify-content :center
   :align-items :center
   :padding-vertical 3
   :padding-horizontal 8
   :border-radius 8})

(defn open-reactions-menu
  [{:keys [on-press]}]
  (let [dark? (theme/dark?)]
    [rn/touchable-opacity {:on-press on-press
                           :style (merge reaction-styling
                                         {:margin-top 25
                                          :border-width 1
                                          :border-color (if dark?
                                                          colors/white-opa-5
                                                          colors/neutral-80)})}
     [icons/icon :main-icons/add-reaction20
      {:color (if dark?
                colors/white
                colors/black)}]]))

(defn render-react
  "Add your emoji as a param here"
  [{:keys [emoji clicks neutral? on-press]}]
  (let [dark? (theme/dark?)
        text-color (if dark? colors/white
                       colors/black)
        numeric-value (int clicks)
        clicks-positive? (pos? numeric-value)]
    [rn/touchable-opacity {:on-press on-press
                           :style (merge reaction-styling
                                         (cond-> {:background-color
                                                  (if dark?
                                                    (if neutral?
                                                      colors/neutral-70
                                                      :transparent)
                                                    (if neutral?
                                                      colors/neutral-30
                                                      :transparent))}
                                           (and dark? (not neutral?)) (assoc :border-color colors/neutral-70
                                                                             :border-width 1)
                                           (and (not dark?) (not neutral?)) (assoc :border-color colors/neutral-30
                                                                                   :border-width 1)))}
     [icons/icon emoji {:no-color true
                        :width 16
                        :height 16}]
     [quo2-text/text {:size :paragraph-2
                      :weight :semi-bold
                      :color text-color
                      :flex-direction :row
                      :align-items :center
                      :justify-content :center}
      (if clicks-positive?
        (str " " numeric-value)
        "")]]))
