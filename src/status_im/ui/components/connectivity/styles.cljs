(ns status-im.ui.components.connectivity.styles
  (:require-macros [status-im.utils.styles :refer [defnstyle]]))

(defnstyle text-wrapper [top opacity window-width pending?]
  {:ios              {:z-index 0}
   :opacity          opacity
   :width            window-width
   :top              (+ (+ 56 top) (if pending? 35 0))
   :position         :absolute
   :background-color "#828b92cc"
   :height           35})

(def text
  {:text-align :center
   :color      :white
   :font-size  14
   :top        8})
