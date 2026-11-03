// Browser QA with a separately launched local Chrome CDP endpoint; no inference.
// node scripts/validate_ui.mjs [http://127.0.0.1:9223] [output-directory]
import {mkdir, writeFile} from 'node:fs/promises';
import path from 'node:path';

const endpoint = process.argv[2] || 'http://127.0.0.1:9223';
const output = process.argv[3] || 'results/research/ui_qa_v2';
await mkdir(output, {recursive: true});
const targets = await (await fetch(endpoint + '/json')).json();
const page = targets.find(t => t.type === 'page');
if (!page) throw Error('A local Chrome page target is required.');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {ws.onopen = resolve; ws.onerror = reject;});
const pending = new Map();
const exceptions = [];
let id = 0;
ws.onmessage = ({data}) => {
  const value = JSON.parse(data);
  if (value.method === 'Runtime.exceptionThrown') exceptions.push(value.params);
  const promise = pending.get(value.id);
  if (promise) {
    pending.delete(value.id);
    value.error ? promise.reject(Error(JSON.stringify(value.error))) : promise.resolve(value.result);
  }
};
const send = (method, params = {}) => new Promise((resolve, reject) => {
  pending.set(++id, {resolve, reject}); ws.send(JSON.stringify({id, method, params}));
});
const evaluate = async expression => {
  const result = await send('Runtime.evaluate', {expression, returnByValue:true, awaitPromise:true});
  if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails));
  return result.result.value;
};
const until = async expression => {
  const stop = Date.now() + 45000;
  while (Date.now() < stop) {
    if (await evaluate(expression)) return;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw Error('UI state deadline exceeded: ' + expression);
};
const screenshot = async name => {
  const layout = await send('Page.getLayoutMetrics');
  const size = layout.cssContentSize;
  const result = await send('Page.captureScreenshot', {format:'png', captureBeyondViewport:true,
    clip:{x:0,y:0,width:size.width,height:size.height,scale:1}});
  await writeFile(path.join(output, name), Buffer.from(result.data, 'base64'));
};
try {
  await send('Page.enable'); await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', {width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate', {url:'http://127.0.0.1:8765/'});
  await until("document.readyState==='complete' && document.querySelector('#audit')?.textContent.includes('Market evaluation blocked')");
  await evaluate("document.querySelector('#exclude').value='ASSET_00';document.querySelector('#run').click()");
  await until("!document.querySelector('#run').disabled && document.querySelector('#message').textContent.startsWith('Comparison complete')");
  const desktop = await evaluate("({rows:document.querySelectorAll('#comparison tr').length, message:document.querySelector('#message').textContent, horizontalOverflow:document.documentElement.scrollWidth>window.innerWidth})");
  if (desktop.rows < 5 || desktop.horizontalOverflow) throw Error('Desktop comparison layout failed.');
  await screenshot('desktop-comparison.png');
  await send('Emulation.setDeviceMetricsOverride', {width:390,height:844,deviceScaleFactor:1,mobile:true});
  const mobile = await evaluate("({viewport:window.innerWidth, documentWidth:document.documentElement.scrollWidth, tableWidth:document.querySelector('#comparison').clientWidth})");
  if (mobile.documentWidth > mobile.viewport) throw Error('Mobile page overflows viewport.');
  await screenshot('mobile-comparison.png');
  await evaluate("document.querySelector('#dataset').value='market';document.querySelector('#run').click()");
  await until("!document.querySelector('#run').disabled && document.querySelector('#comparison').textContent==='No market decision was generated.'");
  const blocked = await evaluate("document.querySelector('#message').textContent");
  const cleared = await evaluate("document.querySelector('#choices').options.length===0 && document.querySelector('#decision').textContent==='No verified market decision is available.' && !document.querySelector('#holdings').textContent.includes('ASSET_')");
  if (!cleared) throw Error('Blocked market request retained stale synthetic decision evidence.');
  await screenshot('mobile-market-blocked.png');
  if (exceptions.length) throw Error('Uncaught browser exceptions.');
  await writeFile(path.join(output, 'validation.json'), JSON.stringify({status:'passed',browser:'Chrome CDP',
    desktop,mobile,marketBlockedMessage:blocked,staleEvidenceCleared:cleared,uncaughtExceptions:exceptions,visualInspection:'pending',
    newInferenceCalls:0,source:'scripts/validate_ui.mjs'}, null, 2));
  console.log('Browser interaction and layout checks passed; inspect PNGs before claiming visual QA.');
} finally {ws.close();}
