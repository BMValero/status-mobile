(ns status-im.ui.components.react
  (:require-macros [status-im.utils.views :as views])
  (:require [clojure.string :as string]
            [goog.object :as object]
            [reagent.core :as reagent]
            [status-im.ui.components.styles :as styles]
            [status-im.utils.utils :as utils]
            [status-im.utils.platform :as platform]
            [status-im.i18n :as i18n]
            [status-im.react-native.js-dependencies :as js-dependencies]
            [status-im.ui.components.colors :as colors]))

(defn get-react-property [name]
  (if js-dependencies/react-native
    (or (object/get js-dependencies/react-native name) {})
    #js {}))

(defn adapt-class [class]
  (when class
    (reagent/adapt-react-class class)))

(defn get-class [name]
  (adapt-class (get-react-property name)))

(def native-modules (.-NativeModules js-dependencies/react-native))
(def device-event-emitter (.-DeviceEventEmitter js-dependencies/react-native))
(def dismiss-keyboard! js-dependencies/dismiss-keyboard)
(def back-handler (get-react-property "BackHandler"))

(def splash-screen (.-SplashScreen native-modules))

;; React Components

(def app-registry (get-react-property "AppRegistry"))
(def app-state (get-react-property "AppState"))
(def net-info (get-react-property "NetInfo"))
(def view (get-class "View"))
(def safe-area-view (get-class "SafeAreaView"))
(def progress-bar (get-class "ProgressBarAndroid"))

(def status-bar (get-class (if platform/desktop? "View" "StatusBar")))

(def scroll-view (get-class "ScrollView"))
(def web-view (get-class "WebView"))
(def keyboard-avoiding-view-class (get-class "KeyboardAvoidingView"))

(def refresh-control (get-class "RefreshControl"))

(def text-class (get-class "Text"))
(def text-input-class (get-class "TextInput"))
(def image-class (get-class "Image"))
(def picker-class (get-class "Picker"))
(def picker-item-class (adapt-class (.-Item (get-react-property "Picker"))))

(defn valid-source? [source]
  (or (not (map? source))
      (not (contains? source :uri))
      (and (contains? source :uri)
           (:uri source))))

(defn image [{:keys [source] :as props}]
  (when (valid-source? source)
    [image-class props]))

(def switch (get-class "Switch"))
(def check-box (get-class "CheckBox"))

(def touchable-highlight-class (get-class "TouchableHighlight"))
(def touchable-without-feedback-class (get-class "TouchableWithoutFeedback"))
(def touchable-opacity (get-class "TouchableOpacity"))
(def activity-indicator (get-class "ActivityIndicator"))

(def modal (get-class "Modal"))

(def pan-responder (.-PanResponder js-dependencies/react-native))
(def animated (.-Animated js-dependencies/react-native))
(def animated-view (reagent/adapt-react-class (.-View animated)))
(def animated-text (reagent/adapt-react-class (.-Text animated)))

(def dimensions (.-Dimensions js-dependencies/react-native))
(def keyboard (.-Keyboard js-dependencies/react-native))
(def linking (.-Linking js-dependencies/react-native))
(def desktop-notification (.-DesktopNotification (.-NativeModules js-dependencies/react-native)))

(def slider (get-class "Slider"))
;; Accessor methods for React Components

(def default-font {:font-family "Inter UI"})

(defn add-font-style [style-key opts]
  (let [style (get opts style-key)]
    (-> opts
        (dissoc :font)
        (assoc style-key (merge default-font style)))))

(defn transform-to-uppercase [{:keys [uppercase? force-uppercase?]} ts]
  (if (or force-uppercase? (and uppercase? platform/android?))
    (vec (map #(when % (string/upper-case %)) ts))
    ts))

(defn text
  ([t]
   [text-class t])
  ([opts t & ts]
   (->> (conj ts t)
        (transform-to-uppercase opts)
        (concat [text-class (add-font-style :style opts)])
        (vec))))

(defn text-input [{:keys [style] :as opts} text]
  [text-input-class (merge
                     {:underline-color-android :transparent
                      :placeholder-text-color  colors/text-gray
                      :placeholder             (i18n/label :t/type-a-message)
                      :value                   text}
                     (-> opts
                         (dissoc :font)
                         (assoc :style (merge default-font style))))])

(defn i18n-text
  [{:keys [style key]}]
  (let [default-style {:font-size 14}]
    [text {:style (merge default-style style)} (i18n/label key)]))

(defn icon
  ([n] (icon n styles/icon-default))
  ([n style]
   [image {:source     {:uri (keyword (str "icon_" (name n)))}
           :resizeMode "contain"
           :style      style}]))

(defn touchable-highlight [props content]
  [touchable-highlight-class
   (merge {:underlay-color :transparent} props)
   content])

(defn touchable-without-feedback [props content]
  [touchable-without-feedback-class
   props
   content])

(defn get-dimensions [name]
  (js->clj (.get dimensions name) :keywordize-keys true))

(defn list-item [component]
  (reagent/as-element component))

(defn value->picker-item [{:keys [value label]}]
  [picker-item-class {:value (or value "") :label (or label value "")}])

(defn picker [{:keys [style on-change selected enabled data]}]
  (into
    [picker-class (merge (when style {:style style})
                         (when enabled {:enabled enabled})
                         (when on-change {:on-value-change on-change})
                         (when selected {:selected-value selected}))]
    (map value->picker-item data)))

;; Image picker

(def image-picker-class js-dependencies/image-crop-picker)

(defn show-access-error [o]
  (when (= "E_PERMISSION_MISSING" (object/get o "code"))
    (utils/show-popup (i18n/label :t/error)
                      (i18n/label :t/photos-access-error))))

(defn show-image-picker
  ([images-fn]
   (show-image-picker images-fn nil))
  ([images-fn media-type]
   (let [image-picker (.-default image-picker-class)]
     (-> image-picker
         (.openPicker (clj->js {:multiple false :mediaType (or media-type "any")}))
         (.then images-fn)
         (.catch show-access-error)))))

;; Clipboard

(def sharing
  (.-Share js-dependencies/react-native))

(defn copy-to-clipboard [text]
  (.setString (.-Clipboard js-dependencies/react-native) text))

(defn get-from-clipboard [clbk]
  (let [clipboard-contents (.getString (.-Clipboard js-dependencies/react-native))]
    (.then clipboard-contents #(clbk %))))

;; HTTP Bridge

(def http-bridge js-dependencies/http-bridge)

;; KeyboardAvoidingView

(defn keyboard-avoiding-view [props & children]
  (let [view-element (if platform/ios?
                       [keyboard-avoiding-view-class (merge {:behavior :padding} props)]
                       [view props])]
    (vec (concat view-element children))))

(views/defview with-activity-indicator
  [{:keys [timeout style enabled? preview]} comp]
  (views/letsubs
    [loading (reagent/atom true)]
    {:component-did-mount (fn []
                            (if (or (nil? timeout)
                                    (> 100 timeout))
                              (reset! loading false)
                              (utils/set-timeout #(reset! loading false)
                                                 timeout)))}
    (if (and (not enabled?) @loading)
      (or preview
          [view {:style (or style {:justify-content :center
                                   :align-items     :center})}
           [activity-indicator {:animating true}]])
      comp)))

(defn navigation-wrapper
  "Wraps component so that it will be shown only when current-screen is one of views"
  [{:keys [component views current-view hide?]
    :or   {hide? false}}]
  (let [current-view? (if (set? views)
                        (views current-view)
                        (= views current-view))

        style (if current-view?
                {:flex   1
                 :zIndex 0}
                {:opacity 0
                 :flex    0
                 :zIndex -1})

        component' (if (fn? component) [component] component)]

    (when (or (not hide?) (and hide? current-view?))
      (if hide?
        component'
        [view style (if (fn? component) [component] component)]))))

(defn with-empty-preview [comp]
  [with-activity-indicator
   {:preview [view {}]}
   comp])

;; Platform-specific View

(defmulti create-main-screen-view #(cond
                                     platform/iphone-x? :iphone-x
                                     platform/ios? :ios
                                     platform/android? :android))

(defmethod create-main-screen-view :iphone-x [current-view]
  (fn [props & children]
    (let [props             (merge props
                                   {:background-color
                                    (case current-view
                                      (:wallet
                                       :wallet-send-transaction
                                       :wallet-transaction-sent
                                       :wallet-request-transaction
                                       :wallet-send-transaction-chat
                                       :wallet-send-assets
                                       :wallet-request-assets
                                       :choose-recipient
                                       :recent-recipients
                                       :wallet-send-transaction-modal
                                       :wallet-transaction-sent-modal
                                       :wallet-send-transaction-request
                                       :wallet-transaction-fee
                                       :wallet-sign-message-modal
                                       :contact-code
                                       :wallet-onboarding-setup
                                       :wallet-settings-assets
                                       :wallet-modal
                                       :wallet-onboarding-setup-modal
                                       :wallet-settings-hook)
                                      colors/blue

                                      (:qr-viewer
                                       :recipient-qr-code)
                                      "#2f3031"

                                      colors/white)})
          bottom-background (when (#{:wallet
                                     :recent-recipients
                                     :wallet-send-assets
                                     :wallet-request-assets
                                     :wallet-settings-assets
                                     :wallet-modal} current-view)
                              [view {:background-color colors/white
                                     :position         :absolute
                                     :bottom           0
                                     :right            0
                                     :left             0
                                     :height           100
                                     :z-index          -1000}])
          children (conj children bottom-background)]
      (apply vector safe-area-view props children))))

(defmethod create-main-screen-view :default [_]
  view)

(views/defview main-screen-modal-view [current-view & components]
  (views/letsubs []
    (let [main-screen-view (create-main-screen-view current-view)]
      [main-screen-view styles/flex
       [(if (= current-view :chat-modal)
          view
          keyboard-avoiding-view)
        {:flex 1 :flex-direction :column}
        (apply vector view styles/flex components)]])))
