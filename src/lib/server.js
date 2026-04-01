function startServer(app, port, serviceName) {
  app.listen(port, () => {
    console.log(`[${serviceName}] listening on ${port}`);
  });
}

module.exports = { startServer };
