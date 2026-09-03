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
      document.querySelectorAll('.tm-rglab').forEach(e=>{
        const bb=e.getBBox(); res.labels[e.textContent.trim()]={w:bb.width,h:bb.height};});
      // everything a range name must avoid, as SVG-space boxes
      const push=(e,kind)=>{const b=e.getBBox();
        // getBBox ignores the element's own transform, so add translate() back
        let dx=0,dy=0; const t=e.getAttribute('transform');
        if(t){const m=/translate\\(([-\\d.]+)[ ,]([-\\d.]+)\\)/.exec(t); if(m){dx=+m[1];dy=+m[2];}}
        res.obstacles.push({kind,t:e.textContent.trim(),
                            x:b.x+dx,y:b.y+dy,w:b.width,h:b.height});};
      document.querySelectorAll('.tm-cname,.tm-cbo,.tm-rname,.tm-rbo,.tm-hylab,.tm-pklab').forEach(e=>{
        const k=e.classList.contains('tm-hylab')?'river':
                e.classList.contains('tm-pklab')?'peak':
                (e.classList.contains('tm-rname')||e.classList.contains('tm-rbo'))?'region':'town';
        push(e,k);});
      return res;}""")
    json.dump(out, open('measured.json','w'))
    print("range labels measured: %d"%len(out['labels']))
    for k,v in out['labels'].items(): print("   %-20s %6.1f x %4.1f SVG units"%(k,v['w'],v['h']))
    print("obstacles: %d"%len(out['obstacles']))
    b.close()
