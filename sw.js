const CACHE='aile-sofrasi-v041-sok-free-prices';
const ASSETS=['./','./index.html','./manifest.webmanifest','./icon.svg','./firebase-config.js','./appcheck-config.js','./prices.json'];
self.addEventListener('install',event=>{
  event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS)));
  self.skipWaiting();
});
self.addEventListener('activate',event=>{
  event.waitUntil(
    caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))
  );
  self.clients.claim();
});
self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET') return;
  event.respondWith(
    fetch(event.request).then(resp=>{
      const copy=resp.clone();
      caches.open(CACHE).then(cache=>cache.put(event.request,copy));
      return resp;
    }).catch(()=>caches.match(event.request).then(r=>r||caches.match('./index.html')))
  );
});


self.addEventListener('notificationclick',event=>{
  event.notification.close();
  const feedbackId=event.notification.data?.feedbackId;
  event.waitUntil((async()=>{
    const all=await clients.matchAll({type:'window',includeUncontrolled:true});
    if(all.length){
      const client=all[0];
      await client.focus();
      client.postMessage({type:'OPEN_MEAL_FEEDBACK',feedbackId});
      return;
    }
    const url=feedbackId?`./?feedback=${encodeURIComponent(feedbackId)}`:'./';
    await clients.openWindow(url);
  })());
});
