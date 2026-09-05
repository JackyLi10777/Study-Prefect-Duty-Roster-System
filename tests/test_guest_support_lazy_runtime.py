"""Execute the browser-only report runtime without a server or browser process."""
import json
from pathlib import Path
import shutil
import subprocess
from html.parser import HTMLParser

from nicegui_app.ui.page_routes.support import _guest_report_markup


def test_guest_optional_controls_are_inert_template_not_live_form():
    class Controls(HTMLParser):
        depth = 0
        live = []
        blueprint = []
        def handle_starttag(self, tag, attrs):
            if tag == "template":
                self.depth += 1
            if tag in {"input", "select", "textarea"}:
                (self.blueprint if self.depth else self.live).append(dict(attrs).get("id"))
        def handle_endtag(self, tag):
            if tag == "template":
                self.depth -= 1
    parser = Controls()
    parser.feed(_guest_report_markup("/rosters/12?private=discard"))
    assert parser.live == ["sy-support-expected", "sy-support-actual", "sy-support-steps"]
    assert set(parser.blueprint) == {"sy-support-route", "sy-support-action", "sy-support-impact",
                                     "sy-support-frequency", "sy-support-last-good"}


def test_guest_runtime_defaults_first_mount_reuse_reset_and_latest_input():
    node = shutil.which("node")
    assert node
    script = Path("nicegui_app/assets/motion/support-feedback-v1.js").read_text(encoding="utf-8")
    harness = r"""
const assert = require('node:assert/strict');
class Element {
 constructor(){this.handlers={};this.dataset={};this.value='';this.textContent='';this.hidden=false;}
 addEventListener(name, fn){(this.handlers[name]??=[]).push(fn);}
 emit(name){for(const fn of this.handlers[name]||[])fn({preventDefault(){}});}
 focus(){document.activeElement=this;}
}
global.HTMLElement=Element;
global.HTMLFormElement=class extends Element{};
global.HTMLOutputElement=class extends Element{};
global.HTMLButtonElement=class extends Element{};
global.HTMLDetailsElement=class extends Element{};
global.HTMLTemplateElement=class extends Element{};
const root=new Element(), nodes={};
for(const name of ['form','result','result-actions','error','download','copy','email']){
 const Kind=name==='form'?HTMLFormElement:name==='result'?HTMLOutputElement:
   ['download','copy','email'].includes(name)?HTMLButtonElement:Element;
 nodes[`#sy-support-browser-${name}`]=new Kind();
}
for(const name of ['expected','actual','steps']){nodes[`#sy-support-${name}`]=new Element();nodes[`#sy-support-${name}`].value='Fictional '+name;}
const optional={};
for(const name of ['route','action','impact','frequency','last-good'])optional[`#sy-support-${name}`]=new Element();
optional['#sy-support-route'].value='roster_workflow'; optional['#sy-support-action'].value='page_view';
const details=new HTMLDetailsElement(),template=new HTMLTemplateElement(),content=new Element(),summary=new Element();
let mounts=0; template.content=optional; template.remove=()=>{};
content.appendChild=fragment=>{mounts++;Object.assign(nodes,fragment);};
content.contains=element=>Object.values(optional).includes(element);
details.querySelector=selector=>selector==='summary'?summary:selector==='template'?template:content;
nodes['#sy-support-details']=details; nodes['#sy-support-details-content']=content;
root.querySelector=selector=>nodes[selector]||null;
root.dataset={defaultRoute:'roster_workflow',defaultWorkflow:'page_view'};
global.document={readyState:'complete',querySelector:()=>root,activeElement:null,
 createElement:()=>({click(){},remove(){}})};
global.crypto=require('node:crypto').webcrypto;
global.navigator={}; global.location={};
let captured;
global.URL={createObjectURL(blob){captured=blob;return 'blob:fictional';},revokeObjectURL(){}};
global.setTimeout=()=>{};
eval(JSON.parse(process.argv[2]));
const form=nodes['#sy-support-browser-form'], download=nodes['#sy-support-browser-download'];
async function report(){form.emit('submit');download.emit('click');return JSON.parse(await captured.text());}
(async()=>{
 assert.equal(mounts,0);
 let value=await report(); assert.equal(value.route_category,'roster_workflow');assert.equal(value.workflow_action,'page_view');assert.equal(value.impact,'');
 details.open=true;details.emit('toggle');assert.equal(mounts,1);
 optional['#sy-support-impact'].value='Last fictional input';
 const identities=Object.values(optional);
 for(let i=0;i<20;i++){document.activeElement=optional['#sy-support-impact'];details.open=false;details.emit('toggle');assert.equal(document.activeElement,summary);details.open=true;details.emit('toggle');}
 assert.equal(mounts,1);assert.deepEqual(Object.values(optional),identities);
 value=await report();assert.equal(value.impact,'Last fictional input');
 nodes['#sy-support-expected'].value='Newest fictional expected';form.emit('input');
 assert.equal(nodes['#sy-support-browser-result-actions'].hidden,true);
 download.emit('click');value=JSON.parse(await captured.text());assert.equal(value.expected_behavior,'Newest fictional expected');
 form.emit('reset'); // Native browser reset itself restores field default values.
 assert.equal(nodes['#sy-support-browser-result'].textContent,'');
 assert.equal(nodes['#sy-support-browser-result-actions'].hidden,true);
 assert.equal(details.handlers.toggle.length,1);assert.equal(form.handlers.submit.length,1);
 assert.equal(value.persistence,'browser-only');
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    result = subprocess.run([node, "-", json.dumps(script)], input=harness, text=True,
                            encoding="utf-8", capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
