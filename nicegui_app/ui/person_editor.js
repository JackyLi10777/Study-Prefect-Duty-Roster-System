// This component owns client-side input until a generation-scoped snapshot is
// acknowledged. It deliberately does not use NiceGUI ValueElement loopback.
// Vue exposes reactive proxies, which structuredClone cannot clone. This wire
// contract contains JSON values only; JSON copying also detaches emitted data.
const copy = value => JSON.parse(JSON.stringify(value));
export default {
  props: {binding: Object, labels: Object, fields: Array},
  emits: ["editor-snapshot"],
  data() {
    return {
      owner: null, values: {}, visible: false, sequence: 0, finalPacket: null,
      hydrating: false, composing: false, deferredAction: null, error: "",
      returnFocus: null, returnScroll: null, skipRestore: false, previousOverflow: null,
    };
  },
  watch: {
    binding: {
      immediate: true,
      handler(binding) {
        if (!binding || binding.generation === this.owner?.generation) return;
        this.releaseScroll();
        this.hydrating = true;
        this.owner = copy(binding);
        this.values = copy(binding.values);
        this.sequence = 0;
        this.finalPacket = null;
        this.composing = false;
        this.deferredAction = null;
        this.error = "";
        this.skipRestore = false;
        this.returnFocus = document.activeElement;
        this.returnScroll = {left: window.scrollX, top: window.scrollY};
        this.visible = true;
        this.$nextTick(() => {
          this.$refs.sheet?.showModal();
          this.previousOverflow = document.documentElement.style.overflow;
          document.documentElement.style.overflow = "hidden";
          this.hydrating = false;
        });
      },
    },
  },
  computed: {
    busy() {return this.hydrating || !!this.finalPacket;},
    activeFields() {
      return this.fields.filter(field => Object.hasOwn(this.values, field.name));
    },
  },
  beforeUnmount() {this.releaseScroll();},
  methods: {
    nativeClosed() {
      // Native close events are queued. An old close event must not finalize a
      // newly opened binding whose dialog is already open again.
      if (!this.visible || this.$refs.sheet?.open) return;
      this.$refs.sheet?.showModal();
      this.requestFinish("close");
    },
    releaseScroll() {
      if (this.previousOverflow === null) return;
      document.documentElement.style.overflow = this.previousOverflow;
      this.previousOverflow = null;
    },
    backdropClick(event) {
      if (event.target !== this.$refs.sheet) return;
      const rect = event.target.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) {
        this.requestFinish("close");
      }
    },
    changed(field, value) {
      if (this.busy || !this.visible || !Object.hasOwn(this.values, field)) return;
      this.values[field] = value;
      if (!this.composing) this.publish("change");
    },
    packet(action) {
      return {
        personId: this.owner.personId, generation: this.owner.generation,
        schemaRevision: this.owner.schemaRevision, sequence: ++this.sequence,
        action, values: copy(this.values),
      };
    },
    publish(action) {
      const packet = this.packet(action);
      if (action !== "change") this.finalPacket = packet;
      this.$emit("editor-snapshot", packet);
    },
    async requestFinish(action = "close") {
      if (this.busy || !this.visible) return;
      const generation = this.owner.generation;
      if (this.composing) {
        this.deferredAction = action;
        document.activeElement?.blur();
        return;
      }
      // Quasar applies model changes on this tick. Read the native text value
      // too, so a paste or final keystroke immediately followed by Done survives.
      await this.$nextTick();
      if (this.busy || !this.visible || generation !== this.owner.generation) return;
      if (this.composing) {
        this.deferredAction = action;
        document.activeElement?.blur();
        return;
      }
      for (const field of this.activeFields) {
        if (field.kind !== "text") continue;
        const ref = this.$refs[field.name];
        const control = Array.isArray(ref) ? ref[0] : ref;
        const input = control?.$el?.querySelector("input,textarea");
        if (input) this.values[field.name] = input.value;
      }
      this.publish(action);
    },
    async compositionEnded() {
      this.composing = false;
      await this.$nextTick();
      const action = this.deferredAction;
      this.deferredAction = null;
      if (action) this.requestFinish(action);
      else if (!this.busy && this.visible) this.publish("change");
    },
    retry() {
      if (this.finalPacket) this.$emit("editor-snapshot", copy(this.finalPacket));
    },
    acknowledge(receipt) {
      if (!receipt.accepted || receipt.generation !== this.owner?.generation || receipt.personId !== this.owner?.personId) return;
      if (!this.finalPacket || receipt.sequence !== this.finalPacket.sequence || receipt.action !== this.finalPacket.action) return;
      this.skipRestore = receipt.action === "full_edit";
      this.finalPacket = null;
      this.visible = false;
      this.error = "";
      this.$refs.sheet?.close();
      this.releaseScroll();
      this.restoreFocus();
    },
    reject(generation, sequence, message) {
      if (generation !== this.owner?.generation) return;
      if (this.finalPacket && sequence !== this.finalPacket.sequence) return;
      this.finalPacket = null;
      this.error = message;
    },
    restoreFocus() {
      if (this.skipRestore) return;
      const search = document.querySelector('[data-testid="prefect-directory-search"]');
      const target = this.returnFocus?.isConnected ? this.returnFocus
        : (search?.matches("input") ? search : search?.querySelector("input"));
      target?.focus({preventScroll: true});
      if (this.returnScroll) window.scrollTo({...this.returnScroll, behavior: "instant"});
    },
  },
  template: `
    <dialog ref="sheet" class="sy-person-editor" @cancel.prevent="requestFinish('close')" @close="nativeClosed" @click="backdropClick"
      style="width:100%;max-width:36rem;max-height:90dvh;margin:auto auto 0;top:auto;bottom:0;border:0;padding:0;border-radius:20px 20px 0 0;color:inherit;background:var(--sy-surface)"
      aria-modal="true" :aria-labelledby="'person-editor-title-' + $attrs.id"
      data-testid="prefect-editor-sheet" :data-person-id="owner?.personId" :data-generation="owner?.generation">
      <q-card style="width:100%;max-width:36rem;max-height:90dvh;overflow:auto;padding:20px;padding-bottom:max(20px,env(safe-area-inset-bottom))"
        @compositionstart.capture="composing = true" @compositionend.capture="compositionEnded">
        <div class="row items-start justify-between q-mb-md">
          <div style="min-width:0;overflow-wrap:anywhere">
            <h2 :id="'person-editor-title-' + $attrs.id" style="font-size:20px;margin:0">{{owner?.title}}</h2>
            <div>{{owner?.subtitle}}</div>
          </div>
          <q-btn flat round icon="close" :aria-label="labels.close" :disable="busy" @click="requestFinish('close')" style="min-width:44px;min-height:44px" />
        </div>
        <div v-for="field in fields" :key="field.name" v-show="Object.hasOwn(values, field.name)" :data-editor-field="field.name" class="q-mb-md">
          <q-input v-if="field.kind === 'text'" :ref="field.name" :label="field.label"
            :model-value="values[field.name]" :disable="busy" input-style="font-size:16px"
            @update:model-value="value => changed(field.name, value)" />
          <q-toggle v-else-if="field.kind === 'boolean'" :label="field.label" :model-value="values[field.name]"
            :disable="busy" @update:model-value="value => changed(field.name, value)" />
          <fieldset v-else-if="field.kind === 'multiple' || field.kind === 'choice'" style="border:0;padding:0;margin:0;min-width:0">
            <legend>{{field.label}}</legend>
            <q-option-group :options="field.options" :type="field.kind === 'multiple' ? 'checkbox' : 'radio'"
              :model-value="values[field.name] ?? (field.kind === 'multiple' ? [] : null)" :disable="busy" inline @update:model-value="value => changed(field.name, value)" />
          </fieldset>
          <label v-else-if="field.kind === 'select'" style="display:block">
            {{field.label}}
            <!-- Keep the picker in the native modal's top layer; a Quasar menu
                 teleported to body would be behind/inert outside this dialog. -->
            <select :value="values[field.name]" :disabled="busy" @change="event => changed(field.name, event.target.value)"
              style="display:block;min-height:44px;width:100%;font-size:16px;color:inherit;background:var(--sy-surface);border:1px solid currentColor;border-radius:8px;padding:8px">
              <option v-for="option in field.options" :key="option.value" :value="option.value">{{option.label}}</option>
            </select>
          </label>
        </div>
        <p role="status" aria-live="polite">{{error || (finalPacket ? labels.waiting : labels.buffered)}}</p>
        <div class="row justify-between q-gutter-sm">
          <q-btn outline :label="labels.fullEdit" :disable="busy" @click="requestFinish('full_edit')" style="min-height:44px" />
          <q-btn v-if="finalPacket" outline :label="labels.retry" @click="retry" style="min-height:44px" />
          <q-btn v-else color="primary" :label="labels.done" :disable="hydrating" @click="requestFinish('close')" data-testid="close-prefect-editor" style="min-height:44px" />
        </div>
      </q-card>
    </dialog>`,
};
