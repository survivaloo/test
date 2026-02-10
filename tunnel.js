const localtunnel = require('localtunnel');

(async () => {
  try {
    const tunnel = await localtunnel({ port: 8080 });
    console.log('\n======================');
    console.log('囲碁ゲーム公開URL:');
    console.log(tunnel.url);
    console.log('======================\n');

    tunnel.on('close', () => {
      console.log('Tunnel closed');
      process.exit(0);
    });

    // Keep the tunnel running
    process.on('SIGINT', () => {
      tunnel.close();
    });
  } catch (err) {
    console.error('Error:', err.message);
    process.exit(1);
  }
})();
