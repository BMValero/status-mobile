(ns status-im.extensions.registry
  (:refer-clojure :exclude [list])
  (:require [clojure.set :as set]
            [clojure.string :as string]
            [re-frame.core :as re-frame]
            [pluto.core :as pluto]
            [status-im.accounts.update.core :as accounts.update]
            [status-im.chat.commands.core :as commands]
            [status-im.chat.commands.protocol :as protocol]
            [status-im.i18n :as i18n]
            [status-im.ui.screens.navigation :as navigation]
            [status-im.utils.fx :as fx]))

(defprotocol Hook
  "Encapsulate hook lifecycle."
  (hook-in [this id env properties cofx] "Hook it into host app.")
  (unhook [this id env properties cofx] "Remove extension hook from app."))

(defmulti hook-for (fn [hook] (pluto/hook-type hook)))

(defmethod hook-for "wallet.settings" [_]
  (reify Hook
    (hook-in [_ id _ m {:keys [db]}]
      {:db (assoc-in db [:wallet :settings id] m)})
    (unhook [_ id _ _ {:keys [db]}]
      {:db (update-in db [:wallet :settings] dissoc id)})))

(defmethod hook-for "chat.command" [_]
  (reify Hook
    (hook-in [_ id {extension-id :id} {:keys [description scope parameters preview short-preview
                                              on-send on-receive on-send-sync]} cofx]
      (let [new-command (if on-send-sync
                          (reify protocol/Command
                            (id [_] (name id))
                            (scope [_] scope)
                            (description [_] description)
                            (parameters [_] (or parameters []))
                            (validate [_ _ _])
                            (on-send [_ command-message _] (when on-send (on-send command-message)))
                            (on-receive [_ command-message _] (when on-receive (on-receive command-message)))
                            (short-preview [_ props] (when short-preview (short-preview props)))
                            (preview [_ props] (when preview (preview props)))
                            protocol/Yielding
                            (yield-control [_ props _] (on-send-sync props))
                            protocol/Extension
                            (extension-id [_] extension-id))
                          (reify protocol/Command
                            (id [_] (name id))
                            (scope [_] scope)
                            (description [_] description)
                            (parameters [_] (or parameters []))
                            (validate [_ _ _])
                            (on-send [_ command-message _] (when on-send (on-send command-message)))
                            (on-receive [_ command-message _] (when on-receive (on-receive command-message)))
                            (short-preview [_ props] (when short-preview (short-preview props)))
                            (preview [_ props] (when preview (preview props)))
                            protocol/Extension
                            (extension-id [_] extension-id)))]
        (commands/load-commands cofx [new-command])))
    (unhook [_ id _ {:keys [scope]} {:keys [db] :as cofx}]
      (when-let [command (get-in db [:id->command [(name id) scope] :type])]
        (commands/remove-command command cofx)))))

(defmethod hook-for :default [a]
  (reify Hook
    (hook-in [this id env properties cofx])
    (unhook [this id env properties cofx])))

(defn hook-id
  [s]
  (when s
    (last (string/split (name s) #"\."))))

(fx/defn update-hooks
  [{:keys [db] :as cofx} hook-fn extension-id]
  (let [account (get db :account/account)
        hooks   (get-in account [:extensions extension-id :hooks])]
    (apply fx/merge cofx
           (map (fn [[type extension]]
                  (hook-fn (hook-for type) (hook-id type) {:id extension-id} extension cofx))
                hooks))))

(fx/defn disable-hooks
  [{:keys [db] :as cofx} extension-id]
  (update-hooks cofx unhook extension-id))

(fx/defn add-to-registry
  [{:keys [db] :as cofx} extension-id extension-data active?]
  (let [{:keys [hooks]} extension-data
        data {:hooks   hooks
              :active? active?}]
    (fx/merge cofx
              {:db (update-in db [:account/account :extensions extension-id] merge data)}
              (update-hooks hook-in extension-id))))

(fx/defn remove-from-registry
  [cofx extension-id]
  (let [extensions (get-in cofx [:db :account/account :extensions])]
    (fx/merge cofx
              (when (get-in extensions [extension-id :active?])
                (update-hooks unhook extension-id))
              {:db (update-in cofx [:db :account/account :extensions] dissoc extension-id)})))

(fx/defn change-state
  [cofx extension-key active?]
  (let [extensions     (get-in cofx [:db :account/account :extensions])
        new-extensions (assoc-in extensions [extension-key :active?] active?)
        hook-fn        (if active?
                         hook-in
                         unhook)]
    (fx/merge cofx
              (accounts.update/account-update {:extensions new-extensions} {:success-event nil})
              (update-hooks hook-fn extension-key))))

(fx/defn install
  [{:keys [db] :as cofx} url {:keys [hooks] :as extension-data} modal?]
  (let [{:account/keys    [account]} db
        extension      {:id      url
                        :name    (or (get-in extension-data [:meta :name]) "Unnamed")
                        :url     url
                        :active? true}
        new-extensions (assoc (:extensions account) url extension)]
    (fx/merge cofx
              {:utils/show-popup {:title      (i18n/label :t/success)
                                  :content    (i18n/label :t/extension-installed)
                                  :on-dismiss #(re-frame/dispatch (if modal?
                                                                    [:navigate-back]
                                                                    [:navigate-to-clean :my-profile]))}}
              (when hooks (accounts.update/account-update {:extensions new-extensions} {}))
              (when hooks (add-to-registry url extension-data true)))))

(fx/defn uninstall
  [{:keys [db] :as cofx} extension-key]
  (let [{:account/keys [account]} db
        new-extensions (dissoc (:extensions account) extension-key)]
    (fx/merge cofx
              {:utils/show-popup {:title     (i18n/label :t/success)
                                  :content   (i18n/label :t/extension-uninstalled)}}
              (remove-from-registry extension-key)
              (accounts.update/account-update {:extensions new-extensions} {}))))

(fx/defn load
  [cofx url modal?]
  (if (get-in cofx [:db :account/account :extensions url])
    {:utils/show-popup {:title   (i18n/label :t/error)
                        :content (i18n/label :t/extension-is-already-added)}}
    {:extensions/load {:extensions [{:url     (string/trim url)
                                     :active? true}]
                       :follow-up  (if modal? :extensions/stage-modal :extensions/stage)}}))

(fx/defn install-from-message
  [cofx url modal?]
  (if (get-in cofx [:db :account/account :dev-mode?])
    (load cofx url modal?)
    {:ui/show-confirmation
     {:title               (i18n/label :t/confirm-install)
      :content             (i18n/label :t/extension-install-alert)
      :on-accept           #(do
                              (re-frame/dispatch [:accounts.ui/dev-mode-switched true])
                              (re-frame/dispatch [:extensions.ui/install-extension-button-pressed url]))}}))

(fx/defn initialize
  [{{:account/keys [account]} :db}]
  (let [{:keys [extensions dev-mode?]} account]
    (when dev-mode?
      {:extensions/load {:extensions (vals extensions)
                         :follow-up  :extensions/add-to-registry}})))

(defn existing-hooks-for
  [type cofx extension-data]
  (let [added-hooks (reduce (fn [acc [_ {:keys [hooks]}]]
                              (->> (type hooks)
                                   (keys)
                                   (into acc)))
                            #{}
                            (get-in cofx [:db :account/account :extensions]))
        hooks       (->> (get-in extension-data [:hooks type])
                         (keys)
                         (into #{}))]
    (set/intersection added-hooks hooks)))

(defn existing-hooks [cofx extension-data]
  (->> (get-in extension-data [:hooks])
       (keys)
       (map #(existing-hooks-for % cofx extension-data))
       (apply set/union)))

(fx/defn stage-extension [{:keys [db] :as cofx} url extension-data modal?]
  (let [hooks (existing-hooks cofx extension-data)]
    (if (empty? hooks)
      (fx/merge cofx
                {:db (assoc db :extensions/staged-extension {:url            url
                                                             :extension-data extension-data})}
                (navigation/navigate-to-cofx (if modal? :show-extension-modal :show-extension) nil))
      {:utils/show-popup {:title   (i18n/label :t/error)
                          :content (i18n/label :t/extension-hooks-cannot-be-added
                                               {:hooks (->> hooks
                                                            (map name)
                                                            (clojure.string/join ", "))})}})))
