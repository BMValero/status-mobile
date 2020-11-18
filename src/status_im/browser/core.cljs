(ns status-im.browser.core
  (:require [clojure.string :as string]
            [re-frame.core :as re-frame]
            [status-im.browser.permissions :as browser.permissions]
            [status-im.constants :as constants]
            [status-im.ethereum.core :as ethereum]
            [status-im.ethereum.ens :as ens]
            [status-im.ethereum.json-rpc :as json-rpc]
            [status-im.ethereum.resolver :as resolver]
            [status-im.i18n :as i18n]
            [status-im.native-module.core :as status]
            [status-im.ui.components.list-selection :as list-selection]
            [status-im.navigation :as navigation]
            [status-im.utils.contenthash :as contenthash]
            [status-im.utils.fx :as fx]
            [status-im.utils.http :as http]
            [status-im.utils.multihash :as multihash]
            [status-im.utils.platform :as platform]
            [status-im.utils.random :as random]
            [status-im.utils.types :as types]
            [status-im.utils.universal-links.utils :as links]
            [taoensso.timbre :as log]
            [status-im.signing.core :as signing]
            [status-im.multiaccounts.update.core :as multiaccounts.update]
            [status-im.ui.components.bottom-sheet.core :as bottom-sheet]
            [status-im.browser.webview-ref :as webview-ref]
            ["eth-phishing-detect" :as eth-phishing-detect]))

(fx/defn update-browser-option
  [{:keys [db]} option-key option-value]
  {:db (assoc-in db [:browser/options option-key] option-value)})

(fx/defn update-browser-options
  [{:keys [db]} options]
  {:db (update db :browser/options merge options)})

(defn get-current-browser [db]
  (get-in db [:browser/browsers (get-in db [:browser/options :browser-id])]))

(defn get-current-url [{:keys [history history-index]
                        :or {history-index 0}}]
  (when history
    (nth history history-index)))

(defn secure? [{:keys [error? dapp?]} {:keys [url]}]
  (or dapp?
      (and (not error?)
           (when url
             (string/starts-with? url "https://")))))

(fx/defn remove-browser
  [{:keys [db]} browser-id]
  {:db            (update-in db [:browser/browsers] dissoc browser-id)
   ::json-rpc/call [{:method "browsers_deleteBrowser"
                     :params [browser-id]
                     :on-success #()}]})

(fx/defn clear-all-browsers
  {:events [:browser.ui/clear-all-browsers-pressed]}
  [{:keys [db]}]
  {:db             (dissoc db :browser/browsers)
   ::json-rpc/call (for [browser-id (keys (get db :browser/browsers))]
                     {:method     "browsers_deleteBrowser"
                      :params     [browser-id]
                      :on-success #()})})

(defn update-dapp-name [{:keys [name] :as browser}]
  (assoc browser :dapp? false :name (or name (i18n/label :t/browser))))

(defn check-if-phishing-url [{:keys [history history-index] :as browser}]
  (let [history-host (http/url-host (try (nth history history-index) (catch js/Error _)))]
    (cond-> browser history-host (assoc :unsafe? (eth-phishing-detect history-host)))))

(defn- content->hash [hex]
  (when (and hex (not= hex "0x"))
    ;; TODO(julien) Remove once our ENS DApp are migrated
    (multihash/base58 (multihash/create :sha2-256 (subs hex 2)))))

(defn resolve-ens-content-callback [hex]
  (let [hash (content->hash hex)]
    (if (and hash (not= hash resolver/default-hash))
      (re-frame/dispatch [:browser.callback/resolve-ens-multihash-success {:namespace :ipfs :hash hash}])
      (re-frame/dispatch [:browser.callback/resolve-ens-contenthash]))))

(defn resolve-ens-contenthash-callback [hex]
  (let [{:keys [hash] :as m} (contenthash/decode hex)]
    (if (and hash (not= hash resolver/default-hash))
      (re-frame/dispatch [:browser.callback/resolve-ens-multihash-success m])
      (re-frame/dispatch [:browser.callback/resolve-ens-multihash-error]))))

(fx/defn resolve-url
  [{:keys [db]} {:keys [error? resolved-url]}]
  (when (not error?)
    (let [current-url (get-current-url (get-current-browser db))
          host (http/url-host current-url)]
      (if (and (not resolved-url) (ens/is-valid-eth-name? host))
        (let [chain   (ethereum/chain-keyword db)]
          {:db                            (update db :browser/options assoc :resolving? true)
           :browser/resolve-ens-content {:registry (get ens/ens-registries
                                                        chain)
                                         :ens-name host
                                         :cb       resolve-ens-content-callback}})
        {:db (update db :browser/options assoc :url (or resolved-url current-url) :resolving? false)}))))

(fx/defn resolve-ens-contenthash
  [{:keys [db]}]
  (let [current-url (get-current-url (get-current-browser db))
        host (http/url-host current-url)
        chain   (ethereum/chain-keyword db)]
    {:db                            (update db :browser/options assoc :resolving? true)
     :browser/resolve-ens-contenthash {:registry (get ens/ens-registries
                                                      chain)
                                       :ens-name host
                                       :cb       resolve-ens-contenthash-callback}}))

(fx/defn update-browser
  [{:keys [db now]}
   {:keys [browser-id] :as browser}]
  (let [updated-browser (-> (assoc browser :timestamp now)
                            (update-dapp-name)
                            (check-if-phishing-url))]
    {:db            (update-in db
                               [:browser/browsers browser-id]
                               merge updated-browser)
     ::json-rpc/call [{:method "browsers_addBrowser"
                       :params [(select-keys updated-browser [:browser-id :timestamp :name :dapp? :history :history-index])]
                       :on-success #()}]}))

(defn can-go-back? [{:keys [history-index]}]
  (pos? history-index))

(fx/defn navigate-to-previous-page
  [cofx]
  (let [{:keys [history-index] :as browser} (get-current-browser (:db cofx))]
    (when (can-go-back? browser)
      (fx/merge cofx
                (update-browser (assoc browser :history-index (dec history-index)))
                (resolve-url nil)))))

(fx/defn ignore-unsafe
  {:events [:browser/ignore-unsafe]}
  [cofx]
  (let [browser (get-current-browser (:db cofx))
        host (http/url-host (get-current-url browser))]
    (update-browser cofx (assoc browser :ignore-unsafe host))))

(defn can-go-forward? [{:keys [history-index history]}]
  (< history-index (dec (count history))))

(fx/defn navigate-to-next-page
  [cofx]
  (let [{:keys [history-index] :as browser} (get-current-browser (:db cofx))]
    (when (can-go-forward? browser)
      (fx/merge cofx
                (update-browser (assoc browser :history-index (inc history-index)))
                (resolve-url nil)))))

(fx/defn update-browser-history
  [cofx browser url]
  (let [history-index (:history-index browser)
        history       (:history browser)]
    (let [new-history (conj (subvec history 0 (inc history-index)) url)
          new-index   (dec (count new-history))]
      (update-browser cofx
                      (assoc browser
                             :history new-history
                             :history-index new-index)))))

(defmulti storage-gateway :namespace)

(defmethod storage-gateway :ipns
  [{:keys [hash]}]
  (str "https://" hash))

(defmethod storage-gateway :ipfs
  [{:keys [hash]}]
  (contenthash/ipfs-url hash))

(defmethod storage-gateway :swarm
  [{:keys [hash]}]
  (str "https://swarm-gateways.net/bzz:/" hash))

(fx/defn resolve-ens-multihash-success
  [{:keys [db] :as cofx} m]
  (let [current-url (get-current-url (get-current-browser db))
        host        (http/url-host current-url)
        path        (subs current-url (+ (.indexOf ^js current-url host) (count host)))
        gateway     (storage-gateway m)]
    (fx/merge cofx
              {:db (-> (update db :browser/options
                               assoc
                               :url (str gateway path)
                               :resolving? false)
                       (assoc-in [:browser/options :resolved-ens host] gateway))})))

(fx/defn resolve-ens-multihash-error
  [{:keys [db] :as cofx}]
  (update-browser-options cofx {:url        (get-current-url (get-current-browser db))
                                :resolving? false
                                :error?     true}))

(fx/defn handle-browser-error
  [cofx]
  (fx/merge cofx
            (update-browser-option :error? true)
            (update-browser-option :loading? false)))

(fx/defn handle-pdf
  [_ url]
  (when (and platform/android? (string/ends-with? url ".pdf"))
    {:browser/show-web-browser-selection url}))

(fx/defn handle-message-link
  [cofx link]
  (if (links/universal-link? link)
    {:dispatch [:universal-links/handle-url link]}
    {:browser/show-browser-selection link}))

(fx/defn update-browser-on-nav-change
  [cofx url error?]
  (let [browser (get-current-browser (:db cofx))
        options (get-in cofx [:db :browser/options])
        current-url (:url options)]
    (when (and (not= "about:blank" url) (not= current-url url) (not= (str current-url "/") url))
      (let [resolved-ens (first (filter (fn [v]
                                          (not= (.indexOf ^js url (second v)) -1))
                                        (:resolved-ens options)))
            resolved-url (if resolved-ens
                           (http/normalize-url (string/replace url (second resolved-ens) (first resolved-ens)))
                           url)]
        (fx/merge cofx
                  (update-browser-history browser resolved-url)
                  (handle-pdf url)
                  (resolve-url {:error? error? :resolved-url (when resolved-ens url)}))))))

(fx/defn update-browser-name
  [cofx title]
  (let [browser (get-current-browser (:db cofx))]
    (when (and (not (:dapp? browser)) title (not (string/blank? title)))
      (update-browser cofx (assoc browser :name title)))))

(fx/defn navigation-state-changed
  [cofx event error?]
  (let [{:strs [url loading title]} (js->clj event)
        deep-link?                  (links/deep-link? url)]
    (if (links/universal-link? url)
      (when-not (and deep-link? platform/ios?) ;; ios webview handles this
        {:dispatch [:universal-links/handle-url url]})
      (fx/merge cofx
                (update-browser-option :loading? loading)
                (update-browser-name title)
                (update-browser-on-nav-change url error?)))))

(fx/defn open-url-in-current-browser
  "Opens a url in the current browser, which mean no new entry is added to the home page
  and history of the current browser is updated so that the user can navigate back to the
  origin url"
  [cofx url]
  (let [browser (get-current-browser (:db cofx))
        normalized-url (http/normalize-and-decode-url url)]
    (if (links/universal-link? normalized-url)
      {:dispatch [:universal-links/handle-url normalized-url]}
      (fx/merge cofx
                (update-browser-option :url-editing? false)
                (update-browser-history browser normalized-url)
                (resolve-url nil)))))

(fx/defn open-url
  "Opens a url in the browser. If a host can be extracted from the url and
  there is already a browser for this host, this browser is reused
  If the browser is reused, the history is flushed"
  [{:keys [db] :as cofx} url]
  (let [normalized-url (http/normalize-and-decode-url url)
        browser {:browser-id    (random/id)
                 :history-index 0
                 :history       [normalized-url]}]
    (if (links/universal-link? normalized-url)
      {:dispatch [:universal-links/handle-url normalized-url]}
      (fx/merge cofx
                {:db (assoc db :browser/options
                            {:browser-id (:browser-id browser)})}
                (navigation/navigate-to-cofx :browser-stack {:screen :browser
                                                             :initial false})
                (update-browser browser)
                (resolve-url nil)))))

(fx/defn open-existing-browser
  "Opens an existing browser with it's history"
  [{:keys [db] :as cofx} browser-id]
  (let [browser (get-in db [:browser/browsers browser-id])]
    (fx/merge cofx
              {:db (assoc db :browser/options
                          {:browser-id browser-id})}
              (update-browser browser)
              (navigation/navigate-to-cofx :browser nil)
              (resolve-url nil))))

(fx/defn web3-error-callback
  {:events [:browser.dapp/transaction-on-error]}
  [_ message-id message]
  {:browser/send-to-bridge
   {:type      constants/web3-send-async-callback
    :messageId message-id
    :error     message}})

(fx/defn dapp-complete-transaction
  {:events [:browser.dapp/transaction-on-result]}
  [_ message-id id result]
  ;;TODO check and test id
  {:browser/send-to-bridge
   {:type      constants/web3-send-async-callback
    :messageId message-id
    :result    {:jsonrpc "2.0"
                :id      (int id)
                :result  result}}})

(defn normalize-message
  "NOTE (andrey) there is no spec for this, so this implementation just to be compatible with MM"
  [message]
  (if (string/starts-with? message "0x")
    message
    (ethereum/utf8-to-hex message)))

(defn normalize-sign-message-params
  "NOTE (andrey) we need this function, because params may be mixed up"
  [params typed?]
  (let [[first-param second-param] params]
    (when (and (string? first-param) (string? second-param))
      (cond
        (ethereum/address? first-param)
        [first-param (if typed? second-param (normalize-message second-param))]
        (ethereum/address? second-param)
        [second-param (if typed? first-param (normalize-message first-param))]))))

(fx/defn send-to-bridge
  [cofx message]
  {:browser/send-to-bridge message})

(fx/defn web3-send-async
  [cofx {:keys [method params id] :as payload} message-id]
  (let [message?      (constants/web3-sign-message? method)
        dapps-address (get-in cofx [:db :multiaccount :dapps-address])
        typed? (not= constants/web3-personal-sign method)]
    (if (or message? (= constants/web3-send-transaction method))
      (let [[address data] (cond (and (= method constants/web3-keycard-sign-typed-data)
                                      (not (vector? params)))
                                 ;; We don't use signer argument for keycard sign-typed-data
                                 ["0x0" params]
                                 message? (normalize-sign-message-params params typed?)
                                 :else [nil nil])]
        (when (or (not message?) (and address data))
          (signing/sign cofx (merge
                              (if message?
                                {:message {:address address
                                           :data data
                                           :typed? typed?
                                           :pinless? (= method constants/web3-keycard-sign-typed-data)
                                           :from dapps-address}}
                                {:tx-obj  (update (first params) :from #(or % dapps-address))})
                              {:on-result [:browser.dapp/transaction-on-result message-id id]
                               :on-error  [:browser.dapp/transaction-on-error message-id]}))))
      (if (#{"eth_accounts" "eth_coinbase"} method)
        (send-to-bridge cofx {:type      constants/web3-send-async-callback
                              :messageId message-id
                              :result    {:jsonrpc "2.0"
                                          :id      (int id)
                                          :result  (if (= method "eth_coinbase") dapps-address [dapps-address])}})
        {:browser/call-rpc [payload
                            #(re-frame/dispatch [:browser.callback/call-rpc
                                                 {:type      constants/web3-send-async-callback
                                                  :messageId message-id
                                                  :error     %1
                                                  :result    %2}])]}))))

(fx/defn web3-send-async-read-only
  [{:keys [db] :as cofx} dapp-name {:keys [method] :as payload} message-id]
  (let [{:dapps/keys [permissions]} db]
    (if (and (#{"eth_accounts" "eth_coinbase" "eth_sendTransaction" "eth_sign"
                "keycard_signTypedData"
                "eth_signTypedData" "personal_sign" "personal_ecRecover"} method)
             (not (some #{constants/dapp-permission-web3} (get-in permissions [dapp-name :permissions]))))
      (send-to-bridge cofx
                      {:type      constants/web3-send-async-callback
                       :messageId message-id
                       :error     {:code 4100}})
      (web3-send-async cofx payload message-id))))

(fx/defn handle-scanned-qr-code
  [cofx data {:keys [dapp-name permission message-id]}]
  (fx/merge (assoc-in cofx [:db :browser/options :yielding-control?] false)
            (browser.permissions/send-response-to-bridge permission message-id true data)
            (browser.permissions/process-next-permission dapp-name)
            (navigation/navigate-back)))

(fx/defn handle-canceled-qr-code
  [cofx {:keys [dapp-name permission message-id]}]
  (fx/merge (assoc-in cofx [:db :browser/options :yielding-control?] false)
            (browser.permissions/send-response-to-bridge permission message-id true nil)
            (browser.permissions/process-next-permission dapp-name)))

(fx/defn process-bridge-message
  [{:keys [db] :as cofx} message]
  (let [browser (get-current-browser db)
        url-original (get-current-url browser)
        data    (types/json->clj message)
        {{:keys [url]} :navState :keys [type permission payload messageId params]} data
        {:keys [dapp? name]} browser
        dapp-name (if dapp? name (http/url-host url-original))]
    (cond
      (and (= type constants/history-state-changed)
           (not= "about:blank" url))
      (update-browser-on-nav-change cofx url nil)

      (= type constants/web3-send-async-read-only)
      (web3-send-async-read-only cofx dapp-name payload messageId)

      (= type constants/api-request)
      (browser.permissions/process-permission cofx dapp-name permission messageId params))))

(defn filter-letters-numbers-and-replace-dot-on-dash
  [^js value]
  (let [cc (.charCodeAt value 0)]
    (cond (or (and (> cc 96) (< cc 123))
              (and (> cc 64) (< cc 91))
              (and (> cc 47) (< cc 58)))
          value
          (= cc 46)
          "-")))

(fx/defn open-chat-from-browser
  [cofx host]
  (let [topic (string/lower-case (apply str (map filter-letters-numbers-and-replace-dot-on-dash host)))]
    {:dispatch [:chat.ui/start-public-chat topic nil]}))

(re-frame/reg-fx
 :browser/resolve-ens-content
 (fn [{:keys [registry ens-name cb]}]
   (resolver/content registry ens-name cb)))

(re-frame/reg-fx
 :browser/resolve-ens-contenthash
 (fn [{:keys [registry ens-name cb]}]
   (resolver/contenthash registry ens-name cb)))

(re-frame/reg-fx
 :browser/send-to-bridge
 (fn [message]
   (let [^js webview @webview-ref/webview-ref
         msg (str "ReactNativeWebView.onMessage('"
                  (types/clj->json message)
                  "');")]
     (when (and message webview)
       (.injectJavaScript webview msg)))))

(re-frame/reg-fx
 :browser/call-rpc
 (fn [[payload callback]]
   (status/call-rpc
    (types/clj->json payload)
    (fn [response]
      (if (= "" response)
        (do
          (log/warn :web3-response-error)
          (callback "web3-response-error" nil))
        (callback nil (.parse js/JSON response)))))))

(re-frame/reg-fx
 :browser/show-browser-selection
 (fn [link]
   (list-selection/browse link)))

(re-frame/reg-fx
 :browser/show-web-browser-selection
 (fn [link]
   (list-selection/browse-in-web-browser link)))

(re-frame/reg-fx
 :browser/clear-web-data
 (fn []
   (status/clear-web-data)))

(defn share-link [url]
  (let [link    (links/generate-link :browse :external url)
        message (i18n/label :t/share-dapp-text {:link link})]
    (list-selection/open-share {:message message})))

(fx/defn dapps-account-selected
  {:events [:dapps-account-selected]}
  [{:keys [db] :as cofx} address]
  (fx/merge cofx
            {:browser/clear-web-data nil}
            (bottom-sheet/hide-bottom-sheet)
            (browser.permissions/clear-dapps-permissions)
            (multiaccounts.update/multiaccount-update :dapps-address address {})
            #(when (= (:view-id db) :browser)
               (merge (navigation/navigate-back %)
                      {:dispatch [:browser.ui/browser-item-selected (get-in db [:browser/options :browser-id])]}))))
