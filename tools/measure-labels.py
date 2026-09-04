from playwright.sync_api import sync_playwright
import json
URL='file:///home/user/Great-Tibet-Map/tibet-three-regions-map.html'
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    pg=b.new_page(viewport={'width':1400,'height':1200})
    pg.goto(URL); pg.wait_for_timeout(600)
    pg.click('[data-act="rivers"]'); pg.click('[data-act="ranges"]'); pg.wait_for_timeout(400)
    out=pg.evaluate("""()=>{
      const res={labels:{},obstacles:[]};
      // range label sizes, in SVG user units, independent of where they sit
      // Latin name sizes for every feature the placer positions. In "both"
      // mode a Tibetan name sits under it, so the pair is measured as one box.
      const pair=(e)=>{const bb=e.getBBox(); return {w:bb.width,h:bb.height};};
      document.querySelectorAll('.tm-rglab,.tm-hylab,.tm-pklab').forEach(e=>{
        if(e.classList.contains('tm-rgbo')||e.classList.contains('tm-hybo')
           ||e.classList.contains('tm-pkbo')) return;
        res.labels[e.textContent.trim()]=pair(e);});
      document.querySelectorAll('.tm-rgbo,.tm-hybo,.tm-pkbo').forEach(e=>{
        // widen the recorded box to cover whichever of the two names is longer
        const t=e.previousElementSibling && e.previousElementSibling.textContent.trim();
        if(!t||!res.labels[t]) return;
        const bb=e.getBBox();
        res.labels[t]={w:Math.max(res.labels[t].w,bb.width), h:res.labels[t].h+13};});
      // Everything a feature name must avoid, as boxes in viewBox units.
      // Positions come from the element's own screen matrix rather than
      // getBBox plus a parsed transform attribute: the Kham title is moved
      // aside by a CSS transform when a physical layer is on, and parsing the
      // attribute cannot see that, so the placer aimed at its old position.
      const svg=document.querySelector('.tibmap__svg');
      const inv=svg.getScreenCTM().inverse();
      const P=(x,y,m)=>{const p=svg.createSVGPoint();p.x=x;p.y=y;
                        const q=p.matrixTransform(m).matrixTransform(inv);return q;};
      const push=(e,kind)=>{
        const b=e.getBBox(), m=e.getScreenCTM(); if(!m) return;
        const c=[P(b.x,b.y,m),P(b.x+b.width,b.y,m),
                 P(b.x+b.width,b.y+b.height,m),P(b.x,b.y+b.height,m)];
        const xs=c.map(p=>p.x), ys=c.map(p=>p.y);
        res.obstacles.push({kind,t:e.textContent.trim(),
                            x:Math.min(...xs),y:Math.min(...ys),
                            w:Math.max(...xs)-Math.min(...xs),
                            h:Math.max(...ys)-Math.min(...ys)});};
      document.querySelectorAll('.tm-cname,.tm-cbo,.tm-rname,.tm-rbo,.tm-ctry').forEach(e=>{
        const k=e.classList.contains('tm-ctry')?'country'
              :(e.classList.contains('tm-rname')||e.classList.contains('tm-rbo'))?'region':'town';
        push(e,k);});
      return res;}""")
    json.dump(out, open('measured.json','w'))
    print("range labels measured: %d"%len(out['labels']))
    for k,v in out['labels'].items(): print("   %-20s %6.1f x %4.1f SVG units"%(k,v['w'],v['h']))
    print("obstacles: %d"%len(out['obstacles']))
    b.close()
