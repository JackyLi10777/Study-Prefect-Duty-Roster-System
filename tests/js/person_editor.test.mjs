import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("../../nicegui_app/ui/person_editor.js", import.meta.url), "utf8");
const {default: component} = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);

function instance() {
  const emitted = [];
  globalThis.document = {documentElement: {style: {overflow: ""}}, activeElement: {blur() {}, isConnected: true, focus() {}}, querySelector() {return null;}};
  globalThis.window = {scrollX: 0, scrollY: 200, scrollTo() {}};
  const vm = {
    ...component.data(), fields: [{name: "remarks", kind: "text"}], $refs: {},
    $nextTick: async callback => {if (callback) callback();},
    $emit: (name, value) => emitted.push({name, value}),
  };
  for (const [name, method] of Object.entries(component.methods)) vm[name] = method.bind(vm);
  for (const [name, getter] of Object.entries(component.computed)) {
    Object.defineProperty(vm, name, {get: getter.bind(vm)});
  }
  function bind(personId = "a", generation = 1) {
    component.watch.binding.handler.call(vm, {
      personId, generation, schemaRevision: "test", baseVersion: 1,
      values: {remarks: "", days: ["MONDAY"]}, title: personId,
    });
  }
  bind();
  return {vm, emitted, bind};
}

test("hydration emits nothing and a later binding keeps no previous values", () => {
  const {vm, emitted, bind} = instance();
  assert.equal(emitted.length, 0);
  vm.values.remarks = "A";
  bind("b", 2);
  assert.equal(vm.values.remarks, "");
  assert.equal(vm.owner.personId, "b");
  assert.equal(emitted.length, 0);
});

test("binding and snapshots accept Vue-style reactive proxies", () => {
  const {vm, emitted} = instance();
  const values = new Proxy({remarks: "reactive"}, {});
  component.watch.binding.handler.call(vm, new Proxy({
    personId: "proxy", generation: 2, schemaRevision: "test", values,
  }, {}));
  vm.values = new Proxy(vm.values, {});
  vm.changed("remarks", "safe copied packet");
  assert.equal(emitted.at(-1).value.values.remarks, "safe copied packet");
});

test("each user event stamps its owner and copies a complete immutable snapshot", () => {
  const {vm, emitted, bind} = instance();
  vm.changed("remarks", "A input");
  vm.values.days.push("TUESDAY");
  bind("b", 2);
  assert.equal(emitted[0].value.personId, "a");
  assert.equal(emitted[0].value.generation, 1);
  assert.deepEqual(emitted[0].value.values, {remarks: "A input", days: ["MONDAY"]});
});

test("immediate Done reads the last native text value before publishing", async () => {
  const {vm, emitted} = instance();
  vm.$refs.remarks = [{$el: {querySelector: () => ({value: "最後一字"})}}];
  await vm.requestFinish("close");
  assert.equal(emitted.at(-1).value.values.remarks, "最後一字");
  assert.equal(vm.visible, true);
  assert.equal(vm.busy, true);
  vm.changed("remarks", "cannot edit finalized packet");
  assert.equal(emitted.length, 1);
});

test("IME close waits for composition end and preserves its final text", async () => {
  const {vm, emitted} = instance();
  vm.composing = true;
  vm.changed("remarks", "中");
  await vm.requestFinish("close");
  assert.equal(emitted.length, 0);
  assert.equal(vm.visible, true);
  vm.$refs.remarks = [{$el: {querySelector: () => ({value: "中文"})}}];
  await vm.compositionEnded();
  await vm.$nextTick();
  assert.equal(emitted.at(-1).value.action, "close");
  assert.equal(emitted.at(-1).value.values.remarks, "中文");
});

test("late ack cannot close another owner or a newer final snapshot", async () => {
  const {vm, emitted, bind} = instance();
  await vm.requestFinish("close");
  const old = emitted.at(-1).value;
  bind("b", 2);
  await vm.requestFinish("close");
  vm.acknowledge({...old, accepted: true});
  assert.equal(vm.visible, true);
  assert.equal(vm.busy, true);
  vm.acknowledge({...emitted.at(-1).value, personId: "a", accepted: true});
  assert.equal(vm.visible, true);
  vm.acknowledge({...emitted.at(-1).value, accepted: true});
  assert.equal(vm.visible, false);
});

test("missing acknowledgement retains inputs and retry sends the identical intent", async () => {
  const {vm, emitted} = instance();
  vm.changed("remarks", "keep this");
  await vm.requestFinish("close");
  const original = structuredClone(emitted.at(-1).value);
  vm.retry();
  assert.deepEqual(emitted.at(-1).value, original);
  assert.equal(vm.visible, true);
  assert.equal(vm.values.remarks, "keep this");
});

test("full editor acknowledgement avoids stealing focus from the next dialog", async () => {
  const {vm, emitted} = instance();
  let focused = 0;
  vm.returnFocus = {isConnected: true, focus() {focused++;}};
  await vm.requestFinish("full_edit");
  vm.acknowledge({...emitted.at(-1).value, accepted: true});
  vm.restoreFocus();
  assert.equal(focused, 0);
});

test("rejected final input remains editable and an unrelated rejection is ignored", async () => {
  const {vm, emitted} = instance();
  await vm.requestFinish("close");
  const final = emitted.at(-1).value;
  vm.reject(99, final.sequence, "stale");
  assert.equal(vm.busy, true);
  vm.reject(final.generation, final.sequence, "retry");
  assert.equal(vm.visible, true);
  assert.equal(vm.busy, false);
  assert.equal(vm.error, "retry");
});

test("a queued close event cannot finalize an already reopened sheet", async () => {
  const {vm, emitted} = instance();
  vm.$refs.sheet = {open: true, showModal() {}};
  vm.nativeClosed();
  await vm.$nextTick();
  assert.equal(emitted.length, 0);
});

test("only an outside-dialog backdrop click requests finalization", async () => {
  const {vm, emitted} = instance();
  vm.$refs.sheet = {getBoundingClientRect: () => ({left: 0, right: 390, top: 100, bottom: 844})};
  vm.backdropClick({target: vm.$refs.sheet, clientX: 10, clientY: 150});
  await vm.$nextTick();
  assert.equal(emitted.length, 0);
  vm.backdropClick({target: vm.$refs.sheet, clientX: 10, clientY: 10});
  await vm.$nextTick();
  assert.equal(emitted.at(-1).value.action, "close");
});

test("focus falls back to search when a filtered card no longer exists", () => {
  const {vm} = instance();
  let focused = 0;
  vm.returnFocus = {isConnected: false};
  document.querySelector = () => ({matches: () => true, focus() {focused++;}});
  vm.restoreFocus();
  assert.equal(focused, 1);
});
