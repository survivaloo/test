// このアプリではService Workerによるキャッシュが古いページを表示し続ける
// 問題を引き起こしたため廃止した。既存にインストール済みの端末を
// クリーンアップするための自己解除(セルフアンインストール)処理のみ残す。

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.map((key) => caches.delete(key)));
      await self.registration.unregister();

      const clientsList = await self.clients.matchAll({ type: "window" });
      clientsList.forEach((client) => client.navigate(client.url));
    })()
  );
});
